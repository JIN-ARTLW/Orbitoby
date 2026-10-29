import pandas as pd
import pytest

from orbitoby._easy_result import DataResult, OrbitResult


@pytest.mark.parametrize(
    "verified_ids",
    [
        ("verified-a1",),
        (),
    ],
)
def test_orbit_plot_preserves_only_parent_verified_lineage(monkeypatch, verified_ids):
    frame = pd.DataFrame(
        {
            "epoch": pd.to_datetime(
                [
                    "2019-11-01T00:00:00Z",
                    "2019-11-02T00:00:00Z",
                ],
                utc=True,
            ),
            "norad_id": [22, 22],
            "mean_motion": [14.1, 14.2],
            "source": ["spacetrack", "spacetrack"],
            "artifact_id": [
                "untrusted-column-id",
                "untrusted-column-id",
            ],
        }
    )

    orbit = OrbitResult(
        frame,
        name="historical orbit",
        start="2019-11-01",
        end="2019-11-03",
        source="spacetrack",
        archive=None,
        norad_ids=(22,),
    )

    orbit._raw_artifact_ids = verified_ids
    captured = {}

    def capture(self, **kwargs):
        captured["result"] = self
        captured["kwargs"] = kwargs
        return "plot-captured"

    monkeypatch.setattr(DataResult, "plot", capture)

    output = orbit.plot("mean_motion")
    assert output == "plot-captured"

    plotted = captured["result"]

    assert plotted._raw_artifact_ids == verified_ids
    assert plotted.table["source"].eq("spacetrack").all()
    assert plotted.table["dataset"].eq("gp_history").all()

    assert plotted.table["plot_label"].str.contains("NORAD 22", regex=False).all()

    assert plotted.table["plot_label"].str.contains("spacetrack", regex=False).all()

    if verified_ids:
        assert plotted.provenance["artifact_id"].tolist() == ["verified-a1"]
    else:
        assert plotted.provenance.empty
