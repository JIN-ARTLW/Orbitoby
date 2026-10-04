from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar


class SourceAdapter(ABC):
    """Common interface for Orbitoby data-source adapters."""

    name: str
    datasets: tuple[str, ...] = ()
    raw_extension: str = "json"

    # Optional canonical scientific mappings exposed by
    # third-party/user adapters.  Kept untyped here to avoid
    # coupling the adapter base class back to canonical.py.
    canonical_bindings: ClassVar[tuple[object, ...]] = ()

    # Only object/catalogue datasets belong in the
    # object identity store. Scientific time series,
    # events and other datasets remain outside it.
    identity_datasets: frozenset[str] = frozenset()

    def raw_extension_for(
        self,
        dataset: str,
        **params: Any,
    ) -> str:
        """Return the raw payload extension for one request."""
        del dataset, params
        return self.raw_extension

    def should_index_identity(
        self,
        dataset: str,
    ) -> bool:
        return dataset in self.identity_datasets

    def should_index_identity_request(
        self,
        dataset: str,
        **params: Any,
    ) -> bool:
        """Return whether one provider request should enter identity storage."""
        del params
        return self.should_index_identity(dataset)

    @abstractmethod
    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        """Return the provider's raw response bytes."""
        raise NotImplementedError

    @abstractmethod
    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        """Normalize one raw response into Python records.

        This compatibility API may materialize the complete result.
        Large built-in datasets should additionally implement
        ``iter_normalized_batches`` and/or ``iter_normalized_file``.
        """
        raise NotImplementedError

    def iter_normalized_batches(
        self,
        dataset: str,
        payload: bytes,
        *,
        batch_size: int = 1000,
        **context: Any,
    ) -> Iterator[list[dict]]:
        """Yield bounded batches of normalized records.

        Default implementation preserves compatibility with existing
        adapters by calling ``normalize`` once. It is not guaranteed
        to be memory-bounded.

        Large adapters should override this method.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")

        records = self.normalize(
            dataset,
            payload,
            **context,
        )

        for start in range(0, len(records), batch_size):
            yield records[start : start + batch_size]

    def iter_normalized_file(
        self,
        dataset: str,
        path: str | Path,
        *,
        batch_size: int = 1000,
        **context: Any,
    ) -> Iterator[list[dict]]:
        """Normalize an archived file in bounded batches.

        Default implementation reads the file into memory and delegates
        to ``iter_normalized_batches``. Large adapters should override it.
        """
        payload = Path(path).read_bytes()

        yield from self.iter_normalized_batches(
            dataset,
            payload,
            batch_size=batch_size,
            **context,
        )
