
"""This module exposes utilities for parsing literal nbt strings.

Exported items:
    parse_nbt      -- Helper function that parses nbt tags
    InvalidLiteral -- Exception raised when parsing invalid nbt literals
"""


__all__ = ['parse_nbt', 'InvalidLiteral']


import re
import json
from collections import namedtuple

from .tag import *


# Token definition

TOKENS = {
    'QUOTED_STRING': r'""|".*?[^\\]"',
    'NUMBER': r'-?(?:[0-9]*?\.[0-9]+|[0-9]+\.[0-9]*?|[0-9]+)[bslfdBSLFD]?',
    'STRING': r'[a-zA-Z0-9._+-]+',
    'COMPOUND': r'\{',
    'CLOSE_COMPOUND': r'\}',
    'BYTE_ARRAY': r'\[B;',
    'INT_ARRAY': r'\[I;',
    'LIST': r'\[',
    'CLOSE_BRACKET': r'\]',
    'COLON': r':',
    'COMMA': r',',
    'INVALID': r'.+?',
}


# Build the regex

TOKENS_REGEX = re.compile(
    '|'.join(f'\s*(?P<{key}>{value})\s*' for key, value in TOKENS.items())
)


# Associate number suffixes to tag types

NUMBER_SUFFIXES = {'b': Byte, 's': Short, 'l': Long, 'f': Float, 'd': Double}


def parse_nbt(literal):
    """Parse a literal nbt string and return the resulting tag."""
    parser = NbtParser(tokenize(literal))
    tag = parser.parse()

    leftover = literal[parser.token_span[1]:]
    if leftover.strip():
        raise parser.error(f'Expected end of string but got {leftover!r}')
    return tag


class InvalidLiteral(ValueError):
    """Exception raised when parsing invalid nbt literals.

    The exception must be instantiated with two parameters. The first
    one needs to be a tuple representing the location of the error in
    the nbt string (start_index, end_index). The second argument is the
    actual error message.
    """

    def __str__(self):
        return f'{self.args[1]} at position {self.args[0][0]}'


Token = namedtuple('Token', ['type', 'value', 'span'])


def tokenize(string):
    """Match and yield all the tokens of the input string."""
    for match in TOKENS_REGEX.finditer(string):
        yield Token(match.lastgroup, match.group().strip(), match.span())


class NbtParser:
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
            raise self.error('Unexpected end of input')
        self.token_span = self.current_token.span
        return self

    def parse(self):
        """Parse and return an nbt literal from the token stream."""
        token_type = self.current_token.type.lower()
        handler = getattr(self, f'parse_{token_type}', None)
        if handler is None:
            raise self.error(f'Invalid literal {self.current_token.value!r}')
        return handler()

    def parse_quoted_string(self):
        """Parse a quoted string from the token stream."""
        return String(self.unquote_string(self.current_token.value))

    def parse_number(self):
        """Parse a number from the token stream."""
        value = self.current_token.value
        suffix = value[-1].lower()
        if suffix in NUMBER_SUFFIXES:
            return NUMBER_SUFFIXES[suffix](value[:-1])
        else:
            return Int(value)

    def parse_string(self):
        """Parse a regular unquoted string from the token stream."""
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

            if self.current_token.type != 'COMMA':
                raise self.error(f'Expected comma but got '
                                 f'{self.current_token.value!r}')
            self.next()

    def parse_compound(self):
        """Parse a compound from the token stream."""
        compound_tag = Compound()

        for token in self.collect_tokens_until('CLOSE_COMPOUND'):
            item_key = token.value
            if token.type not in ('STRING', 'QUOTED_STRING'):
                raise self.error(f'Expected compound key but got {item_key!r}')

            if token.type == 'QUOTED_STRING':
                item_key = self.unquote_string(item_key)

            if self.next().current_token.type != 'COLON':
                raise self.error(f'Expected colon but got '
                                 f'{self.current_token.value!r}')
            self.next()
            compound_tag[item_key] = self.parse()
        return compound_tag

    def fill_generic_array(self, array_tag, number_type, *, number_suffix=''):
        """Fill an array by parsing its items from the token stream."""
        for token in self.collect_tokens_until('CLOSE_BRACKET'):
            is_number = token.type == 'NUMBER'
            if not (is_number and token.value.endswith(number_suffix)):
                raise self.error(f'Invalid {number_type} array element '
                                 f'{token.value!r}')
            array_tag.append(int(token.value.replace(number_suffix, '')))
        return array_tag

    def parse_byte_array(self):
        """Parse a byte array from the token stream."""
        return self.fill_generic_array(ByteArray(), 'byte', number_suffix='b')

    def parse_int_array(self):
        """Parse an int array from the token stream."""
        return self.fill_generic_array(IntArray(), 'int')

    def parse_list(self):
        """Parse a list from the token stream."""
        list_tag = List[End]()

        for token in self.collect_tokens_until('CLOSE_BRACKET'):
            item = self.parse()
            if list_tag.subtype is End:
                list_tag = List[item.__class__]()
            elif not isinstance(item, list_tag.subtype):
                raise self.error(f'Item {str(item)!r} is not a '
                                 f'{list_tag.subtype.__name__} tag')
            list_tag.append(item)
        return list_tag

    def parse_invalid(self):
        """Parse an invalid token from the token stream."""
        raise self.error(f'Invalid token {self.current_token.value!r}')

    @staticmethod
    def unquote_string(string):
        """Return the unquoted value of a quoted string."""
        return json.loads(string.replace(r'\\', '\\'))  # TODO: Fix escaping
