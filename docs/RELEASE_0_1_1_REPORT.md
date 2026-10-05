# Orbitoby v0.1.1 Release Validation Report

Date: 2026-10-05

## Scope

Orbitoby v0.1.1 is a compatibility patch release for the v0.1.0 Science Day workflow.

The release does not introduce a new research workflow. It preserves the v0.1.0 workflow while fixing the dependency minimums that caused unnecessary upgrades in Google Colab and exposing `orbitoby.__version__`.

## Package changes

- Version: `0.1.0` -> `0.1.1`
- Runtime dependency minimums:
  - `duckdb>=1.3.2`
  - `pandas>=2.2.3`
  - `pyarrow>=23.0.1`
  - `python-dotenv>=1.2.3`
  - `pytz>=2025.2`
  - `requests>=2.32.4`
- Optional models extra:
  - `pymsis>=0.13,<0.14`
- Public package version:
  - `orbitoby.__version__`

## Regression validation

Latest dependency environment:

- Ruff: PASS
- Ruff format: PASS
- Full test suite: 284 passed

Colab-baseline minimum dependency environment:

- Python 3.12 local minimum-environment regression: 284 passed
- `pymsis==0.13.0`: PASS
- `Archive.msis_inputs`: PASS
- `Archive.msis_density`: PASS

## Built-wheel compatibility validation

A clean environment was created with the tested Colab-compatible baseline:

- `numpy==2.1.3`
- `duckdb==1.3.2`
- `pandas==2.2.3`
- `pyarrow==23.0.1`
- `python-dotenv==1.2.3`
- `pytz==2025.2`
- `requests==2.32.4`

The locally built `orbitoby-0.1.1-py3-none-any.whl` was then installed with normal dependency resolution.

Results:

- Orbitoby installed as `0.1.1`: PASS
- Existing compatible baseline packages remained unchanged: PASS
- `uv pip check`: PASS
- `pymsis==0.13.0`: PASS
- Science Day public API smoke: PASS

Wheel metadata:

- `Requires-Python: >=3.12`
- `duckdb>=1.3.2`
- `pandas>=2.2.3`
- `pyarrow>=23.0.1`
- `python-dotenv>=1.2.3`
- `pytz>=2025.2`
- `requests>=2.32.4`
- `pymsis>=0.13,<0.14 ; extra == 'models'`

## Live provider validation

Connection diagnostic:

- CelesTrak: PASS
- GFZ: PASS
- NRCan: PASS
- WDC Kyoto: PASS
- Swarm: PASS
- NOAA: PASS
- Space-Track: PASS
- CDAWeb quick capability probe: WARN deadline exceeded
- DISCOS: SKIP credential not configured

The CDAWeb warning did not block the actual OMNI data path.

## Science Day end-to-end validation

`examples/science_day.py --allow-dotenv` completed successfully.

Observed results:

- Population: 13,142 rows
- Historical orbit screening: PASS
- F10.7 observed: 1 row
- Kp: 8 rows
- ap: 8 rows
- daily Ap: 1 row
- Dst: 24 rows
- Solar-wind speed: 24 rows
- Density comparison: 2,880 rows
- Exact timestamp matches: 2,880
- Timestamp mismatches: 0
- Observed missing flags: 0
- Model missing flags: 0

## Colab delivery

Added:

- `.github/workflows/ci.yml`
- `docs/COLAB.md`
- `examples/science_day_colab.ipynb`
- `WORKFLOW.md` v0.1.1 compatibility notes
- package metadata version regression test

The Colab notebook is designed for:

1. fresh Google Colab runtime
2. no repository clone
3. `%pip install "orbitoby[models]==0.1.1"`
4. Space-Track credentials through Colab Secrets
5. the same v0.1.0 Science Day workflow
6. exact observed/model comparison with provenance separation

Notebook validation:

- JSON: PASS
- Python cell syntax: PASS
- Ruff: PASS
- Ruff format: PASS

## Remaining release acceptance

Before declaring the public release complete:

1. push the hotfix branch
2. obtain GitHub CI green
3. merge through the normal release process
4. publish v0.1.1
5. open a completely fresh Google Colab runtime
6. install `orbitoby[models]==0.1.1` from PyPI
7. run `examples/science_day_colab.ipynb` end-to-end
8. confirm Colab dependency preservation and Science Day workflow PASS

The existing public v0.1.0 release remains immutable.
