"""Conservative public metadata for archived provider requests."""

from datetime import date, datetime


def safe_request_metadata(params):
    """Never serialize arbitrary provider request parameters."""
    public = {}

    for key in ("start", "end"):
        value = params.get(key)
        if isinstance(value, (date, datetime)):
            public[key] = value.isoformat()

    for key in ("norad_id", "limit", "local_limit", "offset"):
        value = params.get(key)

        if isinstance(value, bool):
            continue

        if isinstance(value, int) and value >= 0:
            public[key] = value
        elif (
            isinstance(value, str)
            and value.isascii()
            and value.isdecimal()
            and len(value) <= 12
        ):
            public[key] = int(value)

    return {
        "params": public,
        "metadata_policy": "public_allowlist_v1",
        "additional_options_omitted": len(params) > len(public),
    }
