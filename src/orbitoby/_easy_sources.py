"""Public data-source references for beginner results."""

from urllib.parse import urlsplit

import pandas as pd

from orbitoby.sources.metadata import builtin_source_metadata

_DATA_PAGES = {
    "gfz": "https://kp.gfz.de/en/data",
    "wdc_kyoto": "https://wdc.kugi.kyoto-u.ac.jp/dstdir/",
}

_ORIGINS = {
    ("gfz", "kp"): (
        "13 contributing geomagnetic observatories",
        "GFZ Kp index production",
        "https://kp.gfz.de/en/about-kp",
    ),
    ("wdc_kyoto", "dst"): (
        "Kakioka, Honolulu, San Juan, Hermanus observatories",
        "WDC for Geomagnetism, Kyoto",
        "https://wdc.kugi.kyoto-u.ac.jp/dstdir/dst2/onDstindex.html",
    ),
}


def _public_homepage(metadata):
    """Accept only safe, registered public provider homepages."""
    if metadata is None:
        return None

    url = metadata.homepage
    parsed = urlsplit(url)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        return None

    allowed = metadata.host_allowlist
    if allowed and parsed.hostname not in allowed:
        return None

    return url


def source_table(frame):
    """Describe actual contributing sources, without guessing origins."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Source information requires a DataFrame.")

    columns = [
        "metric",
        "source",
        "dataset",
        "provider",
        "provider_site",
        "data_page",
        "observed_by",
        "produced_by",
        "origin_reference",
        "retrieved_at",
    ]

    if frame.empty:
        return pd.DataFrame(columns=columns)

    working = pd.DataFrame(index=frame.index)

    working["metric"] = frame.get("metric", "not declared")

    if "source" in frame:
        working["source"] = frame["source"]
    elif "catalogue_source" in frame:
        working["source"] = frame["catalogue_source"]
    else:
        working["source"] = "not declared"

    working["dataset"] = frame.get("dataset", "not declared")

    time_column = (
        "retrieved_at" if "retrieved_at" in frame else "catalogue_retrieved_at"
    )

    working["retrieved_at"] = frame.get(time_column)

    for column in ("metric", "source", "dataset"):
        working[column] = working[column].fillna("not declared").astype(str)

    metadata = builtin_source_metadata()
    output = []

    for (metric, source, dataset), group in working.groupby(
        ["metric", "source", "dataset"], sort=True
    ):
        provider = metadata.get(source)
        origin = _ORIGINS.get((source, metric))

        parts = dataset.split("_")
        if (
            source == "swarm"
            and len(parts) == 3
            and parts[0] == "density"
            and parts[1] in {"a", "b", "c"}
            and parts[2] in {"acc", "pod"}
        ):
            producer = (
                "Orbitoby (geodetic context extraction and height conversion)"
                if metric == "swarm_trajectory"
                else "Orbitoby (Height_GD metres to kilometres)"
                if metric == "swarm_geodetic_altitude"
                else "not declared"
            )

            origin = (
                f"Swarm {parts[1].upper()} spacecraft (product platform)",
                producer,
                None,
            )

        if source == "orbitoby" and dataset == "nrlmsis_2_1_density":
            origin = (
                "not applicable (numerical model)",
                "NRLMSIS 2.1 calculation by Orbitoby",
                None,
            )

        timestamps = group["retrieved_at"].dropna().astype(str).unique()

        if len(timestamps) == 1:
            retrieved = timestamps[0]
        elif len(timestamps) > 1:
            retrieved = "multiple; see record provenance"
        else:
            retrieved = "not declared"

        output.append(
            {
                "metric": metric,
                "source": source,
                "dataset": dataset,
                "provider": (
                    provider.title
                    if provider
                    else "Orbitoby model computation"
                    if source == "orbitoby" and dataset == "nrlmsis_2_1_density"
                    else "not declared"
                ),
                "provider_site": _public_homepage(provider),
                "data_page": _DATA_PAGES.get(source),
                "observed_by": (origin[0] if origin else "not declared"),
                "produced_by": (origin[1] if origin else "not declared"),
                "origin_reference": (origin[2] if origin else None),
                "retrieved_at": retrieved,
            }
        )

    return pd.DataFrame(output, columns=columns)
