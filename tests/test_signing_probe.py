from signing_probe import signing_readiness


def test_signing_probe_shape():
    data = signing_readiness()
    assert "ready" in data
    assert "modules" in data
    assert isinstance(data["modules"], dict)
