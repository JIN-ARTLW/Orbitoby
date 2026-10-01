from orbitoby.source_api import SourceAPI
from orbitoby.sources.gcat import GCATSource


class FakeArchive(SourceAPI):
    def __init__(self):
        self.sources = {"gcat": GCATSource()}

    def get_source(self, name):
        return self.sources[name]


def test_source_info():
    archive = FakeArchive()

    info = archive.source_info("gcat")

    assert info["name"] == "gcat"
    assert info["title"] == ("General Catalog of Artificial Space Objects")


def test_credits_never_guess_citations():
    archive = FakeArchive()

    credits = archive.credits()

    assert credits[0]["name"] == "gcat"
    assert "citation" not in credits[0]


def test_licenses_preserve_unknown_policy():
    archive = FakeArchive()

    licenses = archive.licenses()

    assert licenses[0]["policy"]["redistribution"] == "unknown"
