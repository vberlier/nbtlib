from io import BytesIO

import pytest
from nbtlib import nbt


def write_parse(nbt_tag):
    data = BytesIO()
    nbt_tag.write(data)
    data.seek(0)
    return nbt_tag.parse(data)


@pytest.mark.parametrize(
    "filename",
    [
        "byte.nbt",
        "short.nbt",
        "int.nbt",
        "long.nbt",
        "float.nbt",
        "double.nbt",
        "byte_array.nbt",
        "string.nbt",
        "list.nbt",
        "compound.nbt",
        "int_array.nbt",
        "long_array.nbt",
    ],
)
def test_tag_bench(benchmark, filename):
    nbt_tag = nbt.load(f"tests/nbt_files/bench/{filename}")
    result = benchmark(write_parse, nbt_tag)
    assert result == nbt_tag
