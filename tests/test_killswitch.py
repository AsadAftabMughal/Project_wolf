from wolf import killswitch


def test_engage_and_release(tmp_path):
    f = str(tmp_path / "state" / "KILL")
    assert not killswitch.is_engaged(f)
    killswitch.engage(f, "test")
    assert killswitch.is_engaged(f)
    killswitch.release(f)
    assert not killswitch.is_engaged(f)


def test_release_when_absent_is_fine(tmp_path):
    killswitch.release(str(tmp_path / "KILL"))
