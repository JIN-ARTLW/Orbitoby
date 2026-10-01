from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points

from orbitoby.sources.base import SourceAdapter

ENTRY_POINT_GROUP = "orbitoby.sources"


@dataclass(frozen=True, slots=True)
class PluginCandidate:
    name: str
    value: str
    distribution: str | None


def _entry_points() -> list[EntryPoint]:
    return list(entry_points(group=ENTRY_POINT_GROUP))


def discover_source_plugins() -> list[PluginCandidate]:
    """Discover plugins without importing or executing them."""
    candidates = []

    for entry_point in _entry_points():
        distribution = None

        if entry_point.dist is not None:
            distribution = entry_point.dist.name

        candidates.append(
            PluginCandidate(
                name=entry_point.name,
                value=entry_point.value,
                distribution=distribution,
            )
        )

    return sorted(
        candidates,
        key=lambda item: (
            item.name,
            item.distribution or "",
        ),
    )


def _coerce_adapter(
    loaded,
) -> SourceAdapter:
    if isinstance(
        loaded,
        SourceAdapter,
    ):
        return loaded

    if isinstance(loaded, type) and issubclass(
        loaded,
        SourceAdapter,
    ):
        return loaded()

    if callable(loaded):
        result = loaded()

        if isinstance(
            result,
            SourceAdapter,
        ):
            return result

    raise TypeError(
        "Orbitoby source plugin must expose a "
        "SourceAdapter instance, subclass, or factory."
    )


def load_trusted_source_plugins(
    trusted: set[str] | frozenset[str],
) -> dict[str, SourceAdapter]:
    """Load only entry points explicitly trusted by the user."""
    result: dict[str, SourceAdapter] = {}

    for entry_point in _entry_points():
        if entry_point.name not in trusted:
            continue

        adapter = _coerce_adapter(entry_point.load())

        if adapter.name in result:
            raise RuntimeError(f"Duplicate plugin source name: {adapter.name}")

        result[adapter.name] = adapter

    return result
