# 저장소와 cache / Storage and cache

기본 `~/.orbitoby`, import 전 `ORBITOBY_DATA_DIR` 환경변수로 변경합니다. raw payload+manifest는 `raw/`, DuckDB metadata는 `warehouse/archive.duckdb`, canonical Parquet는 `warehouse/canonical/`, 모델/파생 Parquet는 product store 경로에 저장됩니다. `Archive.scientific_store`, `Archive.product_store`, `Archive.con`으로 고급 조회를 수행할 수 있습니다.

Set ORBITOBY_DATA_DIR before import to override ~/.orbitoby. Raw payloads/manifests, DuckDB metadata and canonical/product Parquet files are separate. Advanced access is available through scientific_store, product_store and con.

`artifacts(source=..., dataset=..., norad_id=...)`는 raw ID·SHA-256·조회 시각·경로를, `coverage(...)`는 historical orbit 요청 ledger를 보여줍니다. 성공한 빈 요청도 coverage로 남을 수 있으므로 실제 관측 coverage로 해석하지 않습니다. canonical cache는 metric/source/dataset/transform별 요청 구간과 파일을 검증해 부족한 구간만 요청합니다.

artifacts() exposes raw IDs, hashes, retrieval times and paths. coverage() is the historical-orbit request ledger, not proof of observations. Canonical caching tracks request intervals and verified files per metric/source/dataset/transform, fetching uncovered ranges only.

`archive_raw=False`는 raw·영속 cache를 우회하므로 결과 provenance가 불완전할 수 있습니다. 기본 cache 조회는 provider가 이후 수정한 값을 자동 갱신하지 않습니다. 재현 연구에는 archive snapshot, 소프트웨어 버전, 원본 hash, query, 모델 parameters를 보존하세요. 현재 일반 refresh/migration/backup CLI는 없습니다.

archive_raw=False bypasses archival/cache paths and can lack artifact provenance. Cached queries do not automatically refresh later provider revisions. Preserve archive snapshots, software versions, raw hashes, queries and model parameters. No general refresh/migration/backup CLI is provided.

`ScientificStore.write/read_store/query/query_coverage/missing_ranges/record_coverage`는 저수준 canonical 저장 API입니다. `ProductStore.write/read_product/lineage`는 파생·모델 산출물 및 검증된 parent를 저장·조회합니다. `ProductParent(parent_kind,parent_id,role)`의 kind는 raw_artifact/scientific_file/derived_product입니다. 존재하지 않는 parent는 거부합니다. 직접 DB 변경은 검증 절차를 우회하므로 연구용 일반 경로는 Archive를 사용하세요.

ScientificStore exposes low-level canonical persistence; ProductStore exposes derived/model persistence and lineage. Parent kinds are raw_artifact, scientific_file and derived_product; unknown parents are rejected. Direct DB changes bypass validation; prefer Archive for ordinary research.

동일 DuckDB에 두 프로세스가 쓰면 lock 실패할 수 있습니다. workflow와 진단은 순차 실행하세요. 전체 archive를 복사하려면 writer를 먼저 닫으세요.

Concurrent writers can fail on DuckDB locks. Run workflow and diagnostics sequentially; close writers before copying an archive.
