from __future__ import annotations

import duckdb

from orbitoby.config import DB_PATH, ensure_data_dirs


def connect_db() -> duckdb.DuckDBPyConnection:
    ensure_data_dirs()

    con = duckdb.connect(str(DB_PATH))

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id VARCHAR PRIMARY KEY,
            source VARCHAR NOT NULL,
            dataset VARCHAR NOT NULL,
            norad_id INTEGER,
            requested_start DATE,
            requested_end DATE,
            retrieved_at TIMESTAMPTZ NOT NULL,
            sha256 VARCHAR NOT NULL,
            path VARCHAR NOT NULL
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage (
            source VARCHAR NOT NULL,
            dataset VARCHAR NOT NULL,
            norad_id INTEGER,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            artifact_id VARCHAR NOT NULL
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS orbit_elements (
            gp_id BIGINT PRIMARY KEY,
            norad_id INTEGER NOT NULL,

            object_id VARCHAR,
            object_name VARCHAR,

            epoch TIMESTAMP NOT NULL,

            mean_motion DOUBLE,
            eccentricity DOUBLE,
            inclination_deg DOUBLE,
            raan_deg DOUBLE,
            arg_pericenter_deg DOUBLE,
            mean_anomaly_deg DOUBLE,
            bstar DOUBLE,

            semimajor_axis_km DOUBLE,
            period_min DOUBLE,
            apoapsis_km DOUBLE,
            periapsis_km DOUBLE,

            tle_line1 VARCHAR,
            tle_line2 VARCHAR,

            source VARCHAR NOT NULL,
            artifact_id VARCHAR NOT NULL
        )
        """
    )

    con.execute(
        """
        CREATE INDEX IF NOT EXISTS orbit_lookup
        ON orbit_elements (norad_id, epoch)
        """
    )

    from orbitoby.warehouse.identity import SCHEMA

    con.execute(SCHEMA)
    return con
