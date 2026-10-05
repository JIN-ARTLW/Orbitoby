import orbitoby


def test_package_exposes_version():
    assert isinstance(orbitoby.__version__, str)
    assert orbitoby.__version__
