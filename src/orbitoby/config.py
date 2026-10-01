from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


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


SPACETRACK_USERNAME = os.getenv("SPACETRACK_USERNAME")
SPACETRACK_PASSWORD = os.getenv("SPACETRACK_PASSWORD")


def ensure_data_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
