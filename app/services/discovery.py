"""Manual-source discovery orchestration with per-record failure isolation."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    CandidateProcessingStatus,
    DiscoveryRun,
    DiscoveryRunStatus,
    Lead,
    RawCandidate,
)
from app.pipeline.classifier import LeadClassifier
from app.pipeline.parser import CandidateParseError, CandidateParser, ParsedCandidate
from app.pipeline.scorer import LeadScorer
from app.schemas import SeedInput
from app.services.evidence_service import EvidencePersistenceService
from app.services.lead_service import LeadPersistenceService
from app.services.seed_manager import SeedManager
from app.sources import LeadSource, ManualSeedFileError, RawCandidateData
from app.sources.base import SourceRecordError

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DiscoverySummary:
    """Persisted run metrics suitable for CLI output and later API reporting."""

    run_id: str
    query: str
    source: str
    status: DiscoveryRunStatus
    discovered: int
    parsed: int
    duplicates: int
    qualified: int
    rejected: int
    errors: int


class DiscoveryService:
    """Connect a compliant source to parsing, deduplication, and run observability."""

    def __init__(
        self,
        seed_manager: SeedManager | None = None,
        parser: CandidateParser | None = None,
        lead_service: LeadPersistenceService | None = None,
        classifier: LeadClassifier | None = None,
        scorer: LeadScorer | None = None,
        evidence_service: EvidencePersistenceService | None = None,
    ) -> None:
        self._seed_manager = seed_manager or SeedManager()
        self._parser = parser or CandidateParser()
        self._lead_service = lead_service or LeadPersistenceService()
        self._classifier = classifier or LeadClassifier()
        self._scorer = scorer or LeadScorer()
        self._evidence_service = evidence_service or EvidencePersistenceService()

    def run(self, session: Session, seed: SeedInput, source: LeadSource) -> DiscoverySummary:
        """Run one source while isolating source and parser failures from good records."""

        if seed.source != source.source_name:
            raise ValueError("seed source must match the selected source adapter")

        self._seed_manager.get_or_create(session, seed)
        run = DiscoveryRun(query=seed.query, source=seed.source)
        session.add(run)
        session.flush()

        try:
            source_result = source.discover()
        except ManualSeedFileError as error:
            self._mark_source_failure(run, error)
            return self._summary(run)

        run.discovered_count = len(source_result.candidates)
        run.error_count = len(source_result.errors)
        for source_error in source_result.errors:
            self._log_source_error(seed.source, source_error)

        for candidate in source_result.candidates:
            self._process_candidate(session, run, candidate)

        run.status = (
            DiscoveryRunStatus.PARTIAL_FAILURE if run.error_count else DiscoveryRunStatus.SUCCESS
        )
        run.finished_at = datetime.now(timezone.utc)
        session.flush()
        return self._summary(run)

    def _process_candidate(
        self,
        session: Session,
        run: DiscoveryRun,
        candidate: RawCandidateData,
    ) -> None:
        raw_candidate = RawCandidate(
            discovery_run=run,
            source=candidate.source,
            raw_url=candidate.url,
            raw_title=candidate.title,
            raw_description=candidate.description or candidate.snippet,
            raw_contact_text=candidate.raw_contact_text,
            captured_at=candidate.captured_at,
        )
        session.add(raw_candidate)

        try:
            parsed = self._parser.parse(candidate)
            classification = self._classifier.classify(parsed)
            scoring = self._scorer.score(parsed, classification)
            lead = self._lead_from_parsed(parsed)
            lead.business_type = classification.business_type
            lead.score = scoring.score
            lead.score_band = scoring.score_band
            lead.score_reasons = [reason.text for reason in scoring.reasons]
            persistence_result = self._lead_service.assess_and_persist(session, lead)
            if persistence_result.created:
                evidence_drafts = (
                    *(item for item in (classification.evidence,) if item is not None),
                    *scoring.evidences,
                )
                self._evidence_service.persist(session, persistence_result.lead, evidence_drafts)
        except (CandidateParseError, ValueError) as error:
            raw_candidate.processing_status = CandidateProcessingStatus.ERROR
            raw_candidate.error_detail = str(error)
            run.error_count += 1
            LOGGER.warning(
                "source=%s url=%s stage=parse_or_validate error=%s",
                candidate.source,
                candidate.url,
                error,
            )
            return

        raw_candidate.processing_status = CandidateProcessingStatus.PARSED
        raw_candidate.lead = persistence_result.lead
        run.parsed_count += 1
        if not persistence_result.created:
            run.duplicate_count += 1

    @staticmethod
    def _lead_from_parsed(parsed: ParsedCandidate) -> Lead:
        return Lead(
            name=parsed.name,
            description=parsed.description,
            country=parsed.country,
            city=parsed.city,
            website=parsed.website,
            social_url=parsed.social_url,
            email=parsed.email,
            phone=parsed.phone,
            source=parsed.source,
            source_url=parsed.source_url,
        )

    @staticmethod
    def _mark_source_failure(run: DiscoveryRun, error: ManualSeedFileError) -> None:
        run.status = DiscoveryRunStatus.FAILED
        run.error_count = 1
        run.finished_at = datetime.now(timezone.utc)
        LOGGER.warning("source=%s stage=load_seed_file error=%s", run.source, error)

    @staticmethod
    def _log_source_error(source: str, source_error: SourceRecordError) -> None:
        LOGGER.warning(
            "source=%s record_index=%s stage=validate_seed error=%s",
            source,
            source_error.record_index,
            source_error.message,
        )

    @staticmethod
    def _summary(run: DiscoveryRun) -> DiscoverySummary:
        return DiscoverySummary(
            run_id=run.id,
            query=run.query,
            source=run.source,
            status=run.status,
            discovered=run.discovered_count,
            parsed=run.parsed_count,
            duplicates=run.duplicate_count,
            qualified=run.qualified_count,
            rejected=run.rejected_count,
            errors=run.error_count,
        )
