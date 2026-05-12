from domdata_pkg.config import mask_value


def test_password_masked():
    assert mask_value("DOMDATA_MT5_PASSWORD", "secret") == "set"


def test_missing_mask():
    assert mask_value("DOMDATA_MT5_PASSWORD", None) == "missing"
