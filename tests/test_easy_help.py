import pytest

import orbitoby as ob
from orbitoby._easy_help import public_easy_api


def test_help_is_exported():
    assert callable(ob.help)
    assert "help" in ob.__all__


@pytest.mark.parametrize(
    "topic, expected",
    [
        ("Kp", "GFZ"),
        ("GFZ", 'study.weather("Kp"'),
        ("density", "Swarm"),
        ("plot", "SVG"),
        ("sources", "sources().show()"),
        ("MSIS", "NRLMSIS"),
        ("coverage", "UTC"),
        ("login", 'ob.login("Space-Track")'),
    ],
)
def test_beginner_topics(topic, expected, capsys):
    ob.help(topic)
    assert expected in capsys.readouterr().out


def test_index_has_beginner_example(capsys):
    ob.help()
    text = capsys.readouterr().out

    assert 'study.weather("Kp").plot()' in text
    assert 'ob.help("all")' in text or "ob.help('all')" in text


def test_all_help_follows_actual_public_api(capsys):
    commands = public_easy_api()

    assert "ob.study" in commands
    assert "ob.help" in commands
    assert "Study.weather" in commands
    assert "Study.align" in commands
    assert "OrbitResult.plot" in commands
    assert "DataResult.save" in commands
    assert "SourceList.open" in commands

    ob.help("all")
    output = capsys.readouterr().out

    for command, signature in commands.items():
        assert command + signature in output

    # Work not implemented must not be advertised as completed.
    assert "아직 전체 명세를 충족하지 않은 부분" in output


def test_unknown_topic_gives_suggestion(capsys):
    ob.help("weathe")
    output = capsys.readouterr().out

    assert 'ob.help("weather")' in output


def test_invalid_topic_type():
    with pytest.raises(TypeError):
        ob.help(123)
