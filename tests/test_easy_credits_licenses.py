import orbitoby as ob


def test_credits_match_registered_sources():
    credits = ob.credits()
    registered = ob.sources()

    assert len(credits) == len(registered)
    assert set(credits.table["name"]) == set(registered.table["name"])
    assert {"name", "title", "homepage"}.issubset(credits.table.columns)


def test_licenses_preserve_core_policy():
    licenses = ob.licenses()

    assert len(licenses) == len(ob.sources())
    assert {"name", "policy"}.issubset(licenses.table.columns)

    gfz = licenses.table.loc[licenses.table["name"] == "gfz"]

    assert len(gfz) == 1

    registered_policy = ob.source("GFZ").table.iloc[0]["policy"]
    assert gfz.iloc[0]["policy"] == registered_policy


def test_help_includes_credits_and_licenses(capsys):
    ob.help("credits")
    assert "ob.credits().show()" in capsys.readouterr().out

    ob.help("licenses")
    assert "ob.licenses().show()" in capsys.readouterr().out

    ob.help("all")
    text = capsys.readouterr().out

    assert "ob.credits(" in text
    assert "ob.licenses(" in text
