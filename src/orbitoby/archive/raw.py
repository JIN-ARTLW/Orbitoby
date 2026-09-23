from __future__ import annotations

import hashlib
import json

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from orbitoby.config import RAW_DIR


@dataclass(frozen=True, slots=True)
class RawArtifact:
    artifact_id: str
    source: str
    dataset: str
    norad_id: int | None
    requested_start: date | None
    requested_end: date | None
    retrieved_at: datetime
    sha256: str
    path: Path


def save_raw_artifact(
    *,
    source: str,
    dataset: str,
    payload: bytes,
    norad_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    metadata: dict | None = None,
    extension: str = "json",
) -> RawArtifact:
    retrieved_at = datetime.now(timezone.utc)

    # 원본 파일이 같은지 확인할 수 있는 fingerprint
    sha256 = hashlib.sha256(payload).hexdigest()

    artifact_id = (
        f"{retrieved_at:%Y%m%dT%H%M%SZ}_"
        f"{sha256[:12]}_{uuid4().hex}"
    )

    object_dir = (
        f"norad={norad_id}"
        if norad_id is not None
        else "global"
    )

    year_dir = (
        str(start.year)
        if start is not None
        else str(retrieved_at.year)
    )

    directory = (
        RAW_DIR
        / source
        / dataset
        / object_dir
        / year_dir
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload_path = directory / f"{artifact_id}.{extension}"

    # API 원본 그대로 저장
    payload_path.write_bytes(payload)

    manifest_path = (
        directory
        / f"{artifact_id}.manifest.json"
    )

    manifest = {
        "artifact_id": artifact_id,
        "source": source,
        "dataset": dataset,
        "norad_id": norad_id,
        "requested_start": start.isoformat() if start else None,
        "requested_end": end.isoformat() if end else None,
        "retrieved_at": retrieved_at.isoformat(),
        "sha256": sha256,
        "payload_path": str(payload_path),
        "metadata": metadata or {},
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return RawArtifact(
        artifact_id=artifact_id,
        source=source,
        dataset=dataset,
        norad_id=norad_id,
        requested_start=start,
        requested_end=end,
        retrieved_at=retrieved_at,
        sha256=sha256,
        path=payload_path,
    )
