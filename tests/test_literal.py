import pytest

from nbtlib import parse_nbt, InvalidLiteral

from .inputs import literal_values_for_tags, invalid_literals, nbt_files


@pytest.mark.parametrize("literal, expected_tag", literal_values_for_tags)
def test_literal_parsing(literal, expected_tag):
    assert parse_nbt(literal) == expected_tag


@pytest.mark.parametrize("literal, expected_tag", literal_values_for_tags)
def test_tag_literal_value(literal, expected_tag):
    assert parse_nbt(literal).snbt() == expected_tag.snbt()


@pytest.mark.parametrize("nbt_data", [nbt_data for _, nbt_data in nbt_files])
def test_parsing_literal_tag_value(nbt_data):
    assert parse_nbt(nbt_data.snbt()).snbt() == nbt_data.snbt()


@pytest.mark.parametrize("literal", invalid_literals)
def test_parsing_invalid_literal(literal):
    with pytest.raises(InvalidLiteral):
        parse_nbt(literal)
