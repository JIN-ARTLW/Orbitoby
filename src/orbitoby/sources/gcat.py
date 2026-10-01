from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class GCATSource(SourceAdapter):
    name = "gcat"
    identity_datasets = frozenset(
        {
            "satcat",
            "satcat100k",
            "satcat070k",
            "satcat270k",
            "satcat700M",
            "usatcat",
            "psatcat",
            "psatcat100k",
            "psatcat270k",
            "pauxcat",
            "pdeepcat",
            "pftocat",
            "plcat",
            "prcat",
            "ptmpcat",
            "rcat",
            "lprcat",
            "vimcat",
        }
    )
    raw_extension = "tsv"

    datasets = (
        "satcat",
        "satcat100k",
        "satcat070k",
        "satcat270k",
        "satcat700M",
        "usatcat",
        "psatcat",
        "psatcat100k",
        "psatcat270k",
        "pauxcat",
        "pdeepcat",
        "pftocat",
        "plcat",
        "prcat",
        "ptmpcat",
        "rcat",
        "lprcat",
        "vimcat",
    )

    BASE_URL = "https://planet4589.org/space/gcat/tsv/cat"

    def __init__(
        self,
        *,
        http: SafeHttpClient | None = None,
    ) -> None:
        self.metadata = source_metadata(self.name)
        self.http = http or SafeHttpClient(
            allowed_hosts=(self.metadata.host_allowlist),
            read_timeout=180.0,
        )

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        self._validate_dataset(dataset)

        url = f"{self.BASE_URL}/{dataset}.tsv"

        return self.http.get(url)

    def _validate_dataset(
        self,
        dataset: str,
    ) -> None:
        if dataset not in self.datasets:
            raise ValueError(f"Unsupported GCAT dataset: {dataset}")

    @staticmethod
    def _filtered_lines(
        stream: TextIO,
    ) -> Iterator[str]:
        """Preserve #JCAT as the header and ignore other comment lines."""
        for line in stream:
            if line.startswith("\ufeff"):
                line = line.lstrip("\ufeff")

            if line.startswith("#JCAT"):
                yield line[1:]
                continue

            if line.startswith("#"):
                continue

            if not line.strip():
                continue

            yield line

    @classmethod
    def _iter_rows(
        cls,
        stream: TextIO,
    ) -> Iterator[dict]:
        reader = csv.DictReader(
            cls._filtered_lines(stream),
            delimiter="\t",
        )

        if reader.fieldnames is None:
            return

        reader.fieldnames = [field.strip() for field in reader.fieldnames]

        for raw_row in reader:
            row: dict[str, object] = {}

            for key, value in raw_row.items():
                if key is None:
                    continue

                clean_key = key.strip()

                if value is None:
                    clean_value = None
                else:
                    stripped = value.strip()
                    clean_value = stripped if stripped else None

                row[clean_key] = clean_value

            yield row

    def iter_normalized_batches(
        self,
        dataset: str,
        payload: bytes,
        *,
        batch_size: int = 1000,
        **context: Any,
    ) -> Iterator[list[dict]]:
        self._validate_dataset(dataset)

        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")

        text = io.TextIOWrapper(
            io.BytesIO(payload),
            encoding="utf-8-sig",
            newline="",
        )

        batch: list[dict] = []

        try:
            for row in self._iter_rows(text):
                batch.append(row)

                if len(batch) >= batch_size:
                    yield batch
                    batch = []

            if batch:
                yield batch

        finally:
            text.close()

    def iter_normalized_file(
        self,
        dataset: str,
        path: str | Path,
        *,
        batch_size: int = 1000,
        **context: Any,
    ) -> Iterator[list[dict]]:
        self._validate_dataset(dataset)

        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")

        batch: list[dict] = []

        with Path(path).open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            for row in self._iter_rows(stream):
                batch.append(row)

                if len(batch) >= batch_size:
                    yield batch
                    batch = []

        if batch:
            yield batch

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        """Compatibility API.

        This intentionally materializes all records. Internal archival
        ingestion should prefer the batch APIs.
        """
        records: list[dict] = []

        for batch in self.iter_normalized_batches(
            dataset,
            payload,
            batch_size=2000,
            **context,
        ):
            records.extend(batch)

        return records
