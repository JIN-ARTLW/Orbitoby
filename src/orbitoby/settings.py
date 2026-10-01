from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from orbitoby.config import DATA_DIR

DEFAULT_SETTINGS: dict[str, Any] = {
    "trusted_plugins": [],
    "http_sources": [],
}

_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def settings_path() -> Path:
    return DATA_DIR / "settings.json"


def _path(
    path: str | Path | None,
) -> Path:
    if path is None:
        return settings_path()

    return Path(path).expanduser().resolve()


def load_settings(
    path: str | Path | None = None,
) -> dict[str, Any]:
    target = _path(path)

    if not target.exists():
        return deepcopy(DEFAULT_SETTINGS)

    raw = json.loads(target.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise TypeError("Orbitoby settings must be a JSON object.")

    result = deepcopy(DEFAULT_SETTINGS)

    trusted = raw.get(
        "trusted_plugins",
        [],
    )

    sources = raw.get(
        "http_sources",
        [],
    )

    if not isinstance(
        trusted,
        list,
    ):
        raise TypeError("trusted_plugins must be a list.")

    if not isinstance(
        sources,
        list,
    ):
        raise TypeError("http_sources must be a list.")

    result["trusted_plugins"] = sorted(
        {str(item) for item in trusted if str(item).strip()}
    )

    result["http_sources"] = sources

    return result


def save_settings(
    settings: dict[str, Any],
    path: str | Path | None = None,
) -> Path:
    target = _path(path)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = target.with_suffix(".json.tmp")

    temporary.write_text(
        json.dumps(
            settings,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    os.chmod(
        temporary,
        0o600,
    )

    temporary.replace(target)

    return target


def _validate_name(
    value: str,
    *,
    field: str,
) -> str:
    value = value.strip().lower()

    if not _NAME_RE.fullmatch(value):
        raise ValueError(
            f"Invalid {field}: {value!r}. Use lowercase letters, digits, '_' or '-'."
        )

    return value


def trust_plugin(
    name: str,
    *,
    path: str | Path | None = None,
) -> None:
    name = _validate_name(
        name,
        field="plugin name",
    )

    settings = load_settings(path)

    trusted = set(settings["trusted_plugins"])

    trusted.add(name)

    settings["trusted_plugins"] = sorted(trusted)

    save_settings(
        settings,
        path,
    )


def untrust_plugin(
    name: str,
    *,
    path: str | Path | None = None,
) -> None:
    settings = load_settings(path)

    settings["trusted_plugins"] = [
        item for item in settings["trusted_plugins"] if item != name
    ]

    save_settings(
        settings,
        path,
    )


def register_http_source(
    *,
    name: str,
    dataset: str,
    url: str,
    format: str = "json",
    root_key: str | None = None,
    homepage: str | None = None,
    description_en: str = "",
    description_ko: str = "",
    path: str | Path | None = None,
) -> None:
    name = _validate_name(
        name,
        field="source name",
    )

    dataset = _validate_name(
        dataset,
        field="dataset name",
    )

    format = format.strip().lower()

    if format not in {
        "json",
        "csv",
        "tsv",
    }:
        raise ValueError("format must be json, csv, or tsv")

    if not url.startswith("https://"):
        raise ValueError("Declarative HTTP sources require HTTPS.")

    definition = {
        "name": name,
        "dataset": dataset,
        "url": url,
        "format": format,
        "root_key": root_key,
        "homepage": (homepage or url),
        "description_en": (description_en),
        "description_ko": (description_ko),
    }

    settings = load_settings(path)

    definitions = [
        item
        for item in settings["http_sources"]
        if not (item.get("name") == name and item.get("dataset") == dataset)
    ]

    definitions.append(definition)

    settings["http_sources"] = sorted(
        definitions,
        key=lambda item: (
            item["name"],
            item["dataset"],
        ),
    )

    save_settings(
        settings,
        path,
    )


def unregister_http_source(
    name: str,
    *,
    dataset: str | None = None,
    path: str | Path | None = None,
) -> None:
    settings = load_settings(path)

    settings["http_sources"] = [
        item
        for item in settings["http_sources"]
        if not (
            item.get("name") == name
            and (dataset is None or item.get("dataset") == dataset)
        )
    ]

    save_settings(
        settings,
        path,
    )
