"""This module defines utilities for accessing deeply nested properties.

Exported items:
    Path        -- Class representing an nbt path, inherits from `tuple`
    InvalidPath -- Exception raised when creating an invalid nbt path
"""


__all__ = ["Path", "InvalidPath", "NamedKey", "ListIndex", "CompoundMatch"]


import re
from typing import NamedTuple, Optional

from .tag import Int, String, Array, List, Compound
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
            return cls.from_accessors()

        if isinstance(path, Path):
            return cls.from_accessors(path)

        if isinstance(path, int):
            # Handle an integer x as if the string "[x]" were just parsed
            return cls.from_accessors((ListIndex(index=int(path)),))

        accessors = ()
        for accessor in parse_accessors(path):
            accessors = extend_accessors(accessors, accessor)

        return cls.from_accessors(accessors)

    def __getitem__(self, key):
        if isinstance(key, Path):
            new_accessors = tuple(key)
        elif isinstance(key, str):
            new_accessors = (NamedKey(key),)
        elif isinstance(key, int):
            new_accessors = (ListIndex(index=int(key)),)
        elif isinstance(key, slice) and all(
            n is None for n in [key.start, key.stop, key.step]
        ):
            new_accessors = (ListIndex(index=None),)
        elif isinstance(key, Compound):
            new_accessors = (CompoundMatch(key),)
        else:
            raise KeyError(key)

        accessors = tuple(self)

        for accessor in new_accessors:
            accessors = extend_accessors(accessors, accessor)

        return self.from_accessors(accessors)

    def __add__(self, other):
        if isinstance(other, Path):
            return self[other]
        elif isinstance(other, (str, int)):
            return self[Path(other)]
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, Path):
            return other[self]
        elif isinstance(other, (str, int)):
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
    def from_accessors(cls, accessors=()):
        return super().__new__(cls, accessors)

    def traverse(self, tag):
        tags = [(None, tag)]

        setter = None
        deleter = None

        for accessor in self:
            setter = getattr(accessor, "set", setter)
            deleter = getattr(accessor, "delete", deleter)

            tags = accessor.get(tags)

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
        return f"{self.__class__.__name__}({str(self)!r})"

    def __str__(self):
        segments = [""]

        for accessor in self:
            segment = str(accessor)

            if not segment or segment.startswith("["):
                segments[-1] += segment

            elif segment.startswith("{"):
                if segments[-1].endswith("[]"):
                    segments[-1] = segments[-1][:-2] + f"[{segment}]"
                else:
                    segments[-1] += segment

            else:
                segments.append(segment)

        return ".".join(filter(None, segments))


def can_be_converted_to_int(string):
    if not isinstance(string, str):
        return False
    try:
        int(string)
        return True
    except ValueError:
        return False


def parse_accessors(path):
    try:
        parser = Parser(tokenize(path))
    except InvalidLiteral:
        return ()

    while True:
        try:
            tag = parser.parse()
        except InvalidLiteral as exc:
            raise InvalidPath(f"Invalid path at position {exc.args[0][0]}") from exc

        if isinstance(tag, String):
            if parser.current_token.type == "QUOTED_STRING":
                yield NamedKey(tag[:])
            else:
                yield from (NamedKey(key) for key in tag.split(".") if key)

        elif isinstance(tag, List):
            if not tag:
                yield ListIndex(index=None)
            elif len(tag) != 1:
                raise InvalidPath("Brackets should only contain one element")
            elif issubclass(tag.subtype, Compound):
                yield ListIndex(index=None)
                yield CompoundMatch(tag[0])
            elif issubclass(tag.subtype, Int) or can_be_converted_to_int(tag[0]):
                yield ListIndex(int(tag[0]))
            else:
                raise InvalidPath(
                    "Brackets should only contain an integer or a compound"
                )

        elif isinstance(tag, Compound):
            yield CompoundMatch(tag)

        elif parser.current_token.type == "NUMBER":
            yield from (
                NamedKey(key) for key in parser.current_token.value.split(".") if key
            )

        else:
            raise InvalidPath(f"Invalid path element {tag}")

        try:
            parser.next()
        except InvalidLiteral:
            break


def extend_accessors(accessors, new_accessor):
    if isinstance(new_accessor, CompoundMatch) and accessors:
        *except_last, last_accessor = accessors

        if isinstance(last_accessor, CompoundMatch):
            new_compound = new_accessor.compound.with_defaults(last_accessor.compound)
            return tuple(except_last) + (CompoundMatch(new_compound),)
        if isinstance(last_accessor, ListIndex) and last_accessor.index is not None:
            raise InvalidPath(
                f"Can't match a compound on list items selected with {last_accessor!r}"
            )
    return accessors + (new_accessor,)


class NamedKey(NamedTuple):
    key: str

    UNQUOTED_REGEX = re.compile(r"^[a-zA-Z0-9_]+$")

    def get(self, tags):
        return [
            (tag, tag[self.key])
            for _, tag in tags
            if isinstance(tag, dict) and self.key in tag
        ]

    def set(self, tags, value):
        for parent, _ in tags:
            parent[self.key] = value

    def delete(self, tags):
        for parent, _ in tags:
            if self.key in parent:
                del parent[self.key]

    def __str__(self):
        return (
            self.key
            if self.UNQUOTED_REGEX.match(self.key)
            else '"' + self.key.replace('"', '\\"') + '"'
        )


class ListIndex(NamedTuple):
    index: Optional[int]

    def get(self, tags):
        tags = [tag for tag in tags if isinstance(tag[1], (List, Array))]

        if self.index is None:
            return [((tag, i), item) for _, tag in tags for i, item in enumerate(tag)]

        return [
            ((tag, self.index), tag[self.index])
            for _, tag in tags
            if -len(tag) <= self.index < len(tag)
        ]

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
    compound: Compound

    def get(self, tags):
        return [(parent, tag) for parent, tag in tags if tag.match(self.compound)]

    def __str__(self):
        return self.compound.snbt()
