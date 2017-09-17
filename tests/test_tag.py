
from io import BytesIO

import pytest

from nbtlib.tag import *


tag_parsing_inputs = [

    # Byte tag
    (b'\x00', Byte(0)),
    (b'\xFF', Byte(-1)),
    (b'\x7F', Byte(127)),
    (b'\x80', Byte(-128)),

    # Short tag
    (b'\x00\x00', Short(0)),
    (b'\xFF\xFF', Short(-1)),
    (b'\x7F\xFF', Short(32767)),
    (b'\x80\x00', Short(-32768)),

    # Int tag
    (b'\x00\x00\x00\x00', Int(0)),
    (b'\xFF\xFF\xFF\xFF', Int(-1)),
    (b'\x7F\xFF\xFF\xFF', Int(2147483647)),
    (b'\x80\x00\x00\x00', Int(-2147483648)),

    # Long tag
    (b'\x00\x00\x00\x00\x00\x00\x00\x00', Long(0)),
    (b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF', Long(-1)),
    (b'\x7F\xFF\xFF\xFF\xFF\xFF\xFF\xFF', Long(9223372036854775807)),
    (b'\x80\x00\x00\x00\x00\x00\x00\x00', Long(-9223372036854775808)),

]


@pytest.mark.parametrize('bytes_input, expected_tag', tag_parsing_inputs)
def test_tag_parsing(bytes_input, expected_tag):
    tag_type = type(expected_tag)
    parsed_tag = tag_type.parse(BytesIO(bytes_input))
    assert parsed_tag == expected_tag

