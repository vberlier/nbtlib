"""This module exposes utilities for parsing snbt.

Exported functions:
    parse_nbt -- Helper function that parses nbt literals
    tokenize  -- Generator that lazily yields tokens from a string

Exported classes:
    Parser -- Class that can parse nbt tags from a literal token stream

Exported exceptions:
    InvalidLiteral -- Raised when parsing invalid nbt literals
"""


__all__ = ["parse_nbt", "InvalidLiteral", "tokenize", "Parser"]


import re
from collections import namedtuple

from .serializer import STRING_QUOTES, ESCAPE_SEQUENCES, ESCAPE_SUBS
from ..tag import (
    Byte,
    Short,
    Int,
    Long,
    Float,
    Double,
    ByteArray,
    String,
    List,
    Compound,
    IntArray,
    LongArray,
    OutOfRange,
    IncompatibleItemType,
)


# Token definition

ESCAPE_REGEX = re.compile(r"\\.")

TOKENS = {
    "QUOTED_STRING": "|".join(
        fr"{q}(?:{ESCAPE_REGEX.pattern}|[^\\])*?{q}" for q in STRING_QUOTES
    ),
    "NUMBER": r"[+-]?(?:[0-9]*?\.[0-9]+|[0-9]+\.[0-9]*?|[1-9][0-9]*|0)([eE][+-]?[0-9]+)?[bslfdBSLFD]?(?![a-zA-Z0-9._+-])",
    "STRING": r"[a-zA-Z0-9._+-]+",
    "COMPOUND": r"\{",
    "CLOSE_COMPOUND": r"\}",
    "BYTE_ARRAY": r"\[B;",
    "INT_ARRAY": r"\[I;",
    "LONG_ARRAY": r"\[L;",
    "LIST": r"\[",
    "CLOSE_BRACKET": r"\]",
    "COLON": r":",
    "COMMA": r",",
    "INVALID": r".+?",
}


# Build the regex

TOKENS_REGEX = re.compile(
    "|".join(fr"\s*(?P<{key}>{value})\s*" for key, value in TOKENS.items())
)


# Associate number suffixes to tag types

NUMBER_SUFFIXES = {"b": Byte, "s": Short, "l": Long, "f": Float, "d": Double}


# Define literal aliases

LITERAL_ALIASES = {
    "true": Byte(1),
    "false": Byte(0),
}


# Custom errors


class InvalidLiteral(ValueError):
    """Exception raised when parsing invalid nbt literals.

    The exception must be instantiated with two parameters. The first
    one needs to be a tuple representing the location of the error in
    the nbt string (start_index, end_index). The second argument is the
    actual error message.
    """

    def __str__(self):
        return f"{self.args[1]} at position {self.args[0][0]}"


# User-friendly helper


def parse_nbt(literal):
    """Parse a literal nbt string and return the resulting tag."""
    parser = Parser(tokenize(literal))
    tag = parser.parse()

    cursor = parser.token_span[1]
    leftover = literal[cursor:]

    if leftover.strip():
        parser.token_span = cursor, cursor + len(leftover)
        raise parser.error(f"Expected end of string but got {leftover!r}")

    return tag


# Implement tokenization

Token = namedtuple("Token", ["type", "value", "span"])


def tokenize(string):
    """Match and yield all the tokens of the input string."""
    for match in TOKENS_REGEX.finditer(string):
        yield Token(match.lastgroup, match.group().strip(), match.span())


# Implement parser


class Parser:
    """Nbt literal parser.

    The parser needs to be instantiated with a token stream as argument.
    Using the `parse` method will return the corresponding nbt tag.

    The parser will raise an InvalidLiteral exception if it encounters
    an invalid nbt literal while parsing.
    """

    def __init__(self, token_stream):
        self.token_stream = iter(token_stream)
        self.current_token = None
        self.token_span = (0, 0)

        self.next()

    def error(self, message):
        """Create an InvalidLiteral using the current token position."""
        return InvalidLiteral(self.token_span, message)

    def next(self):
        """Move to the next token in the token stream."""
        self.current_token = next(self.token_stream, None)
        if self.current_token is None:
            self.token_span = self.token_span[1], self.token_span[1]
            raise self.error("Unexpected end of input")
        self.token_span = self.current_token.span
        return self

    def parse(self):
        """Parse and return an nbt literal from the token stream."""
        token_type = self.current_token.type.lower()
        handler = getattr(self, f"parse_{token_type}", None)
        if handler is None:
            raise self.error(f"Invalid literal {self.current_token.value!r}")
        return handler()

    def parse_quoted_string(self):
        """Parse a quoted string from the token stream."""
        return String(self.unquote_string(self.current_token.value))

    def parse_number(self):
        """Parse a number from the token stream."""
        value = self.current_token.value
        suffix = value[-1].lower()

        try:
            if suffix in NUMBER_SUFFIXES:
                return NUMBER_SUFFIXES[suffix](value[:-1])
            return Double(value) if "." in value else Int(value)
        except (OutOfRange, ValueError):
            return String(value)

    def parse_string(self):
        """Parse a regular unquoted string from the token stream."""
        aliased_value = LITERAL_ALIASES.get(self.current_token.value.lower())
        if aliased_value is not None:
            return aliased_value
        return String(self.current_token.value)

    def collect_tokens_until(self, token_type):
        """Yield the item tokens in a comma-separated tag collection."""
        self.next()
        if self.current_token.type == token_type:
            return

        while True:
            yield self.current_token

            self.next()
            if self.current_token.type == token_type:
                return

            if self.current_token.type != "COMMA":
                raise self.error(f"Expected comma but got {self.current_token.value!r}")
            self.next()

    def parse_compound(self):
        """Parse a compound from the token stream."""
        compound_tag = Compound()

        for token in self.collect_tokens_until("CLOSE_COMPOUND"):
            item_key = token.value
            if token.type not in ("NUMBER", "STRING", "QUOTED_STRING"):
                raise self.error(f"Expected compound key but got {item_key!r}")

            if token.type == "QUOTED_STRING":
                item_key = self.unquote_string(item_key)

            if self.next().current_token.type != "COLON":
                raise self.error(f"Expected colon but got {self.current_token.value!r}")
            self.next()
            compound_tag[item_key] = self.parse()
        return compound_tag

    def array_items(self, number_type, *, number_suffix=""):
        """Parse and yield array items from the token stream."""
        for token in self.collect_tokens_until("CLOSE_BRACKET"):
            is_number = token.type == "NUMBER"
            value = token.value.lower()
            if not (is_number and value.endswith(number_suffix)):
                raise self.error(f"Invalid {number_type} array element {token.value!r}")
            yield int(value.replace(number_suffix, ""))

    def parse_byte_array(self):
        """Parse a byte array from the token stream."""
        return ByteArray(list(self.array_items("byte", number_suffix="b")))

    def parse_int_array(self):
        """Parse an int array from the token stream."""
        return IntArray(list(self.array_items("int")))

    def parse_long_array(self):
        """Parse a long array from the token stream."""
        return LongArray(list(self.array_items("long", number_suffix="l")))

    def parse_list(self):
        """Parse a list from the token stream."""
        try:
            return List(
                [self.parse() for _ in self.collect_tokens_until("CLOSE_BRACKET")]
            )
        except IncompatibleItemType as exc:
            raise self.error(
                f"Item {str(exc.item)!r} is not a {exc.subtype.__name__} tag"
            ) from None

    def parse_invalid(self):
        """Parse an invalid token from the token stream."""
        raise self.error(f"Invalid token {self.current_token.value!r}")

    def unquote_string(self, string):
        """Return the unquoted value of a quoted string."""
        value = string[1:-1]

        forbidden_sequences = {ESCAPE_SUBS[STRING_QUOTES[string[0]]]}
        valid_sequences = set(ESCAPE_SEQUENCES) - forbidden_sequences

        for seq in ESCAPE_REGEX.findall(value):
            if seq not in valid_sequences:
                raise self.error(f'Invalid escape sequence "{seq}"')

        for seq, sub in ESCAPE_SEQUENCES.items():
            value = value.replace(seq, sub)

        return value
