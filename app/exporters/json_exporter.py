"""UTF-8 JSON rendering for reviewable lead records."""

import json
from collections.abc import Iterable
from typing import TextIO


def write_json(output: TextIO, records: Iterable[dict[str, object]]) -> None:
    """Write a valid JSON array, including for an empty export."""

    json.dump(list(records), output, ensure_ascii=False, indent=2)
    output.write("\n")
