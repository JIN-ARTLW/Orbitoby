from pathlib import Path

from orbitoby.sources.gcat import GCATSource

PAYLOAD = (
    b"# metadata comment\n"
    b"#JCAT\tSatcat\tPiece\tName\tMass\tState\tStatus\tExtra\n"
    b"S00001\t25544\t1998-067A\tISS\t420000\tUS\tO\talpha\n"
    b"# another comment\n"
    b"S00002\t20580\t1990-037B\tHST\t11110\tUS\tO\tbeta\n"
)


def test_gcat_normalize_preserves_header_and_rows():
    source = GCATSource()

    records = source.normalize(
        "satcat",
        PAYLOAD,
    )

    assert len(records) == 2
    assert records[0]["JCAT"] == "S00001"
    assert records[0]["Satcat"] == "25544"
    assert records[0]["Extra"] == "alpha"


def test_gcat_batched_normalization():
    source = GCATSource()

    batches = list(
        source.iter_normalized_batches(
            "satcat",
            PAYLOAD,
            batch_size=1,
        )
    )

    assert len(batches) == 2
    assert all(len(batch) == 1 for batch in batches)


def test_gcat_file_streaming(tmp_path: Path):
    path = tmp_path / "satcat.tsv"
    path.write_bytes(PAYLOAD)

    source = GCATSource()

    batches = list(
        source.iter_normalized_file(
            "satcat",
            path,
            batch_size=2,
        )
    )

    assert len(batches) == 1
    assert len(batches[0]) == 2
    assert batches[0][1]["Name"] == "HST"


def test_invalid_gcat_dataset():
    source = GCATSource()

    try:
        source.normalize(
            "not-a-dataset",
            PAYLOAD,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_gcat_streams_seventy_thousand_rows(tmp_path: Path):
    path = tmp_path / "large_satcat.tsv"

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        stream.write("#JCAT\tSatcat\tPiece\tName\tMass\tState\tStatus\n")

        for i in range(70_000):
            norad_id = 100_000 + i
            stream.write(f"S{i:05d}\t{norad_id}\t2026-001A\tOBJECT-{i}\t100\tUS\tO\n")

    source = GCATSource()

    total = 0
    batch_count = 0
    maximum_batch = 0

    for batch in source.iter_normalized_file(
        "satcat",
        path,
        batch_size=1000,
    ):
        total += len(batch)
        batch_count += 1
        maximum_batch = max(
            maximum_batch,
            len(batch),
        )

    assert total == 70_000
    assert batch_count == 70
    assert maximum_batch == 1000
