"""This module exposes utilities for serializing nbt tags to snbt.

Exported functions:
    serialize_tag -- Helper function that serializes nbt tags

Exported classes:
    Serializer -- Class that can turn nbt tags into their literal representation

Exported objects:
    STRING_QUOTES    -- Maps the two types of quote to each other
    ESCAPE_SEQUENCES -- Maps escape sequences to their substitution
    ESCAPE_SUBS      -- Maps substitutions to their escape sequence
"""


__all__ = [
    "serialize_tag",
    "STRING_QUOTES",
    "ESCAPE_SEQUENCES",
    "ESCAPE_SUBS",
    "Serializer",
]


import re
from contextlib import contextmanager


# Quoted string escaping

STRING_QUOTES = {
    '"': "'",
    "'": '"',
}

QUOTE_REGEX = re.compile("|".join(STRING_QUOTES))

ESCAPE_SEQUENCES = {fr"\{q}": q for q in STRING_QUOTES}
ESCAPE_SEQUENCES[r"\\"] = "\\"

ESCAPE_SUBS = dict(reversed(tuple(map(reversed, ESCAPE_SEQUENCES.items()))))


# Detect if a compound key can be represented unquoted

UNQUOTED_COMPOUND_KEY = re.compile(r"^[a-zA-Z0-9._+-]+$")


# User-friendly helper


def serialize_tag(tag, *, indent=None, compact=False, quote=None):
    """Serialize an nbt tag to its literal representation."""
    serializer = Serializer(indent=indent, compact=compact, quote=quote)
    return serializer.serialize(tag)


# Implement serializer


class Serializer:
    """Nbt tag serializer."""

    def __init__(self, *, indent=None, compact=False, quote=None):
        self.indentation = indent * " " if isinstance(indent, int) else indent
        self.comma = "," if compact else ", "
        self.colon = ":" if compact else ": "
        self.semicolon = ";" if compact else "; "

        self.indent = ""
        self.previous_indent = ""

        self.quote = quote

    @contextmanager
    def depth(self):
        """Increase the level of indentation by one."""
        if self.indentation is None:
            yield
        else:
            previous = self.previous_indent
            self.previous_indent = self.indent
            self.indent += self.indentation
            yield
            self.indent = self.previous_indent
            self.previous_indent = previous

    def should_expand(self, tag):
        """Return whether the specified tag should be expanded."""
        return (
            self.indentation is not None
            and tag
            and (
                not self.previous_indent
                or (
                    tag.serializer == "list"
                    and tag.subtype.serializer in ("array", "list", "compound")
                )
                or (tag.serializer == "compound")
            )
        )

    def expand(self, separator, fmt):
        """Return the expanded version of the separator and format string."""
        return (
            f"{separator}\n{self.indent}",
            fmt.replace("{}", f"\n{self.indent}{{}}\n{self.previous_indent}"),
        )

    def escape_string(self, string):
        """Return the escaped literal representation of an nbt string."""
        if self.quote:
            quote = self.quote
        else:
            found = QUOTE_REGEX.search(string)
            quote = STRING_QUOTES[found.group()] if found else next(iter(STRING_QUOTES))

        for match, seq in ESCAPE_SUBS.items():
            if match == quote or match not in STRING_QUOTES:
                string = string.replace(match, seq)

        return f"{quote}{string}{quote}"

    def stringify_compound_key(self, key):
        """Escape the compound key if it can't be represented unquoted."""
        if UNQUOTED_COMPOUND_KEY.match(key):
            return key
        return self.escape_string(key)

    def serialize(self, tag):
        """Return the literal representation of a tag."""
        handler = getattr(self, f"serialize_{tag.serializer}", None)
        if handler is None:
            raise TypeError(f"Can't serialize {type(tag)!r} instance")
        return handler(tag)

    def serialize_numeric(self, tag):
        """Return the literal representation of a numeric tag."""
        str_func = int.__repr__ if isinstance(tag, int) else float.__repr__
        return str_func(tag) + tag.suffix

    def serialize_array(self, tag):
        """Return the literal representation of an array tag."""
        elements = self.comma.join(map(serialize_tag, tag)).upper()
        return f"[{tag.array_prefix}{self.semicolon}{elements}]"

    def serialize_string(self, tag):
        """Return the literal representation of a string tag."""
        return self.escape_string(tag)

    def serialize_list(self, tag):
        """Return the literal representation of a list tag."""
        separator, fmt = self.comma, "[{}]"

        with self.depth():
            if self.should_expand(tag):
                separator, fmt = self.expand(separator, fmt)

            return fmt.format(separator.join(map(self.serialize, tag)))

    def serialize_compound(self, tag):
        """Return the literal representation of a compound tag."""
        separator, fmt = self.comma, "{{{}}}"

        with self.depth():
            if self.should_expand(tag):
                separator, fmt = self.expand(separator, fmt)

            return fmt.format(
                separator.join(
                    f"{self.stringify_compound_key(key)}{self.colon}{self.serialize(value)}"
                    for key, value in tag.items()
                )
            )
