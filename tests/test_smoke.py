import cutkit


def test_version_exists() -> None:
    assert isinstance(cutkit.__version__, str)
