import duckdb

from orbitoby import service


class FakeScientificStore:
    def __init__(self, con):
        self.con = con


class FakeProductStore:
    def __init__(self, con):
        self.con = con


def test_archive_stores_share_main_connection(
    monkeypatch,
):
    con = duckdb.connect(":memory:")

    monkeypatch.setattr(
        service,
        "connect_db",
        lambda: con,
    )

    monkeypatch.setattr(
        service,
        "ScientificStore",
        FakeScientificStore,
    )

    monkeypatch.setattr(
        service,
        "ProductStore",
        FakeProductStore,
    )

    monkeypatch.setattr(
        service,
        "build_sources",
        lambda *, credentials: {},
    )

    archive = service.Archive()

    try:
        assert archive.con is con

        assert archive.scientific_store.con is archive.con

        assert archive.product_store.con is archive.con

    finally:
        archive.close()
