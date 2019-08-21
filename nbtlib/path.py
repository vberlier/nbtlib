"""This module defines utilities for accessing deeply nested properties.

Exported items:
    Path        -- Class representing an nbt path, inherits from `str`
    InvalidPath -- Exception raised when creating an invalid nbt path
"""


__all__ = ['Path', 'InvalidPath']


import re
from typing import NamedTuple, Optional

from .tag import Int, String, List, Compound
from .literal.parser import Parser, tokenize, InvalidLiteral


class InvalidPath(ValueError):
    """Raised when creating an invalid nbt path."""


class Path(str):
    """Represents an nbt path.

    Instances of this class can be used for indexing into list and compound
    tags for accessing deeply nested properties.
    """

    __slots__ = ('parts',)

    def __new__(cls, path=None):
        return cls.from_parts(parse_parts(path) if path else ())

    @classmethod
    def from_parts(cls, parts):
        parts = tuple(parts)
        self = super().__new__(cls, join_parts(parts))
        self.parts = parts
        return self

    def traverse(self, tag):
        tags = [(None, tag)]

        setter = None
        deleter = None

        for part in self.parts:
            setter = getattr(part, 'set', setter)
            deleter = getattr(part, 'delete', deleter)

            tags = part.get(tags)

        return tags, setter, deleter

    def get(self, tag):
        return [tag for _, tag in self.traverse(tag)[0]]

    def set(self, tag, value):
        tags, setter, _ = self.traverse(tag)

        if setter:
            setter(tags, value)

    def delete(self, tag):
        tags, _, deleter = self.traverse(tag)

        if deleter:
            deleter(tags)

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'


class NamedKey(NamedTuple):
    key: str

    UNQUOTED_REGEX = re.compile(r'^[a-zA-Z0-9_]+$')

    def get(self, tags):
        return [(tag, tag[self.key]) for _, tag in tags if self.key in tag]

    def set(self, tags, value):
        for parent, _ in tags:
            parent[self.key] = value

    def delete(self, tags):
        for parent, _ in tags:
            if self.key in parent:
                del parent[self.key]

    def __str__(self):
        return (
            self.key if self.UNQUOTED_REGEX.match(self.key) else
            '"' + self.key.replace('"', '\\"') + '"'
        )


class ListIndex(NamedTuple):
    index: Optional[int]

    def get(self, tags):
        if self.index is None:
            return [((tag, i), item)
                    for _, tag in tags
                    for i, item in enumerate(tag)]
        return [((tag, self.index), tag[self.index])
                for _, tag in tags if self.index < len(tag)]

    def set(self, tags, value):
        for (parent, i), _ in tags:
            if self.index is None or i == self.index:
                parent[i] = value

    def delete(self, tags):
        for (parent, i), _ in reversed(tags):
            if self.index is None or i == self.index:
                del parent[i]

    def __str__(self):
        return f'[{"" if self.index is None else self.index}]'


class CompoundMatch(NamedTuple):
    compound: Optional[Compound]

    def get(self, tags):
        return [(parent, tag) for parent, tag in tags if tag.match(self.compound)]

    def __str__(self):
        return str(self.compound)


def parse_parts(path):
    if isinstance(path, Path):
        yield from path.parts

    try:
        parser = Parser(tokenize(path))
    except InvalidLiteral:
        return ()

    while True:
        try:
            tag = parser.parse()
        except InvalidLiteral as exc:
            raise InvalidPath(f'Invalid path at position {exc.args[0][0]}') from exc

        if isinstance(tag, String):
            if parser.current_token.type == 'QUOTED_STRING':
                yield NamedKey(tag[:])
            else:
                yield from (NamedKey(key) for key in tag.split('.') if key)

        elif isinstance(tag, List):
            if not tag:
                yield ListIndex(index=None)
            elif len(tag) != 1:
                raise InvalidPath('Brackets should only contain one element')
            elif issubclass(tag.subtype, Int):
                yield ListIndex(int(tag[0]))
            elif issubclass(tag.subtype, Compound):
                yield ListIndex(index=None)
                yield CompoundMatch(tag[0])
            else:
                raise InvalidPath(f'Brackets should only contain an integer or a compound')

        elif isinstance(tag, Compound):
            yield CompoundMatch(tag)

        else:
            raise InvalidPath(f'Invalid path element {tag}')

        try:
            parser.next()
        except InvalidLiteral:
            break


def join_parts(parts):
    segments = ['']

    for p in parts:
        segment = str(p)

        if not segment or segment.startswith('['):
            segments[-1] += segment
        elif segment.startswith('{'):
            if segments[-1].endswith('[]'):
                segments[-1] = segments[-1][:-2] + f'[{segment}]'
            else:
                segments[-1] += segment
        else:
            segments.append(segment)

    return '.'.join(filter(None, segments))
