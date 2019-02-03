import pytest

from nbtlib import nbt, Compound

from .inputs import nbt_files


def validate_types(tag, expected):
    return isinstance(tag, type(expected)) and (
        not isinstance(tag, Compound)
        or all(validate_types(val, expected[key]) for key, val in tag.items())
    )


@pytest.mark.parametrize('file_path, value', nbt_files)
def test_file_loading(file_path, value):
    nbt_file = nbt.load(file_path)
    assert nbt_file == value


@pytest.mark.parametrize('file_path, value', nbt_files)
def test_file_compression(file_path, value):
    nbt_file = nbt.load(file_path)
    assert nbt_file.gzipped == value.gzipped


@pytest.mark.parametrize('file_path, value', nbt_files)
def test_file_types(file_path, value):
    nbt_file = nbt.load(file_path)
    assert validate_types(nbt_file, value), 'mismatched types'
