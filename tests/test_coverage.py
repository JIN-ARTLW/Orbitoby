from datetime import date

import duckdb

from orbitoby.warehouse.coverage import (
    missing_ranges,
)


def connection():
    con = duckdb.connect(":memory:")

    con.execute(
        """
        CREATE TABLE coverage (
            source VARCHAR NOT NULL,
            dataset VARCHAR NOT NULL,
            norad_id INTEGER,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            artifact_id VARCHAR NOT NULL
        )
        """
    )

    return con


def test_missing_ranges_empty_archive():
    con = connection()

    result = missing_ranges(
        con,
        source="spacetrack",
        dataset="gp_history",
        norad_id=228,
        start=date(2020, 1, 1),
        end=date(2020, 1, 31),
    )

    assert result == [
        (
            date(2020, 1, 1),
            date(2020, 1, 31),
        )
    ]


def test_missing_ranges_after_existing_coverage():
    con = connection()

    con.execute(
        """
        INSERT INTO coverage
        VALUES (
            'spacetrack',
            'gp_history',
            228,
            DATE '2020-01-01',
            DATE '2020-01-31',
            'artifact'
        )
        """
    )

    result = missing_ranges(
        con,
        source="spacetrack",
        dataset="gp_history",
        norad_id=228,
        start=date(2020, 1, 15),
        end=date(2020, 2, 29),
    )

    assert result == [
        (
            date(2020, 2, 1),
            date(2020, 2, 29),
        )
    ]
