"""Validated storage and reuse of MVP discovery seed queries."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Query
from app.schemas import SeedInput


class SeedManager:
    """Create or reuse a query/source/region combination for manual discovery runs."""

    def get_or_create(self, session: Session, seed: SeedInput) -> Query:
        """Return an existing exact seed or stage a new one without committing the session."""

        statement = select(Query).where(Query.query == seed.query, Query.source == seed.source)
        if seed.region is None:
            statement = statement.where(Query.region.is_(None))
        else:
            statement = statement.where(Query.region == seed.region)

        existing_seed = session.scalar(statement.order_by(Query.created_at, Query.id).limit(1))
        if existing_seed is not None:
            return existing_seed

        query = Query(query=seed.query, source=seed.source, region=seed.region)
        session.add(query)
        return query
