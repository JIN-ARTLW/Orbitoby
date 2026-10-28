import importlib

import pytest

import orbitoby as ob


def test_sources_remains_importable_package():
    package = importlib.import_module("orbitoby.sources")

    assert ob.sources is package
    assert callable(ob.sources)
    assert hasattr(package, "__path__")


def test_real_offline_registration():
    providers = ob.sources()
    records = ob.datasets()

    assert len(providers) > 0
    assert len(records) > 0
    assert {"name"}.issubset(providers.table.columns)
    assert {"source"}.issubset(records.table.columns)


def test_gfz_provider_lookup_is_case_insensitive():
    upper = ob.source("GFZ").table
    lower = ob.source("gfz").table

    assert upper.to_dict("records") == lower.to_dict("records")


def test_missing_provider_is_not_silently_replaced():
    with pytest.raises(ValueError, match="Unknown source"):
        ob.source("provider-that-does-not-exist")


def test_unknown_dataset_is_not_silently_replaced():
    with pytest.raises(ValueError, match="not registered"):
        ob.dataset("dataset-that-does-not-exist")


def test_live_discovery_requires_narrowing():
    with pytest.raises(ValueError, match="live=True"):
        ob.datasets(live=True)


def test_help_all_contains_live_registry(capsys):
    ob.help("all")
    output = capsys.readouterr().out

    assert "ob.sources()" in output
    assert "ob.datasets(" in output
    assert "등록된 제공기관" in output
    assert "등록된 데이터셋" in output
    assert "gfz" in output.casefold()
