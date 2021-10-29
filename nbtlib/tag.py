r"""
.. testsetup::

    import io
    import struct
    from pprint import pprint
    from nbtlib import *

All the tag classes have a :meth:`Base.parse` classmethod that reads
nbt data from a file-like object and returns a tag instance. Tag
instances can then write their binary representation back to file-like
objects using the :meth:`Base.write` method.

.. doctest::

    >>> fileobj = io.BytesIO(b"\x03\x00\x03foo\x00\x00\x00{\x00")
    >>> data = Compound.parse(fileobj)
    >>> data
    Compound({'foo': Int(123)})

    >>> fileobj = io.BytesIO()
    >>> data.write(fileobj)
    >>> fileobj.getvalue()
    b'\x03\x00\x03foo\x00\x00\x00{\x00'

Each tag inherits from a closely equivalent python builtin. For instance,
the :class:`Compound` class inherits from the builtin ``dict`` type.
This means that all the familiar operations available on the base type
work out of the box on the derived tag instances.

+-------------------+---------------------------------------------------------+
|     Base type     |                   Associated nbt tags                   |
+===================+=========================================================+
| ``int``           | :class:`Byte` :class:`Short` :class:`Int` :class:`Long` |
+-------------------+---------------------------------------------------------+
| ``float``         | :class:`Float` :class:`Double`                          |
+-------------------+---------------------------------------------------------+
| ``str``           | :class:`String`                                         |
+-------------------+---------------------------------------------------------+
| ``numpy.ndarray`` | :class:`ByteArray` :class:`IntArray` :class:`LongArray` |
+-------------------+---------------------------------------------------------+
| ``list``          | :class:`List`                                           |
+-------------------+---------------------------------------------------------+
| ``dict``          | :class:`Compound`                                       |
+-------------------+---------------------------------------------------------+

Operator overloading works as expected with all tag types. Note that values are
returned unwrapped.

.. doctest::

    >>> data = Compound({"foo": Int(123)})
    >>> data["foo"] = Int(-1 * data["foo"])
    >>> data["bar"] = String("hello")
    >>> data
    Compound({'foo': Int(-123), 'bar': String('hello')})
"""


__all__ = [
    "Base",
    "Numeric",
    "NumericInteger",
    "Byte",
    "Short",
    "Int",
    "Long",
    "Float",
    "Double",
    "String",
    "List",
    "Compound",
    "End",
    "Array",
    "ByteArray",
    "IntArray",
    "LongArray",
    "EndInstantiation",
    "OutOfRange",
    "IncompatibleItemType",
    "CastError",
]


from struct import Struct
from struct import error as StructError

import numpy as np

from .literal.serializer import serialize_tag

# Struct formats used to pack and unpack numeric values


def get_format(fmt, string):
    """Return a dictionary containing a format for each byte order."""
    return {"big": fmt(">" + string), "little": fmt("<" + string)}


BYTE = get_format(Struct, "b")
SHORT = get_format(Struct, "h")
USHORT = get_format(Struct, "H")
INT = get_format(Struct, "i")
LONG = get_format(Struct, "q")
FLOAT = get_format(Struct, "f")
DOUBLE = get_format(Struct, "d")


# Custom errors


class EndInstantiation(TypeError):
    """Raised when trying to instantiate an :class:`End` tag."""

    def __init__(self):
        super().__init__("End tags can't be instantiated")


class OutOfRange(ValueError):
    """Raised when a numeric value is out of range.

    Converting builtin ``int`` instances to numeric nbt tags can fail if
    the tag type isn't big enough.

    .. doctest::

        >>> Byte(127)
        Byte(127)
        >>> Byte(128)
        Traceback (most recent call last):
        ...
        nbtlib.tag.OutOfRange: Byte(128) is out of range
    """

    def __init__(self, value):
        super().__init__(f"{value!r} is out of range")


class IncompatibleItemType(TypeError):
    """Raised when a list item is incompatible with the subtype of the list.

    Unlike builtin python lists, list tags are homogeneous so adding an
    incompatible item to the list raises an error.

    .. doctest::

        >>> List([String("foo"), Int(123)])
        Traceback (most recent call last):
        ...
        nbtlib.tag.IncompatibleItemType: Int(123) should be a String tag
    """

    def __init__(self, item, subtype):
        super().__init__(f"{item!r} should be a {subtype.__name__} tag")
        self.item = item
        self.subtype = subtype


class CastError(ValueError):
    """Raised when an object couldn't be converted to the appropriate tag type.

    Casting occurs when adding items to list tags and nbt schema
    instances. If the item couldn't be converted to the required type,
    the conversion raises an error.

    .. doctest::

        >>> integers = List[Int]()
        >>> integers.append("foo")
        Traceback (most recent call last):
        ...
        nbtlib.tag.CastError: Couldn't cast 'foo' to Int

    Note that casting only occurs when the value is an unwrapped python object.
    Incompatible tags will raise an :class:`IncompatibleItemType` exception.

    .. doctest::

        >>> strings = List[String]()
        >>> strings.append(123)
        >>> strings
        List[String]([String('123')])
        >>> strings.append(Int(123))
        Traceback (most recent call last):
        ...
        nbtlib.tag.IncompatibleItemType: Int(123) should be a String tag
    """

    def __init__(self, obj, tag_type):
        super().__init__(f"Couldn't cast {obj!r} to {tag_type.__name__}")
        self.obj = obj
        self.tag_type = tag_type


# Read/write helpers for numeric and string values


def read_numeric(fmt, fileobj, byteorder="big"):
    """Read a numeric value from a file-like object."""
    try:
        fmt = fmt[byteorder]
        return fmt.unpack(fileobj.read(fmt.size))[0]
    except StructError:
        return 0
    except KeyError as exc:
        raise ValueError("Invalid byte order") from exc


def write_numeric(fmt, value, fileobj, byteorder="big"):
    """Write a numeric value to a file-like object."""
    try:
        fileobj.write(fmt[byteorder].pack(value))
    except KeyError as exc:
        raise ValueError("Invalid byte order") from exc


def read_string(fileobj, byteorder="big"):
    """Read a string from a file-like object."""
    length = read_numeric(USHORT, fileobj, byteorder)
    return fileobj.read(length).decode("utf-8", "replace")


def write_string(value, fileobj, byteorder="big"):
    """Write a string to a file-like object."""
    data = value.encode("utf-8")
    write_numeric(USHORT, len(data), fileobj, byteorder)
    fileobj.write(data)


# Path helpers


def find_tag(key, tags):
    """Return the first recursively matching tag."""
    for tag in tags:
        if isinstance(tag, (Compound, List)):
            value = tag.get(key)
            if value is None:
                value = find_tag(
                    key, list(tag if isinstance(tag, List) else tag.values())
                )
            if value is not None:
                return value
    return None


# Tag definitions


class Base:
    """Base class inherited by all nbt tags.

    This class defines the API shared by all nbt tags. Derived classes
    that define a :attr:`tag_id` attribute are considered as concrete
    tag implementations and are registered in the :attr:`all_tags`
    registry. Concrete tag implementations inherit from both the
    :class:`Base` class and their associated builtin data type.

    Attributes:
        all_tags: A dictionary mapping tag ids to child classes.

            .. doctest::

                >>> pprint(Base.all_tags)
                {0: <class 'nbtlib.tag.End'>,
                 1: <class 'nbtlib.tag.Byte'>,
                 2: <class 'nbtlib.tag.Short'>,
                 3: <class 'nbtlib.tag.Int'>,
                 4: <class 'nbtlib.tag.Long'>,
                 5: <class 'nbtlib.tag.Float'>,
                 6: <class 'nbtlib.tag.Double'>,
                 7: <class 'nbtlib.tag.ByteArray'>,
                 8: <class 'nbtlib.tag.String'>,
                 9: <class 'nbtlib.tag.List'>,
                 10: <class 'nbtlib.tag.Compound'>,
                 11: <class 'nbtlib.tag.IntArray'>,
                 12: <class 'nbtlib.tag.LongArray'>}

            The mapping is used by the :meth:`get_tag` classmethod to
            retrieve the tag type when parsing the binary format.

        tag_id: The id of the tag in the binary format.

            .. doctest::

                >>> Int.tag_id
                3

        serializer: The name of the associated snbt serializer.

            .. doctest ::

                >>> Int.serializer
                'numeric'
    """

    __slots__ = ()
    all_tags = {}
    tag_id = None
    serializer = None

    def __init_subclass__(cls):
        # Add class to the `all_tags` dictionary if it has a tag id
        if cls.tag_id is not None and cls.tag_id not in cls.all_tags:
            cls.all_tags[cls.tag_id] = cls

    @classmethod
    def get_tag(cls, tag_id):
        """Return the tag class corresponding to the given tag id.

        .. doctest ::

            >>> Base.get_tag(3)
            <class 'nbtlib.tag.Int'>

        Arguments:
            tag_id: The tag id must be valid otherwise the method raises a ``KeyError``.
        """
        return cls.all_tags[tag_id]

    @classmethod
    def parse(cls, fileobj, byteorder="big"):
        r"""Parse data from a file-like object and return a tag instance.

        The default implementation does nothing. Concrete tags override
        this method.

        Arguments:
            fileobj: A readable file-like object.
            byteorder: Whether the nbt data is big-endian or little-endian.

                .. doctest::

                    >>> Int.parse(io.BytesIO(b"\x00\x00\x00\x01"))
                    Int(1)
                    >>> Int.parse(io.BytesIO(b"\x01\x00\x00\x00"), byteorder="little")
                    Int(1)
        """

    def write(self, fileobj, byteorder="big"):
        r"""Write the binary representation of the tag to a file-like object.

        The default implementation does nothing. Concrete tags override
        this method.

        Arguments:
            fileobj: A writable file-like object.
            byteorder: Whether the nbt data should be big-endian or little-endian.

                .. doctest::

                    >>> big_endian = io.BytesIO()
                    >>> little_endian = io.BytesIO()
                    >>> Int(1).write(big_endian)
                    >>> Int(1).write(little_endian, byteorder="little")
                    >>> big_endian.getvalue()
                    b'\x00\x00\x00\x01'
                    >>> little_endian.getvalue()
                    b'\x01\x00\x00\x00'
        """

    def match(self, other):
        """Check whether the tag recursively matches a subset of values.

        The default implementation checks that the :attr:`tag_id` of the argument
        matches and that the two instances are equal. Concrete tags override
        this method.

        .. doctest::

            >>> data = Compound({
            ...     'foo': Int(42),
            ...     'hello': String('world')
            ... })
            >>> data.match({'foo': 42})
            True
        """
        if hasattr(other, "tag_id") and self.tag_id != other.tag_id:
            return False
        return self == other

    def snbt(self, indent=None, compact=False, quote=None):
        """Return the snbt literal corresponding to the tag instance.

        .. doctest::

            >>> Compound({"foo": Long(123)}).snbt()
            '{foo: 123L}'
            >>> Compound({"foo": Long(123)}).snbt(compact=True)
            '{foo:123L}'
            >>> print(Compound({"foo": Long(123)}).snbt(indent=4))
            {
                foo: 123L
            }
        """
        return serialize_tag(self, indent=indent, compact=compact, quote=quote)

    def unpack(self, json=False):
        """Return the unpacked nbt value as an instance of the associated base type.

        .. doctest::

            >>> Compound({"foo": Long(123)}).unpack()
            {'foo': 123}

        Arguments:
            json: Whether the returned value should be json-serializable.

                This argument will convert array tags into plain python lists
                instead of numpy arrays.

                .. doctest::

                    >>> Compound({"foo": ByteArray([1, 2, 3])}).unpack()
                    {'foo': array([1, 2, 3], dtype=int8)}
                    >>> Compound({"foo": ByteArray([1, 2, 3])}).unpack(json=True)
                    {'foo': [1, 2, 3]}
        """
        return None

    def __repr__(self):
        if self.tag_id is not None:
            return f"{self.__class__.__name__}({super().__repr__()})"
        return super().__repr__()


class End(Base):
    """Nbt tag used to mark the end of compound tags.

    :class:`End` tags are the markers that terminate compound tags in
    the binary format. They need to exist as a type but can't be used on
    their own so manual instantiation raises an :class:`EndInstantiation`
    exception.

    .. doctest::

        >>> End()
        Traceback (most recent call last):
        ...
        nbtlib.tag.EndInstantiation: End tags can't be instantiated
    """

    __slots__ = ()
    tag_id = 0

    def __new__(cls, *args, **kwargs):
        raise EndInstantiation()


class Numeric(Base):
    r"""Intermediate class that represents a numeric nbt tag.

    This class inherits from the :class:`Base` class and implements
    :meth:`parse` and :meth:`write` for all the numeric nbt tags using
    the :attr:`fmt` attribute.

    Derived tags will use the ``numeric`` serializer and can specify a
    literal suffix with the :attr:`suffix` attribute.

    Attributes:
        fmt: The struct format used to pack and unpack the tag value.

            .. doctest::

                >>> Int.fmt['big'].pack(1)
                b'\x00\x00\x00\x01'
                >>> Int.fmt['little'].pack(1)
                b'\x01\x00\x00\x00'

        suffix: The suffix used by the ``numeric`` snbt serializer.

            .. doctest::

                >>> Long.suffix
                'L'
                >>> Long(123).snbt()
                '123L'
    """

    __slots__ = ()
    serializer = "numeric"
    fmt = None
    suffix = ""

    @classmethod
    def parse(cls, fileobj, byteorder="big"):
        """Override :meth:`Base.parse` for numeric tags."""
        return cls(read_numeric(cls.fmt, fileobj, byteorder))

    def write(self, fileobj, byteorder="big"):
        """Override :meth:`Base.write` for numeric tags."""
        write_numeric(self.fmt, self, fileobj, byteorder)


class NumericInteger(Numeric, int):
    """Intermediate class that represents a numeric integer nbt tag.

    This class adds range checks to the :class:`Numeric` class. It also
    inherits from ``int`` and raises an :class:`OutOfRange` exception
    when the tag is instantiated with a value that can't be represented
    by the associated struct format.

    .. doctest::

        >>> Byte(127)
        Byte(127)
        >>> Byte(128)
        Traceback (most recent call last):
        ...
        nbtlib.tag.OutOfRange: Byte(128) is out of range

    Concrete tag implementations deriving from this class also inherit
    utilities for interpreting the value of the tag as an unsigned
    integer.

    .. doctest::

        >>> value = Byte.from_unsigned(255)
        >>> value
        Byte(-1)
        >>> value.as_unsigned
        255

    Attributes:
        range: The supported range of values.

            .. doctest::

                >>> Byte.range
                range(-128, 128)
                >>> Int.range
                range(-2147483648, 2147483648)

        mask: The bit mask derived from the struct format.

            .. doctest::

                >>> f'{Byte.mask:b}'
                '11111111'

        bits: The bit length derived from the struct format.

            .. doctest::

                >>> Int.bits
                32
                >>> Long.bits
                64
    """

    __slots__ = ()
    range = None
    mask = None
    bits = None

    def __init_subclass__(cls):
        super().__init_subclass__()
        limit = 2 ** (8 * cls.fmt["big"].size - 1)
        cls.range = range(-limit, limit)
        cls.mask = limit * 2 - 1
        cls.bits = cls.mask.bit_length()

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        if int(self) not in cls.range:
            raise OutOfRange(self)
        return self

    def unpack(self, json=False):
        """Override :meth:`Base.unpack` for numeric integer tags."""
        return int(self)

    @property
    def as_unsigned(self):
        """Interpret the value of the tag as an unsigned integer."""
        return self & self.mask

    @classmethod
    def from_unsigned(cls, value):
        """Encode an unsigned integer as an integer tag."""
        return cls(value - (value * 2 & cls.mask + 1))


class Byte(NumericInteger):
    """Nbt tag representing a signed byte."""

    __slots__ = ()
    tag_id = 1
    fmt = BYTE
    suffix = "b"


class Short(NumericInteger):
    """Nbt tag representing a signed 16 bit integer."""

    __slots__ = ()
    tag_id = 2
    fmt = SHORT
    suffix = "s"


class Int(NumericInteger):
    """Nbt tag representing a signed 32 bit integer."""

    __slots__ = ()
    tag_id = 3
    fmt = INT


class Long(NumericInteger):
    """Nbt tag representing a signed 64 bit integer."""

    __slots__ = ()
    tag_id = 4
    fmt = LONG
    suffix = "L"


class Float(Numeric, float):
    """Nbt tag representing a single-precision floating point number."""

    __slots__ = ()
    tag_id = 5
    fmt = FLOAT
    suffix = "f"

    def unpack(self, json=False):
        """Override :meth:`Base.unpack` for float tags."""
        return float(self)


class Double(Numeric, float):
    """Nbt tag representing a double-precision floating point number."""

    __slots__ = ()
    tag_id = 6
    fmt = DOUBLE
    suffix = "d"

    def unpack(self, json=False):
        """Override :meth:`Base.unpack` for double tags."""
        return float(self)


class Array(Base, np.ndarray):
    """Intermediate class that represents an array nbt tag.

    Array tags are represented by numpy arrays. This class combines the
    :class:`Base` class with the numpy ``ndarray`` type and implements
    :meth:`parse` and :meth:`write` depending on a few additional
    attributes.

    Derived tags will use the ``array`` serializer and can specify an array
    prefix with the :attr:`array_prefix` attribute.

    Attributes:
        item_type: The numpy array data type.

            .. doctest::

                >>> IntArray.item_type['big']
                dtype('>i4')
                >>> IntArray.item_type['little']
                dtype('int32')

        array_prefix: The literal array prefix.

            .. doctest::

                >>> IntArray.array_prefix
                'I'
                >>> IntArray([1, 2, 3]).snbt()
                '[I; 1, 2, 3]'

        wrapper: The tag used to wrap the integer.

            .. doctest::

                >>> IntArray.wrapper
                <class 'nbtlib.tag.Int'>
                >>> IntArray([1, 2, 3])[0]
                Int(1)
    """

    __slots__ = ()
    serializer = "array"
    item_type = None
    array_prefix = None
    wrapper = None

    def __new__(cls, value=None, *, length=0, byteorder="big"):
        item_type = cls.item_type[byteorder]
        if value is None:
            return np.zeros((length,), item_type).view(cls)
        return np.asarray(value, item_type).view(cls)

    @classmethod
    def parse(cls, fileobj, byteorder="big"):
        """Override :meth:`Base.parse` for array tags."""
        item_type = cls.item_type[byteorder]
        data = fileobj.read(read_numeric(INT, fileobj, byteorder) * item_type.itemsize)
        return cls(np.frombuffer(data, item_type), byteorder=byteorder)

    def write(self, fileobj, byteorder="big"):
        """Override :meth:`Base.write` for array tags."""
        write_numeric(INT, len(self), fileobj, byteorder)
        array = self if self.item_type[byteorder] is self.dtype else self.byteswap()
        fileobj.write(array.tobytes())

    def unpack(self, json=False):
        """Override :meth:`Base.unpack` for array tags."""
        return self.tolist() if json else np.copy(self)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return super().__getitem__(index)
        return int.__new__(self.wrapper, super().__getitem__(index))

    def __bool__(self):
        return all(self)

    def __repr__(self):
        return f'{self.__class__.__name__}([{", ".join(map(str, self))}])'


class ByteArray(Array):
    """Nbt tag representing an array of signed bytes."""

    __slots__ = ()
    tag_id = 7
    item_type = get_format(np.dtype, "b")
    array_prefix = "B"
    wrapper = Byte


class String(Base, str):
    """Nbt tag representing a string."""

    __slots__ = ()
    tag_id = 8
    serializer = "string"

    @classmethod
    def parse(cls, fileobj, byteorder="big"):
        """Override :meth:`Base.parse` for string tags."""
        return cls(read_string(fileobj, byteorder))

    def write(self, fileobj, byteorder="big"):
        """Override :meth:`Base.write` for string tags."""
        write_string(self, fileobj, byteorder)

    def unpack(self, json=False):
        """Override :meth:`Base.unpack` for string tags."""
        return str(self)


class List(Base, list):
    """Nbt tag representing a list of other nbt tags.

    Nbt lists are homogeneous and can only hold a single type of tag. This
    constraint is enforced by requiring the :class:`List` class to be
    subclassed and define an appropriate :attr:`subtype` attribute. The
    ``class_getitem`` operator is defined so that
    ``List[TagName]`` returns a subclass with the subtype ``TagName``.

    .. doctest::

        >>> List[Int]
        <class 'nbtlib.tag.List[Int]'>
        >>> List[Int].subtype
        <class 'nbtlib.tag.Int'>

    The base class constructor returns an instance of the appropriate
    subtype if it can infer the subtype from the elements of the given
    iterable. Check out :meth:`infer_list_subtype` for details.

    .. doctest::

        >>> List([Int(123)])
        List[Int]([Int(123)])

    The class inherits from the :class:`Base` class and the ``list``
    builtin. The inherited mutating operations are overridden to include
    an ``isinstance`` check. For example, the :meth:`append` method
    will raise an :class:`IncompatibleItemType` exception if the list
    subtype doesn't match the item type.

    .. doctest::

        >>> strings = List[String]()
        >>> strings.append(Int(123))
        Traceback (most recent call last):
        ...
        nbtlib.tag.IncompatibleItemType: Int(123) should be a String tag

    To make things a bit more ergonomic, arbitrary python objects are
    transparently converted to the list subtype.

    .. doctest::

        >>> strings.append(String("foo"))
        >>> strings.append("bar")
        >>> strings
        List[String]([String('foo'), String('bar')])

    However, note that impossible conversions raise a :class:`CastError`.

    .. doctest::

        >>> List[Int](["foo"])
        Traceback (most recent call last):
        ...
        nbtlib.tag.CastError: Couldn't cast 'foo' to Int

    Finally, list tags support path indexing. Check out the
    :ref:`path documentation <NBT Paths>` for more details.

    .. doctest::

        >>> compounds = List([
        ...     Compound({"foo": Int(123)}),
        ...     Compound({"foo": Int(456)}),
        ... ])
        >>> compounds[Path("[{foo: 456}]")]
        Compound({'foo': Int(456)})
    """

    __slots__ = ()
    tag_id = 9
    serializer = "list"
    variants = {}
    subtype = End

    def __new__(cls, iterable=()):
        if cls.subtype is End:
            iterable = tuple(iterable)
            subtype = cls.infer_list_subtype(iterable)
            cls = cls[subtype]
        return super().__new__(cls, iterable)

    def __init__(self, iterable=()):
        super().__init__(map(self.cast_item, iterable))

    def __class_getitem__(cls, item):
        if item is End:
            return List

        try:
            return cls.variants[item]
        except KeyError:
            variant = type(
                f"List[{item.__name__}]", (List,), {"__slots__": (), "subtype": item}
            )
            cls.variants[item] = variant
            return variant

    @staticmethod
    def infer_list_subtype(items):
        """Infer a list subtype from a list of items.

        .. doctest::

            >>> List.infer_list_subtype([Int(123)])
            <class 'nbtlib.tag.Int'>

        This method is used by the base :class:`List` constructor to figure
        out the subtype of the :class:`List` subclass that should be returned.

        Arguments:
            items:
                Can be any kind of iterable containing at least one tag instance
                and zero or more python objects convertible to the type of the
                tag instance.

                .. doctest::

                    >>> List.infer_list_subtype([123, Int(456)])
                    <class 'nbtlib.tag.Int'>
        """
        subtype = End

        for item in items:
            item_type = type(item)
            if not issubclass(item_type, Base):
                continue

            if subtype is End:
                subtype = item_type
                if not issubclass(subtype, List):
                    return subtype
            elif subtype is not item_type:
                stype, itype = subtype, item_type
                generic = List
                while issubclass(stype, List) and issubclass(itype, List):
                    stype, itype = stype.subtype, itype.subtype
                    generic = List[generic]

                if stype is End:
                    subtype = item_type
                elif itype is not End:
                    return generic.subtype
        return subtype

    @classmethod
    def parse(cls, fileobj, byteorder="big"):
        """Override :meth:`Base.parse` for list tags."""
        tag = cls.get_tag(read_numeric(BYTE, fileobj, byteorder))
        length = read_numeric(INT, fileobj, byteorder)
        return cls[tag](tag.parse(fileobj, byteorder) for _ in range(length))

    def write(self, fileobj, byteorder="big"):
        """Override :meth:`Base.write` for list tags."""
        write_numeric(BYTE, self.subtype.tag_id, fileobj, byteorder)
        write_numeric(INT, len(self), fileobj, byteorder)
        for elem in self:
            elem.write(fileobj, byteorder)

    def match(self, other):
        """Override :meth:`Base.match` for list tags.

        The method returns ``True`` if all the elements the iterable
        appear at least once in the current instance.

        .. doctest::

            >>> List[Int]([1, 2, 3]).match([3, 1])
            True
        """
        if not isinstance(other, list):
            return False
        if not other:
            return not self
        return all(any(item.match(other_item) for item in self) for other_item in other)

    def unpack(self, json=False):
        """Override :meth:`Base.unpack` for list tags."""
        return [item.unpack(json) for item in self]

    def find(self, key, default=None):
        """Return the first recursively matching tag.

        .. doctest::

            >>> tag = parse_nbt("[{data: {value: 42}}, {data: {value: 7}}]")
            >>> tag.find(Path("data.value"))
            Int(42)
            >>> tag.find("value")
            Int(42)

        Arguments:
            index: Can be a string, an integer, a slice or an instance of :class:`nbtlib.path.Path`.
            default: Returned when the element could not be found.
        """
        value = find_tag(key, [self])
        return default if value is None else value

    def get(self, index, default=None):
        """Return the element at the specified index.

        Arguments:
            index: Can be an integer, a slice or an instance of :class:`nbtlib.path.Path`.
            default: Returned when the element could not be found.
        """
        return (self.get_all(index) or [default])[0]

    def get_all(self, index):
        """Return all the elements matching the specified index.

        Arguments:
            index: Can be an integer, a slice or an instance of :class:`nbtlib.path.Path`.
        """
        try:
            return (
                [super().__getitem__(index)]
                if isinstance(index, (int, slice))
                else index.get(self)
            )
        except (IndexError, AttributeError):
            return []

    def __getitem__(self, index):
        if isinstance(index, (int, slice)):
            return super().__getitem__(index)
        values = index.get(self)
        if not values:
            raise IndexError(index)
        return values[0]

    def __setitem__(self, index, value):
        if isinstance(index, (int, slice)):
            super().__setitem__(
                index,
                [self.cast_item(item) for item in value]
                if isinstance(index, slice)
                else self.cast_item(value),
            )
        else:
            index.set(self, value)

    def __delitem__(self, index):
        if isinstance(index, (int, slice)):
            super().__delitem__(index)
        else:
            index.delete(self)

    def append(self, value):
        """Override ``list.append`` to include ``isinstance`` check and auto conversion."""
        super().append(self.cast_item(value))

    def extend(self, iterable):
        """Override ``list.extend`` to include ``isinstance`` check and auto conversion."""
        super().extend(map(self.cast_item, iterable))

    def insert(self, index, value):
        """Override ``list.insert`` to include ``isinstance`` check and auto conversion."""
        super().insert(index, self.cast_item(value))

    @classmethod
    def cast_item(cls, item):
        """Cast list item to the appropriate tag type.

        .. doctest::

            >>> List[Int].cast_item(123)
            Int(123)

        Arguments:
            item:
                Can be any object convertible to the current tag type. If the
                conversion fails, the method raises a :class:`CastError`.
        """
        if not isinstance(item, cls.subtype):
            incompatible = isinstance(item, Base) and not any(
                issubclass(cls.subtype, tag_type) and isinstance(item, tag_type)
                for tag_type in cls.all_tags.values()
            )
            if incompatible:
                raise IncompatibleItemType(item, cls.subtype)

            try:
                return cls.subtype(item)
            except EndInstantiation:
                raise ValueError(
                    "List tags without an explicit subtype must "
                    "either be empty or instantiated with "
                    "elements from which a subtype can be "
                    "inferred"
                ) from None
            except (IncompatibleItemType, CastError):
                raise
            except Exception as exc:
                raise CastError(item, cls.subtype) from exc
        return item


class Compound(Base, dict):
    """Nbt tag that represents a mapping of strings to other nbt tags.

    The class inherits from the :class:`Base` class and the ``dict``
    builtin. Compound tag instances support path indexing. Check out the
    :ref:`path documentation <NBT Paths>` for more details.

    .. doctest::

        >>> compound = Compound({'foo': Compound({'bar': Int(123)})})
        >>> compound[Path("foo.bar")]
        Int(123)

    Attributes:
        end_tag: Bytes used to mark the end of the compound.
    """

    __slots__ = ()
    tag_id = 10
    serializer = "compound"
    end_tag = b"\x00"

    @classmethod
    def parse(cls, fileobj, byteorder="big"):
        """Override :meth:`Base.parse` for compound tags."""
        self = cls()
        tag_id = read_numeric(BYTE, fileobj, byteorder)
        while tag_id != 0:
            name = read_string(fileobj, byteorder)
            self[name] = cls.get_tag(tag_id).parse(fileobj, byteorder)
            tag_id = read_numeric(BYTE, fileobj, byteorder)
        return self

    def write(self, fileobj, byteorder="big"):
        """Override :meth:`Base.write` for compound tags."""
        for name, tag in self.items():
            write_numeric(BYTE, tag.tag_id, fileobj, byteorder)
            write_string(name, fileobj, byteorder)
            tag.write(fileobj, byteorder)
        fileobj.write(self.end_tag)

    def match(self, other):
        """Override :meth:`Base.match` for compound tags.

        The method returns ``True`` if each key-value pair in the
        dictionary is present in the current instance.

        .. doctest::

            >>> compound = Compound({"foo": Int(123), "bar": Int(456)})
            >>> compound.match({"foo": Int(123)})
            True
        """
        return (
            isinstance(other, dict)
            and self.keys() >= other.keys()
            and all(self[key].match(value) for key, value in other.items())
        )

    def unpack(self, json=False):
        """Override :meth:`Base.unpack` for compound tags."""
        return {key: value.unpack(json) for key, value in self.items()}

    def find(self, key, default=None):
        """Return the first recursively matching tag.

        .. doctest::

            >>> tag = parse_nbt("{foo: {bar: [{value: 42}, {value: 7}]}}")
            >>> tag.find(Path("[1].value"))
            Int(7)
            >>> tag.find("value")
            Int(42)

        Arguments:
            index: Can be a string, an integer, a slice or an instance of :class:`nbtlib.path.Path`.
            default: Returned when the element could not be found.
        """
        value = find_tag(key, [self])
        return default if value is None else value

    def get(self, key, default=None):
        """Get the element with the specified key.

        Arguments:
            key: Can be a string or an instance of :class:`nbtlib.path.Path`.
            default: Returned when the element could not be found.
        """
        try:
            return (key.get(self) or [default])[0]
        except AttributeError:
            return super().get(key, default)

    def get_all(self, key):
        """Return all the elements matching the specified key.

        Arguments:
            index: Can be a string or an instance of :class:`nbtlib.path.Path`.
        """
        try:
            return [super().__getitem__(key)] if isinstance(key, str) else key.get(self)
        except KeyError:
            return []

    def __contains__(self, item):
        if isinstance(item, str):
            return super().__contains__(item)
        return bool(item.get(self))

    def __getitem__(self, key):
        if isinstance(key, str):
            return super().__getitem__(key)
        values = key.get(self)
        if not values:
            raise KeyError(key)
        return values[0]

    def __setitem__(self, key, value):
        if isinstance(key, str):
            super().__setitem__(key, value)
        else:
            key.set(self, value)

    def __delitem__(self, key):
        if isinstance(key, str):
            super().__delitem__(key)
        else:
            key.delete(self)

    def merge(self, other):
        """Recursively merge tags from another dictionary.

        .. doctest::

            >>> compound = Compound({
            ...     "value": Compound({"foo": Int(123), "bar": Int(456)}),
            ... })
            >>> compound.merge({
            ...     "value": {"bar": Int(-1), "hello": String("world")},
            ... })
            >>> compound["value"]
            Compound({'foo': Int(123), 'bar': Int(-1), 'hello': String('world')})

        Arguments:
            other: Can be a builtin ``dict`` or an instance of :class:`Compound`.
        """
        for key, value in other.items():
            if key in self and (
                isinstance(self[key], Compound) and isinstance(value, dict)
            ):
                self[key].merge(value)
            else:
                self[key] = value

    def with_defaults(self, other):
        """Return a new compound with recursively applied default values.

        .. doctest::

            >>> compound = Compound({
            ...     "value": Compound({"foo": Int(123), "bar": Int(456)}),
            ... })
            >>> new_compound = compound.with_defaults({
            ...     "value": {"bar": Int(-1), "hello": String("world")},
            ... })
            >>> new_compound["value"]
            Compound({'bar': Int(456), 'hello': String('world'), 'foo': Int(123)})

        Arguments:
            other: Can be a builtin ``dict`` or an instance of :class:`Compound`.
        """
        result = Compound(other)
        for key, value in self.items():
            if key in result and (
                isinstance(value, Compound) and isinstance(result[key], dict)
            ):
                value = value.with_defaults(result[key])
            result[key] = value
        return result


class IntArray(Array):
    """Nbt tag representing an array of signed 32 bit integers."""

    __slots__ = ()
    tag_id = 11
    item_type = get_format(np.dtype, "i4")
    array_prefix = "I"
    wrapper = Int


class LongArray(Array):
    """Nbt tag representing an array of signed 64 bit integers."""

    __slots__ = ()
    tag_id = 12
    item_type = get_format(np.dtype, "i8")
    array_prefix = "L"
    wrapper = Long
