import pytest

from nbtlib import parse_nbt

from inputs import literal_values_for_tags, nbt_files


@pytest.mark.parametrize('literal, expected_tag', literal_values_for_tags)
def test_literal_parsing(literal, expected_tag):
    assert parse_nbt(literal) == expected_tag


@pytest.mark.parametrize('nbt_data', [nbt_data for _, nbt_data in nbt_files])
def test_parsing_literal_tag_value(nbt_data):
    assert str(parse_nbt(str(nbt_data))) == str(nbt_data)
