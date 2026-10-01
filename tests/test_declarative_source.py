import json

from orbitoby.sources.declarative import (
    DeclarativeHTTPSource,
    build_declarative_sources,
)


def make_source():
    return DeclarativeHTTPSource(
        name="demo",
        definitions=[
            {
                "name": "demo",
                "dataset": "objects",
                "url": ("https://example.com/objects.json"),
                "format": "json",
                "root_key": "data.items",
                "homepage": ("https://example.com/"),
            }
        ],
    )


def test_json_root_normalization():
    adapter = make_source()

    payload = json.dumps(
        {
            "data": {
                "items": [
                    {"id": 1},
                    {"id": 2},
                ]
            }
        }
    ).encode()

    records = adapter.normalize(
        "objects",
        payload,
    )

    assert records == [
        {"id": 1},
        {"id": 2},
    ]


def test_csv_normalization():
    adapter = DeclarativeHTTPSource(
        name="demo",
        definitions=[
            {
                "name": "demo",
                "dataset": "table",
                "url": ("https://example.com/table.csv"),
                "format": "csv",
            }
        ],
    )

    records = adapter.normalize(
        "table",
        b"id,name\n1,Alpha\n2,Beta\n",
    )

    assert records[1]["name"] == "Beta"


def test_multiple_datasets_group_into_one_source():
    sources = build_declarative_sources(
        [
            {
                "name": "demo",
                "dataset": "a",
                "url": ("https://example.com/a.json"),
                "format": "json",
            },
            {
                "name": "demo",
                "dataset": "b",
                "url": ("https://example.com/b.json"),
                "format": "json",
            },
        ]
    )

    assert set(sources["demo"].datasets) == {"a", "b"}
