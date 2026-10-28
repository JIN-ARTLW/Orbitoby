"""Beginner management commands delegating to existing Archive Core."""

import ipaddress
from urllib.parse import urlsplit

import pandas as pd

from orbitoby._easy_discovery import CatalogList, _read_archive


def _nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value.strip()


def _public_url(url):
    url = _nonempty(url, "url")
    parsed = urlsplit(url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Use a public HTTPS URL.")

    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(
            "Do not register embedded credentials, URL queries "
            "or fragments through the beginner API."
        )

    hostname = parsed.hostname.lower()

    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Local addresses are not allowed.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Private or reserved IP addresses are not allowed.")

    return url


def _catalog(value, title):
    if isinstance(value, pd.DataFrame):
        records = value.to_dict("records")
    elif isinstance(value, list):
        records = [
            dict(item) if isinstance(item, dict) else {"name": item} for item in value
        ]
    elif isinstance(value, dict):
        records = [value]
    else:
        raise TypeError("Core returned an unsupported management report type.")

    return CatalogList(records, title=title)


def add_source(
    name,
    url=None,
    *,
    dataset=None,
    format="json",
    root_key=None,
    homepage=None,
    description_en="",
    description_ko="",
):
    """Register a declared native HTTP product, not a canonical series."""
    name = _nonempty(name, "name")
    dataset = _nonempty(dataset, "dataset")
    url = _public_url(url)

    if format not in {"json", "csv"}:
        raise ValueError("Supported native formats: json, csv.")

    if homepage is not None:
        homepage = _public_url(homepage)

    def register(archive):
        names = archive.register_http_source(
            name=name,
            dataset=dataset,
            url=url,
            format=format,
            root_key=root_key,
            homepage=homepage,
            description_en=description_en,
            description_ko=description_ko,
        )
        return _catalog(names, "Registered sources after addition")

    result = _read_archive(register)
    print("Native source registered. No scientific field mapping was inferred.")
    print("Existing studies may need to be recreated to see the change.")
    return result


def remove_source(name, *, dataset=None):
    """Unregister a custom HTTP source; do not delete raw artifacts."""
    name = _nonempty(name, "name")

    if dataset is not None:
        dataset = _nonempty(dataset, "dataset")

    result = _read_archive(
        lambda archive: _catalog(
            archive.unregister_http_source(name, dataset=dataset),
            "Registered sources after removal",
        )
    )

    print("Source registration updated. Archived data was not deleted by this command.")
    return result


def refresh_sources():
    """Refresh a Core source registry snapshot."""
    result = _read_archive(
        lambda archive: _catalog(
            archive.reload_sources(),
            "Refreshed source registry",
        )
    )

    print("Create a new study to use the refreshed source registry.")
    return result


def trust_plugin(name, *, confirm=False):
    """Trust a discovered plugin only after explicit user approval."""
    name = _nonempty(name, "name")

    if confirm is not True:
        raise ValueError(
            "A trusted plugin can execute Python code. "
            f"Review ob.plugins().show(), then use "
            f"ob.trust_plugin({name!r}, confirm=True) to approve."
        )

    def trust(archive):
        candidates = archive.plugin_candidates()
        names = {item.get("name") for item in candidates}

        if name not in names:
            raise ValueError(f"Plugin {name!r} is not a discovered candidate.")

        return _catalog(
            archive.trust_source_plugin(name),
            "Registered sources after plugin trust",
        )

    return _read_archive(trust)


def untrust_plugin(name):
    """Revoke an existing plugin's trusted status."""
    name = _nonempty(name, "name")

    return _read_archive(
        lambda archive: _catalog(
            archive.untrust_source_plugin(name),
            "Registered sources after plugin untrust",
        )
    )


def rebuild_index(
    *,
    source=None,
    dataset=None,
    batch_size=500,
    progress=True,
):
    """Reindex existing raw artifacts without refetching source data."""
    if (
        isinstance(batch_size, bool)
        or not isinstance(batch_size, int)
        or batch_size <= 0
    ):
        raise ValueError("batch_size must be a positive integer.")

    if not isinstance(progress, bool):
        raise TypeError("progress must be a boolean.")

    result = _read_archive(
        lambda archive: _catalog(
            archive.reindex(
                source=source,
                dataset=dataset,
                batch_size=batch_size,
                progress=progress,
            ),
            "Raw artifact reindex report",
        )
    )

    print("Reindex completed; review the report for per-artifact failures.")
    return result
