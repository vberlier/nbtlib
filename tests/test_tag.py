from io import BytesIO
import pytest

from nbtlib.tag import *

from inputs import bytes_for_valid_tags, out_of_range_numeric_tags


@pytest.mark.parametrize('byteorder, bytes_input, expected_tag', bytes_for_valid_tags)
def test_valid_bytes_parsing(byteorder, bytes_input, expected_tag):
    tag_type = type(expected_tag)
    parsed_tag = tag_type.parse(BytesIO(bytes_input), byteorder)
    assert parsed_tag == expected_tag


@pytest.mark.parametrize('byteorder, expected_bytes, tag_input', bytes_for_valid_tags)
def test_valid_tag_serialization(byteorder, expected_bytes, tag_input):
    buff = BytesIO()
    tag_input.write(buff, byteorder)
    buff.seek(0)
    serialized_bytes = buff.read()
    assert serialized_bytes == expected_bytes


def test_end_tag_instantiation():
    with pytest.raises(EndInstantiation):
        End()


@pytest.mark.parametrize('tag_type, value', out_of_range_numeric_tags)
def test_out_of_range_numeric_tags(tag_type, value):
    with pytest.raises(OutOfRange):
        tag_type(value)


class TestListTagEdgeCases:
    def test_incompatible_with_subtype(self):
        with pytest.raises(IncompatibleItemType):
            List[String]([4, Int(-1)])

    def test_incompatible_without_subtype(self):
        with pytest.raises(IncompatibleItemType):
            List([Int(2), String('5')])

    def test_bare_elements_without_subtype(self):
        with pytest.raises(ValueError):
            List(['hello'])

    def test_casting_error_with_subtype(self):
        with pytest.raises(CastError):
            List[List[Int]]([[5, 4], [[]]])

    def test_casting_error_without_subtype(self):
        with pytest.raises(CastError):
            List([[5, 4], List([List([])])])
