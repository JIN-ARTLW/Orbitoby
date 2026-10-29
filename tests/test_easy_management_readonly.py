import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def __init__(self):
        self.closed = False
        self.artifact_filters = None
        self.plugin_calls = 0

    def artifacts(self, *, source=None, dataset=None, norad_id=None):
        self.artifact_filters = (source, dataset, norad_id)

        return pd.DataFrame(
            [
                {
                    "artifact_id": "raw-1",
                    "source": "gfz",
                    "dataset": "kp",
                    "norad_id": 39452,
                    "retrieved_at": pd.Timestamp("2024-05-10T00:00:00Z"),
                    "path": "/Users/private-user/raw.json",
                    "metadata": {"params": {"token": "PRIVATE_SECRET"}},
                    "request_url": ("https://example.org/data?token=PRIVATE_SECRET"),
                    "sha256": "abc123",
                }
            ]
        )

    def plugin_candidates(self):
        self.plugin_calls += 1

        return [
            {
                "name": "example-plugin",
                "distribution": "example-package",
                "status": "candidate",
                "credentials": "PRIVATE_SECRET",
                "secret": "PRIVATE_SECRET",
            }
        ]

    def close(self):
        self.closed = True


@pytest.fixture
def fake_archive(monkeypatch):
    from orbitoby import service

    archive = FakeArchive()

    monkeypatch.setattr(
        service,
        "Archive",
        lambda: archive,
    )

    return archive


def test_artifacts_preserve_public_identifiers(fake_archive):
    result = ob.artifacts(
        source="gfz",
        dataset="kp",
        norad_id=39452,
    )

    assert len(result) == 1

    row = result.table.iloc[0]

    assert row["artifact_id"] == "raw-1"
    assert row["source"] == "gfz"
    assert row["dataset"] == "kp"
    assert row["norad_id"] == 39452
    assert row["sha256"] == "abc123"

    assert fake_archive.artifact_filters == (
        "gfz",
        "kp",
        39452,
    )
    assert fake_archive.closed


def test_artifact_private_fields_are_not_exposed(fake_archive, capsys):
    result = ob.artifacts()

    assert "path" not in result.table
    assert "metadata" not in result.table
    assert "request_url" not in result.table

    result.show()
    printed = capsys.readouterr().out
    serialized = result.table.to_string()

    for forbidden in (
        "PRIVATE_SECRET",
        "/Users/private-user",
        "request_url",
    ):
        assert forbidden not in printed
        assert forbidden not in serialized


def test_plugins_are_candidates_not_automatic_trust(fake_archive, capsys):
    result = ob.plugins()

    assert fake_archive.plugin_calls == 1
    assert fake_archive.closed

    row = result.table.iloc[0]

    assert row["name"] == "example-plugin"
    assert "candidate" in row["meaning"]

    result.show()
    output = capsys.readouterr().out

    assert "PRIVATE_SECRET" not in output
    assert "credentials" not in result.table


@pytest.mark.parametrize("invalid", [0, -1, True, "39452"])
def test_invalid_artifact_identifier_rejected(invalid):
    with pytest.raises(ValueError, match="positive integer"):
        ob.artifacts(norad_id=invalid)


def test_management_help_is_available(capsys):
    ob.help("artifacts")
    assert "ob.artifacts().show()" in capsys.readouterr().out

    ob.help("plugins")
    assert "ob.plugins().show()" in capsys.readouterr().out

    ob.help("all")
    output = capsys.readouterr().out

    assert "ob.artifacts(" in output
    assert "ob.plugins(" in output
