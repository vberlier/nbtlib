from io import BytesIO
import pytest

from inputs import bytes_for_valid_tags, literal_values_for_tags


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


@pytest.mark.parametrize('literal_value, tag_input', literal_values_for_tags)
def test_tag_literal_value(literal_value, tag_input):
    assert literal_value == str(tag_input)
