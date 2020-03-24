r"""Definitions for all the nbt tag classes.

.. testsetup::

    import io
    import struct
    from pprint import pprint
    import nbtlib

All the tag classes have a :meth:`Base.parse` classmethod that reads
nbt data from a file-like object and returns a tag instance. Tag
instances can then write their binary representation back to file-like
objects using the :meth:`Base.write` method.

.. doctest::

    >>> fileobj = io.BytesIO(b'\x03\x00\x03foo\x00\x00\x00{\x00')
    >>> data = nbtlib.Compound.parse(fileobj)
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

+-------------------+------------------------------------------------------------+
| Base type         | Associated nbt tags                                        |
+===================+============================================================+
| **int**           | :class:`Byte`, :class:`Short`, :class:`Int`, :class:`Long` |
+-------------------+------------------------------------------------------------+
| **float**         | :class:`Float`, :class:`Double`                            |
+-------------------+------------------------------------------------------------+
| **str**           | :class:`String`                                            |
+-------------------+------------------------------------------------------------+
| **numpy.ndarray** | :class:`ByteArray`, :class:`IntArray`, :class:`LongArray`  |
+-------------------+------------------------------------------------------------+
| **list**          | :class:`List`                                              |
+-------------------+------------------------------------------------------------+
| **dict**          | :class:`Compound`                                          |
+-------------------+------------------------------------------------------------+

.. doctest::

    >>> data['foo'] = nbtlib.Int(10 * data['foo'])
    >>> data['bar'] = nbtlib.String('hello')
    >>> data
    Compound({'foo': Int(1230), 'bar': String('hello')})
"""


__all__ = ['Base', 'End', 'Numeric', 'NumericInteger', 'Byte', 'Short', 'Int',
           'Long', 'Float', 'Double', 'Array', 'ByteArray', 'String', 'List',
           'Compound', 'IntArray', 'LongArray', 'EndInstantiation',
           'OutOfRange', 'IncompatibleItemType', 'CastError']


from struct import Struct, error as StructError
import numpy as np

from .literal.serializer import serialize_tag


# Struct formats used to pack and unpack numeric values

def get_format(fmt, string):
    """Return a dictionary containing a format for each byte order."""
    return {'big': fmt('>' + string), 'little': fmt('<' + string)}

BYTE = get_format(Struct, 'b')
SHORT = get_format(Struct, 'h')
USHORT = get_format(Struct, 'H')
INT = get_format(Struct, 'i')
LONG = get_format(Struct, 'q')
FLOAT = get_format(Struct, 'f')
DOUBLE = get_format(Struct, 'd')


# Custom errors

class EndInstantiation(TypeError):
    """Raised when trying to instantiate an :class:`End` tag.

    :class:`End` tags are essentially markers that terminate compound
    tags in the binary format. They need to exist as a type but can't
    have a value of their own so manual instantiation raises an
    exception.
    """

    def __init__(self):
        super().__init__('End tags can\'t be instantiated')


class OutOfRange(ValueError):
    """Raised when a numeric value is out of range.

    Converting builtin ``int`` instances to numeric nbt tags can fail if
    the tag type isn't big enough.
    """

    def __init__(self, value):
        super().__init__(f'{value!r} is out of range')


class IncompatibleItemType(TypeError):
    """Raised when a list item is incompatible with the subtype of the list.

    Unlike builtin python lists, list tags must have a uniform subtype
    so adding an incompatible item to the list raises an error.
    """

    def __init__(self, item, subtype):
        super().__init__(f'{item!r} should be a {subtype.__name__} tag')
        self.item = item
        self.subtype = subtype


class CastError(ValueError):
    """Raised when an object couldn't be casted to the appropriate tag type.

    Casting occurs when adding items to list tags and nbt schema
    instances. If the item couldn't be converted to the required type,
    the conversion raises an error.
    """

    def __init__(self, obj, tag_type):
        super().__init__(f'Couldn\'t cast {obj!r} to {tag_type.__name__}')
        self.obj = obj
        self.tag_type = tag_type


# Read/write helpers for numeric and string values

def read_numeric(fmt, fileobj, byteorder='big'):
    """Read a numeric value from a file-like object."""
    try:
        fmt = fmt[byteorder]
        return fmt.unpack(fileobj.read(fmt.size))[0]
    except StructError:
        return 0
    except KeyError as exc:
        raise ValueError('Invalid byte order') from exc


def write_numeric(fmt, value, fileobj, byteorder='big'):
    """Write a numeric value to a file-like object."""
    try:
        fileobj.write(fmt[byteorder].pack(value))
    except KeyError as exc:
        raise ValueError('Invalid byte order') from exc


def read_string(fileobj, byteorder='big'):
    """Read a string from a file-like object."""
    length = read_numeric(USHORT, fileobj, byteorder)
    return fileobj.read(length).decode('utf-8')


def write_string(value, fileobj, byteorder='big'):
    """Write a string to a file-like object."""
    data = value.encode('utf-8')
    write_numeric(USHORT, len(data), fileobj, byteorder)
    fileobj.write(data)


# Tag definitions

class Base:
    """Base class inherited by all nbt tags.

    This class defines the abstract API implemented by all nbt tags.
    Derived classes that define a tag id are considered as concrete tag
    implementations and are registered in the :attr:`all_tags` registry.
    Concrete tag implementations inherit from both the :class:`Base`
    class and their associated builtin data type.

    The :meth:`write` method and the :meth:`parse` classmethod are
    overwritten by each concrete tag implementation as well as the
    :attr:`tag_id` and :attr:`serializer` class attributes.

    .. doctest::

        >>> nbtlib.Int.tag_id
        3
        >>> nbtlib.Int.serializer
        'numeric'

    It's worth mentioning that :func:`repr` returns a python
    representation of the tag and that calling :func:`str` or simply
    printing an nbt tag will output the snbt literal representing that
    tag.

    .. doctest::

        >>> data = nbtlib.Compound({'foo': nbtlib.Byte(1)})
        >>> print(repr(data))
        Compound({'foo': Byte(1)})
        >>> print(data)
        {foo: 1b}

    Attributes:
        all_tags: A dictionnary mapping tag ids to child classes.

            .. doctest::

                >>> pprint(nbtlib.Base.all_tags)
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
        serializer: The name of the associated snbt serializer.
    """

    __slots__ = ()
    all_tags = {}
    tag_id = None
    serializer = None

    def __init_subclass__(cls):
        # Add class to the `all_tags` dictionnary if it has a tag id
        if cls.tag_id is not None and cls.tag_id not in cls.all_tags:
            cls.all_tags[cls.tag_id] = cls

    @classmethod
    def get_tag(cls, tag_id):
        """Return the tag class corresponding to the given tag id."""
        return cls.all_tags[tag_id]

    @classmethod
    def parse(cls, fileobj, byteorder='big'):
        """Parse data from a file-like object and return a tag instance."""

    def write(self, fileobj, byteorder='big'):
        """Write the binary representation of the tag to a file-like object."""

    def match(self, other):
        """Check whether the tag recursively matches a subset of values.

        .. doctest::

            >>> data = nbtlib.Compound({
            ...     'foo': nbtlib.Int(42),
            ...     'hello': nbtlib.String('world')
            ... })
            >>> data.match({'foo': 42})
            True
        """
        if hasattr(other, 'tag_id') and self.tag_id != other.tag_id:
            return False
        return self == other

    def __repr__(self):
        if self.tag_id is not None:
            return f'{self.__class__.__name__}({super().__repr__()})'
        return super().__repr__()

    def __str__(self):
        try:
            return serialize_tag(self)
        except TypeError:
            return super().__str__()


class End(Base):
    """Nbt tag used to mark the end of a compound tag.

    End tags raise an :class:`EndInstantiation` exception upon
    instantiation.
    """

    __slots__ = ()
    tag_id = 0

    def __new__(cls, *args, **kwargs):
        raise EndInstantiation()


class Numeric(Base):
    """Intermediate class that represents a numeric nbt tag.

    This class is not meant to be instantiated. It inherits from the
    :class:`Base` class, defines an additional class attribute
    :attr:`fmt` and uses it to implement :meth:`parse` and :meth:`write`
    for all the numeric nbt tags. Derived classes overwrite the :attr:`fmt`
    attribute with the struct format corresponding to the tag's type.
    Concrete numeric nbt tags inherit from this class as well as the
    ``int`` or ``float`` builtin type.

    Attributes:
        fmt: The struct format used to pack and unpack the tag value.

            .. doctest::

                >>> nbtlib.Int.fmt['big'].pack(42) == struct.pack('>i', 42)
                True

        suffix: The suffix used by the numeric snbt serializer.

            .. doctest::

                >>> nbtlib.Long.suffix
                'L'
                >>> str(nbtlib.Long(1234))
                '1234L'
    """

    __slots__ = ()
    serializer = 'numeric'
    fmt = None
    suffix = ''

    @classmethod
    def parse(cls, fileobj, byteorder='big'):
        return cls(read_numeric(cls.fmt, fileobj, byteorder))

    def write(self, fileobj, byteorder='big'):
        write_numeric(self.fmt, self, fileobj, byteorder)


class NumericInteger(Numeric, int):
    """Intermediate class that represents a numeric integer nbt tag.

    This class adds range checks to the :class:`Numeric` class. It also
    inherits from the ``int`` builtin and raises an :class:`OutOfRange`
    exception when the tag is instantiated with a value that can't be
    represented by the specified struct format.

    .. doctest::

        >>> nbtlib.Byte(42)
        Byte(42)
        >>> nbtlib.Byte(9999)
        Traceback (most recent call last):
        ...
        nbtlib.tag.OutOfRange: Byte(9999) is out of range

    Concrete tag implementations deriving from this class also inherit
    utilities for interpreting the value of the tag as an unsigned
    integer.

    .. doctest::

        >>> value = nbtlib.Byte.from_unsigned(255)
        >>> value
        Byte(-1)
        >>> value.as_unsigned
        255

    Attributes:
        range: The supported range of values.

            .. doctest::

                >>> nbtlib.Byte.range
                range(-128, 128)
                >>> nbtlib.Int.range
                range(-2147483648, 2147483648)

        mask: The largest number that can be represented.

            .. doctest::

                >>> nbtlib.Byte.mask
                255

        bits: The bit length of the largest number that can be represented.

            .. doctest::

                >>> nbtlib.Int.bits
                32
                >>> nbtlib.Long.bits
                64
    """

    __slots__ = ()
    range = None
    mask = None
    bits = None

    def __init_subclass__(cls):
        super().__init_subclass__()
        limit = 2 ** (8 * cls.fmt['big'].size - 1)
        cls.range = range(-limit, limit)
        cls.mask = limit * 2 - 1
        cls.bits = cls.mask.bit_length()

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        if int(self) not in cls.range:
            raise OutOfRange(self)
        return self

    @property
    def as_unsigned(self):
        """Interpret the value of the tag as an unsigned integer."""
        return self & self.mask

    @classmethod
    def from_unsigned(cls, value):
        """Create a numeric integer tag from an unsigned integer."""
        return cls(value - (value * 2 & cls.mask + 1))


class Byte(NumericInteger):
    """Nbt tag representing a signed byte."""

    __slots__ = ()
    tag_id = 1
    fmt = BYTE
    suffix = 'b'


class Short(NumericInteger):
    """Nbt tag representing a signed 16 bit integer."""

    __slots__ = ()
    tag_id = 2
    fmt = SHORT
    suffix = 's'


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
    suffix = 'L'


class Float(Numeric, float):
    """Nbt tag representing a single-precision floating point number."""

    __slots__ = ()
    tag_id = 5
    fmt = FLOAT
    suffix = 'f'


class Double(Numeric, float):
    """Nbt tag representing a double-precision floating point number."""

    __slots__ = ()
    tag_id = 6
    fmt = DOUBLE
    suffix = 'd'


class Array(Base, np.ndarray):
    """Intermediate class that represents an array nbt tag.

    Array tags are represented by numpy arrays. This class combines the
    :class:`Base` class with the numpy :class:`ndarray` type and
    implements :meth:`parse` and :meth:`write` depending on a few
    additional class attributes.

    Attributes:
        item_type: The numpy array data type.

            .. doctest::

                >>> nbtlib.IntArray.item_type['big']
                dtype('>i4')

        array_prefix: The literal array prefix.

            .. doctest::

                >>> print(nbtlib.IntArray([1, 2, 3]))
                [I; 1, 2, 3]
                >>> nbtlib.IntArray.array_prefix
                'I'

        wrapper: The tag used to wrap the integer.

            .. doctest::

                >>> nbtlib.IntArray.wrapper
                <class 'nbtlib.tag.Int'>
    """

    __slots__ = ()
    serializer = 'array'
    item_type = None
    array_prefix = None
    wrapper = None

    def __new__(cls, value=None, *, length=0, byteorder='big'):
        item_type = cls.item_type[byteorder]
        if value is None:
            return np.zeros((length,), item_type).view(cls)
        return np.asarray(value, item_type).view(cls)

    @classmethod
    def parse(cls, fileobj, byteorder='big'):
        item_type = cls.item_type[byteorder]
        data = fileobj.read(read_numeric(INT, fileobj, byteorder) * item_type.itemsize)
        return cls(np.frombuffer(data, item_type), byteorder=byteorder)

    def write(self, fileobj, byteorder='big'):
        write_numeric(INT, len(self), fileobj, byteorder)
        array = self if self.item_type[byteorder] is self.dtype else self.byteswap()
        fileobj.write(array.tobytes())

    def __getitem__(self, index):
        if isinstance(index, slice):
            return super().__getitem__(index)
        return int.__new__(self.wrapper, super().__getitem__(index))

    def __bool__(self):
        return all(self)

    def __repr__(self):
        return f'{self.__class__.__name__}([{", ".join(int.__str__(el) for el in self)}])'


class ByteArray(Array):
    """Nbt tag representing an array of signed bytes."""

    __slots__ = ()
    tag_id = 7
    item_type = get_format(np.dtype, 'b')
    array_prefix = 'B'
    wrapper = Byte


class String(Base, str):
    """Nbt tag representing a string."""

    __slots__ = ()
    tag_id = 8
    serializer = 'string'

    @classmethod
    def parse(cls, fileobj, byteorder='big'):
        return cls(read_string(fileobj, byteorder))

    def write(self, fileobj, byteorder='big'):
        write_string(self, fileobj, byteorder)


class ListMeta(type):
    """Allows class indexing to create and return subclasses on the fly.

    This metaclass is used by the List tag class definition. It allows
    the class to create and return subclasses of itself when it is
    indexed with a tag type. If a subclass of the specified type has
    already been created, the existing subclass will be returned.
    """

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls.variants = {}

    def __getitem__(cls, item):
        if item is End:
            return List

        try:
            return List.variants[item]
        except KeyError:
            variant = type(f'{List.__name__}[{item.__name__}]', (List,),
                           {'__slots__': (), 'subtype': item})
            List.variants[item] = variant
            return variant


class List(Base, list, metaclass=ListMeta):
    """Nbt tag representing a list of other nbt tags.

    Nbt lists are uniform and can only hold a single type of tag. This
    constraint is enforced by requiring the tag class to be subclassed
    and define an appropriate :attr:`subtype` attribute. A metaclass
    make it so that accessing ``List[TagName]`` will return a subclass
    of :class:`List` with the subtype ``TagName``.

    .. doctest::

        >>> nbtlib.List[nbtlib.Int].subtype
        <class 'nbtlib.tag.Int'>

    The class inherits from :class:`Base` and the ``list`` builtin.
    The inherited mutating operations have been overwritten to include
    an :func:`isinstance` check. For instance, when calling the
    :meth:`append` method, the item will be wrapped by the defined
    :attr:`subtype` if ``isinstance(item, cls.subtype)`` returns False.

    Attributes:
        subtype: The nbt tag that will be used to wrap list items.
    """

    __slots__ = ()
    tag_id = 9
    serializer = 'list'
    subtype = End

    def __new__(cls, iterable=()):
        if cls.subtype is End:
            iterable = tuple(iterable)
            subtype = cls.infer_list_subtype(iterable)
            cls = cls[subtype]
        return super().__new__(cls, iterable)

    def __init__(self, iterable=()):
        super().__init__(map(self.cast_item, iterable))

    @staticmethod
    def infer_list_subtype(items):
        """Infer a list subtype from a collection of items."""
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
    def parse(cls, fileobj, byteorder='big'):
        tag = cls.get_tag(read_numeric(BYTE, fileobj, byteorder))
        length = read_numeric(INT, fileobj, byteorder)
        return cls[tag](tag.parse(fileobj, byteorder) for _ in range(length))

    def write(self, fileobj, byteorder='big'):
        write_numeric(BYTE, self.subtype.tag_id, fileobj, byteorder)
        write_numeric(INT, len(self), fileobj, byteorder)
        for elem in self:
            elem.write(fileobj, byteorder)

    def match(self, other):
        if not isinstance(other, list):
            return False
        if not other:
            return not self
        return all(any(item.match(other_item) for item in self) for other_item in other)

    def get(self, index, default=None):
        return (self.get_all(index) or [default])[0]

    def get_all(self, index):
        try:
            return ([super().__getitem__(index)]
                    if isinstance(index, (int, slice)) else index.get(self))
        except IndexError:
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
            super().__setitem__(index, [self.cast_item(item) for item in value]
                                     if isinstance(index, slice) else self.cast_item(value))
        else:
            index.set(self, value)

    def __delitem__(self, index):
        if isinstance(index, (int, slice)):
            super().__delitem__(index)
        else:
            index.delete(self)

    def append(self, value):
        super().append(self.cast_item(value))

    def extend(self, iterable):
        super().extend(map(self.cast_item, iterable))

    def insert(self, index, value):
        super().insert(index, self.cast_item(value))

    @classmethod
    def cast_item(cls, item):
        """Cast list item to the appropriate tag type."""
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
                raise ValueError('List tags without an explicit subtype must '
                                 'either be empty or instantiated with '
                                 'elements from which a subtype can be '
                                 'inferred') from None
            except (IncompatibleItemType, CastError):
                raise
            except Exception as exc:
                raise CastError(item, cls.subtype) from exc
        return item


class Compound(Base, dict):
    """Nbt tag that represents a mapping of strings to other nbt tags.

    The Compound class inherits both from Base and the python builtin
    dict type. This means that all the operations that are usually
    available on python dictionaries are supported.

    Class attributes:
        end_tag -- Bytes used to mark the end of the compound
    """

    __slots__ = ()
    tag_id = 10
    serializer = 'compound'
    end_tag = b'\x00'

    @classmethod
    def parse(cls, fileobj, byteorder='big'):
        self = cls()
        tag_id = read_numeric(BYTE, fileobj, byteorder)
        while tag_id != 0:
            name = read_string(fileobj, byteorder)
            self[name] = cls.get_tag(tag_id).parse(fileobj, byteorder)
            tag_id = read_numeric(BYTE, fileobj, byteorder)
        return self

    def write(self, fileobj, byteorder='big'):
        for name, tag in self.items():
            write_numeric(BYTE, tag.tag_id, fileobj, byteorder)
            write_string(name, fileobj, byteorder)
            tag.write(fileobj, byteorder)
        fileobj.write(self.end_tag)

    def match(self, other):
        return isinstance(other, dict) and self.keys() >= other.keys() and all(
            self[key].match(value) for key, value in other.items()
        )

    def get(self, key, default=None):
        if isinstance(key, str):
            return super().get(key, default)
        return (key.get(self) or [default])[0]

    def get_all(self, key):
        try:
            return ([super().__getitem__(key)]
                    if isinstance(key, str) else key.get(self))
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
        """Recursively merge tags from another compound."""
        for key, value in other.items():
            if key in self and (isinstance(self[key], Compound)
                                and isinstance(value, dict)):
                self[key].merge(value)
            else:
                self[key] = value

    def with_defaults(self, other):
        """Return a new compound with recursively applied default values."""
        result = Compound(other)
        for key, value in self.items():
            if key in result and (isinstance(value, Compound)
                                  and isinstance(result[key], dict)):
                value = value.with_defaults(result[key])
            result[key] = value
        return result


class IntArray(Array):
    """Nbt tag representing an array of signed integers."""

    __slots__ = ()
    tag_id = 11
    item_type = get_format(np.dtype, 'i4')
    array_prefix = 'I'
    wrapper = Int


class LongArray(Array):
    """Nbt tag representing an array of signed longs."""

    __slots__ = ()
    tag_id = 12
    item_type = get_format(np.dtype, 'i8')
    array_prefix = 'L'
    wrapper = Long
