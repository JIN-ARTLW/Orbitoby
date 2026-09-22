from __future__ import annotations

import io
from typing import Any

import pandas as pd
import requests

from space_object_archive.sources.base import SourceAdapter


class GCATSource(SourceAdapter):
    name = "gcat"

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

    BASE_URL = (
        "https://planet4589.org/"
        "space/gcat/tsv/cat"
    )

    def __init__(self) -> None:
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent":
                    "space-object-archive/0.1"
            }
        )

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:

        if dataset not in self.datasets:
            raise ValueError(
                f"Unsupported GCAT dataset: "
                f"{dataset}"
            )

        url = (
            f"{self.BASE_URL}/"
            f"{dataset}.tsv"
        )

        response = self.session.get(
            url,
            timeout=180,
        )

        response.raise_for_status()

        return response.content

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:

        df = pd.read_csv(
            io.BytesIO(
                payload
            ),
            sep="\t",
            comment="#",
            dtype=str,
            low_memory=False,
        )

        df = df.where(
            pd.notnull(df),
            None,
        )

        return df.to_dict(
            orient="records"
        )