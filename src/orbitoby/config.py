from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = (
    Path(
        os.getenv(
            "ORBITOBY_DATA_DIR",
            str(Path.home() / ".orbitoby"),
        )
    )
    .expanduser()
    .resolve()
)

RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
DB_PATH = WAREHOUSE_DIR / "archive.duckdb"
CANONICAL_DIR = WAREHOUSE_DIR / "canonical"


def ensure_data_dirs() -> None:
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    WAREHOUSE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    CANONICAL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
