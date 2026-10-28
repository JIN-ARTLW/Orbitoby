import pandas as pd
import pytest

from orbitoby._easy_result import SourceList
from orbitoby._easy_sources import source_table


def sample_frame():
    return pd.DataFrame(
        {
            "metric": ["kp", "dst", "f107_observed"],
            "source": ["gfz", "wdc_kyoto", "gfz"],
            "dataset": ["kp", "dst_hourly", "f107_observed"],
            "retrieved_at": ["2026-10-27"] * 3,
        }
    )


def test_verified_sources():
    table = source_table(sample_frame())

    assert len(table) == 3

    kp = table.loc[table["metric"] == "kp"].iloc[0]
    dst = table.loc[table["metric"] == "dst"].iloc[0]
    f107 = table.loc[table["metric"] == "f107_observed"].iloc[0]

    assert kp["data_page"] == "https://kp.gfz.de/en/data"
    assert "13" in kp["observed_by"]
    assert dst["source"] == "wdc_kyoto"
    assert f107["observed_by"] == "not declared"


def test_unknown_source_is_not_invented():
    frame = pd.DataFrame(
        {
            "metric": ["example"],
            "source": ["unknown_private_source"],
            "dataset": ["example"],
        }
    )

    result = source_table(frame).iloc[0]

    assert result["provider_site"] is None
    assert result["data_page"] is None
    assert result["observed_by"] == "not declared"


def test_open_requires_source_choice():
    sources = SourceList(sample_frame(), "recommended")

    with pytest.raises(ValueError, match="Multiple source pages"):
        sources.open()


def test_open_uses_public_page(monkeypatch):
    visited = []
    monkeypatch.setattr("webbrowser.open", lambda url: visited.append(url))

    sources = SourceList(sample_frame(), "recommended")
    url = sources.open("Kp")

    assert url == "https://kp.gfz.de/en/data"
    assert visited == [url]
