import pandas as pd
import pytest

import orbitoby as ob
from orbitoby.research import ResearchWindow


class FakeArchive:
    def __init__(self, wrong_source=False):
        self.calls = []
        self.wrong_source = wrong_source

    def window(self, **kwargs):
        self.calls.append(kwargs)

        times = pd.to_datetime(
            ["2024-05-10T00:00:00Z", "2024-05-10T03:00:00Z"],
            utc=True,
        )

        metrics = kwargs["fields"]

        values = pd.DataFrame({"timestamp": times})
        presence = pd.DataFrame({"timestamp": times})
        missing = pd.DataFrame({"timestamp": times})
        rows = []

        for metric in metrics:
            values[metric] = [1.0, 2.0]
            presence[metric] = [True, True]
            missing[metric] = [None, None]

            provider = "wdc_kyoto" if metric == "dst" else "gfz"

            if self.wrong_source:
                provider = "other"

            for timestamp in times:
                rows.append(
                    {
                        "timestamp": timestamp,
                        "metric": metric,
                        "source": provider,
                        "dataset": metric,
                        "unit": "test",
                    }
                )

        return ResearchWindow(
            data=values,
            presence=presence,
            missing_reason=missing,
            provenance=pd.DataFrame(rows),
            units={metric: "test" for metric in metrics},
        )


def test_multiple_weather():
    study = ob.study("2024-05-10", "2024-05-20")
    fake = FakeArchive()
    study._archive = fake

    result = study.weather("F10.7", "Kp", "Dst")

    assert len(result.table) == 2
    assert len(result.provenance) == 6
    assert set(result.units) == {"f107_observed", "kp", "dst"}
    assert fake.calls[0]["source_preference"] == ("gfz", "wdc_kyoto")


def test_metadata_is_preserved(tmp_path):
    study = ob.study("2024-05-10", "2024-05-20")
    study._archive = FakeArchive()

    result = study.weather("Kp", "Dst")
    result.save(tmp_path / "weather.csv")

    assert (tmp_path / "weather.csv").exists()
    assert (tmp_path / "weather_provenance.csv").exists()
    assert (tmp_path / "weather_presence.csv").exists()
    assert (tmp_path / "weather_missing.csv").exists()
    assert (tmp_path / "weather_metadata.json").exists()


def test_unexpected_provider_is_rejected():
    study = ob.study("2024-05-10", "2024-05-20")
    study._archive = FakeArchive(wrong_source=True)

    with pytest.raises(ValueError, match="unexpected source"):
        study.weather("Kp", "Dst")
