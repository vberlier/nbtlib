"""This module defines utilities for accessing deeply nested properties.

Exported items:
    Path        -- Class representing an nbt path, inherits from `tuple`
    InvalidPath -- Exception raised when creating an invalid nbt path
"""


__all__ = ['Path', 'InvalidPath']


import re
from typing import NamedTuple, Optional

from .tag import Int, String, List, Compound
from .literal.parser import Parser, tokenize, InvalidLiteral


class InvalidPath(ValueError):
    """Raised when creating an invalid nbt path."""


class Path(tuple):
    """Represents an nbt path.

    Instances of this class can be used for indexing into list and compound
    tags for accessing deeply nested properties.
    """

    __slots__ = ()

    def __new__(cls, path=None):
        if path is None:
            return cls.from_parts()

        if isinstance(path, Path):
            return cls.from_parts(path)

        parts = ()
        for part in parse_parts(path):
            parts = extend_parts(parts, part)

        return cls.from_parts(parts)

    def __getitem__(self, key):
        if isinstance(key, Path):
            new_parts = tuple(key)
        elif isinstance(key, str):
            new_parts = (NamedKey(key),)
        elif isinstance(key, int):
            new_parts = (ListIndex(index=key),)
        elif isinstance(key, slice) and all(n is None for n in [key.start, key.stop, key.step]):
            new_parts = (ListIndex(index=None),)
        elif isinstance(key, Compound):
            new_parts = (CompoundMatch(key),)
        else:
            raise KeyError(key)

        parts = tuple(self)

        for part in new_parts:
            parts = extend_parts(parts, part)

        return self.from_parts(parts)

    def __add__(self, other):
        if isinstance(other, Path):
            return self[other]
        elif isinstance(other, str):
            return self[Path(other)]
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, Path):
            return other[self]
        elif isinstance(other, str):
            return Path(other)[self]
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, str):
            other = Path(other)
        return super().__eq__(other)

    def __ne__(self, other):
        if isinstance(other, str):
            other = Path(other)
        return super().__ne__(other)

    def __hash__(self):
        return super().__hash__()

    @classmethod
    def from_parts(cls, parts=()):
        return super().__new__(cls, parts)

    def traverse(self, tag):
        tags = [(None, tag)]

        setter = None
        deleter = None

        for part in self:
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
        return f'{self.__class__.__name__}({str(self)!r})'

    def __str__(self):
        segments = ['']

        for part in self:
            segment = str(part)

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


def extend_parts(parts, new_part):
    if isinstance(new_part, CompoundMatch) and parts:
        *except_last, last_part = parts

        if isinstance(last_part, CompoundMatch):
            return tuple(except_last) + (
                CompoundMatch(new_part.compound.with_defaults(last_part.compound)),
            )
        if isinstance(last_part, ListIndex) and last_part.index is not None:
            raise InvalidPath('Can\'t match a compound on list items '
                              f'selected with {last_part!r}')
    return parts + (new_part,)


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
                raise InvalidPath('Brackets should only contain an integer or a compound')

        elif isinstance(tag, Compound):
            yield CompoundMatch(tag)

        else:
            raise InvalidPath(f'Invalid path element {tag}')

        try:
            parser.next()
        except InvalidLiteral:
            break
