from collections import namedtuple

from domdata_pkg.serializers import rows_from, to_jsonable


def test_namedtuple_to_jsonable():
    Tick = namedtuple("Tick", "bid ask")
    assert to_jsonable(Tick(1.0, 2.0)) == {"bid": 1.0, "ask": 2.0}


def test_rows_from_scalar():
    assert rows_from({"a": 1}) == [{"a": 1}]
