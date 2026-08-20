"""UTF-8 CSV rendering for reviewable lead records."""

import csv
import json
from collections.abc import Iterable
from typing import TextIO

EXPORT_FIELDS = (
    "lead_id",
    "name",
    "business_type",
    "score",
    "score_reason",
    "location",
    "website",
    "social_url",
    "email",
    "phone",
    "source_url",
    "status",
    "created_at",
)


def write_csv(output: TextIO, records: Iterable[dict[str, object]]) -> None:
    """Write the documented CSV header even when no records are available."""

    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, extrasaction="raise")
    writer.writeheader()
    for record in records:
        writer.writerow({field: _csv_value(record[field]) for field in EXPORT_FIELDS})


def _csv_value(value: object) -> str | int:
    if value is None:
        return ""
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return value
    return str(value)
