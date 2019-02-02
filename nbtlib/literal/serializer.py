"""This module exposes utilities for serializing nbt tags to snbt.

Exported functions:
    serialize_tag -- Helper function that serializes nbt tags

Exported classes:
    Serializer -- Class that can turn nbt tags into their literal representation

Exported objects:
    ESCAPE_SEQUENCES -- Maps escape sequences to their substitution
    ESCAPE_SUBS      -- Maps substitutions to their escape sequence
"""


__all__ = ['serialize_tag', 'ESCAPE_SEQUENCES', 'ESCAPE_SUBS', 'Serializer']


import re


# Escape nbt strings

ESCAPE_SEQUENCES = {
    r'\"': '"',
    r'\\': '\\',
}

ESCAPE_SUBS = dict(reversed(tuple(map(reversed, ESCAPE_SEQUENCES.items()))))


def escape_string(string):
    """Return the escaped literal representation of an nbt string."""
    for match, seq in ESCAPE_SUBS.items():
        string = string.replace(match, seq)
    return f'"{string}"'


# Detect if a compound key can be represented unquoted

UNQUOTED_COMPOUND_KEY = re.compile(r'^[a-zA-Z0-9._+-]+$')


def stringify_compound_key(key):
    """Escape the compound key if it can't be represented unquoted."""
    if UNQUOTED_COMPOUND_KEY.match(key):
        return key
    else:
        return escape_string(key)


# User-friendly helper

def serialize_tag(tag):
    """Serialize an nbt tag to its literal representation."""
    return Serializer().serialize(tag)


# Implement serializer

class Serializer:
    """Nbt tag serializer."""

    def serialize(self, tag):
        """Return the literal representation of a tag."""
        handler = getattr(self, f'serialize_{tag.serializer}', None)
        if handler is None:
            raise TypeError(f'Can\'t serialize {type(tag)!r} instance')
        return handler(tag)

    def serialize_numeric(self, tag):
        """Return the literal representation of a numeric tag."""
        str_func = int.__str__ if isinstance(tag, int) else float.__str__
        return str_func(tag) + tag.suffix

    def serialize_array(self, tag):
        """Return the literal representation of an array tag."""
        elements = ','.join(f'{el}{tag.item_suffix}' for el in tag)
        return f'[{tag.array_prefix};{elements}]'

    def serialize_string(self, tag):
        """Return the literal representation of a string tag."""
        return escape_string(tag)

    def serialize_list(self, tag):
        """Return the literal representation of a list tag."""
        return f'[{",".join(map(self.serialize, tag))}]'

    def serialize_compound(self, tag):
        """Return the literal representation of a compound tag."""
        pairs = ','.join(f'{stringify_compound_key(key)}:{self.serialize(value)}'
                         for key, value in tag.items())
        return '{' + pairs + '}'
