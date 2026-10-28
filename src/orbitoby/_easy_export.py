"""Conservative export of shareable scientific result data."""

import json
import re
from pathlib import Path

_PRIVATE_COLUMN = re.compile(
    r"(?:^|_)(?:context|password|passwd|secret|token|"
    r"api_key|cookie|authorization|credential|session|"
    r"private_url|request_url|headers)(?:_|$)",
    re.IGNORECASE,
)

_PRIVATE_CONTENT = re.compile(
    r"https?://|"
    r"\bbearer\s+\S+|"
    r"\b(?:password|secret|token|api_key|access_token)"
    r"\s*[:=]\s*\S+",
    re.IGNORECASE,
)


def export_result_csv(result, filename):
    """Export flat scientific fields, never raw structured context."""
    path = Path(filename)

    if path.suffix.lower() != ".csv":
        raise ValueError("Use a .csv filename.")

    frame = result.table
    kept = []
    excluded = []

    for name in frame.columns:
        column = frame[name]

        if _PRIVATE_COLUMN.search(str(name)):
            excluded.append(str(name))
            continue

        if any(isinstance(value, (dict, list, tuple, set, bytes)) for value in column):
            excluded.append(str(name))
            continue

        # Fail closed rather than accidentally writing an
        # authenticated or unreviewed URL into a shared file.
        if any(
            _PRIVATE_CONTENT.search(value) for value in column if isinstance(value, str)
        ):
            raise ValueError(
                f"Column {name!r} contains potentially private "
                "text or URLs. CSV export was stopped."
            )

        kept.append(name)

    if not kept:
        raise ValueError("No safely exportable columns were found.")

    public = frame.loc[:, kept]
    public.to_csv(path, index=False)

    metadata_path = path.with_name(path.stem + "_export.json")

    metadata = {
        "name": str(result.name),
        "requested_source": str(result.requested_source),
        "start": str(result.start),
        "end": str(result.end),
        "time_convention": (
            "not applicable: archive-wide identity lookup"
            if getattr(result, "_archive_scope", False)
            else "UTC [start, end)"
        ),
        "interpolation": "none by Easy API",
        "exported_columns": [str(name) for name in kept],
        "excluded_columns": excluded,
        "raw_archive_replaced": False,
    }

    # Do not write even metadata if its identifiers contain
    # a potentially sensitive value.
    for key in ("name", "requested_source", "start", "end"):
        if _PRIVATE_CONTENT.search(metadata[key]):
            path.unlink(missing_ok=True)
            raise ValueError(
                "Export metadata may contain private information. "
                "CSV export was stopped."
            )

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Saved data:", path)
    print("Saved export metadata:", metadata_path)

    if excluded:
        print("Excluded from shared CSV:", ", ".join(excluded))

    return path
