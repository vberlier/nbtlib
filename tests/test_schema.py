import pytest

from nbtlib import schema, String, Int, List, CastError


@pytest.fixture
def LooseSchema():
    return schema("Thing", {"foo": String, "bar": List[schema("Bar", {"value": Int})]})


@pytest.fixture
def StrictSchema():
    return schema(
        "Thing",
        {"foo": String, "bar": List[schema("Bar", {"value": Int}, strict=True)]},
        strict=True,
    )


@pytest.fixture(params=["LooseSchema", "StrictSchema"])
def DummySchema(request):
    return request.getfixturevalue(request.param)


def test_normal_instantiate(DummySchema):
    thing = DummySchema({"foo": 123, "bar": [{"value": "11"}]})

    assert type(thing) is DummySchema
    assert type(thing["foo"]) is String
    assert type(thing["bar"][0]["value"]) is Int


def test_invalid_instantiation(DummySchema):
    with pytest.raises(CastError):
        DummySchema({"foo": "ok", "bar": 42})


def test_normal_setitem(DummySchema):
    thing = DummySchema()
    thing["foo"] = "hello"

    assert type(thing["foo"]) is String


def test_invalid_setitem(DummySchema):
    thing = DummySchema()

    with pytest.raises(CastError):
        thing["bar"] = "abc"


def test_normal_update(DummySchema):
    thing = DummySchema()
    thing.update({"foo": "hello"})

    assert type(thing["foo"]) is String


def test_invalid_update(DummySchema):
    thing = DummySchema()

    with pytest.raises(CastError):
        thing.update({"bar": [{"value": 10}, {"value": []}]})


def test_loose_schema_with_extra_key(LooseSchema):
    thing = LooseSchema({"hello": "world"})

    assert type(thing["hello"]) is str


def test_strict_schema_with_extra_key(StrictSchema):
    with pytest.raises(TypeError):
        thing = StrictSchema({"hello": "world"})
