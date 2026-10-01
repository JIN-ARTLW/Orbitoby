from __future__ import annotations

from datetime import date, timedelta

import duckdb


def missing_ranges(
    con: duckdb.DuckDBPyConnection,
    *,
    source: str,
    dataset: str,
    norad_id: int,
    start: date,
    end: date,
) -> list[tuple[date, date]]:
    """
    요청한 기간 중 로컬 archive에 아직 없는 날짜 구간을 반환한다.

    예:
        보유: 2020-01-01 ~ 2020-01-31
        요청: 2020-01-15 ~ 2020-02-29

        반환:
        [(2020-02-01, 2020-02-29)]
    """

    if start > end:
        raise ValueError("start must be <= end")

    rows = con.execute(
        """
        SELECT start_date, end_date
        FROM coverage
        WHERE source = ?
          AND dataset = ?
          AND norad_id = ?
          AND end_date >= ?
          AND start_date <= ?
        ORDER BY start_date, end_date
        """,
        [
            source,
            dataset,
            norad_id,
            start,
            end,
        ],
    ).fetchall()

    # 아무것도 보유하고 있지 않으면 전체 기간이 필요함
    if not rows:
        return [(start, end)]

    missing: list[tuple[date, date]] = []

    cursor = start

    for covered_start, covered_end in rows:
        # 요청 시작 이전에 끝난 coverage는 무시
        if covered_end < cursor:
            continue

        # cursor와 다음 coverage 사이에 빈 구간이 존재
        if covered_start > cursor:
            gap_end = min(
                end,
                covered_start - timedelta(days=1),
            )

            if cursor <= gap_end:
                missing.append((cursor, gap_end))

        # 이미 보유한 구간을 건너뜀
        cursor = max(
            cursor,
            covered_end + timedelta(days=1),
        )

        if cursor > end:
            break

    # 마지막 coverage 이후에도 요청 기간이 남아 있는 경우
    if cursor <= end:
        missing.append((cursor, end))

    return missing
