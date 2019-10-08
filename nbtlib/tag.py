"""This module contains nbt tag definitions.

All the tag classes defined here can be used to instantiate nbt tags.
They also all have a `parse` classmethod that reads nbt data from a
file-like object and returns a tag instance. Tag instances can write
their binary representation to file-like objects using the `write`
method.

Each tag inherits from the equivalent python data type. This means that
all the operations that are commonly used on the base types are
available on nbt tags.

Exported classes:
    End       -- Represents the end of a compound tag
    Byte      -- Represents a byte tag, inherits from `int`
    Short     -- Represents a short tag, inherits from `int`
    Int       -- Represents an int tag, inherits from `int`
    Long      -- Represents a long tag, inherits from `int`
    Float     -- Represents a float tag, inherits from `float`
    Double    -- Represents a double tag, inherits from `float`
    ByteArray -- Represents a byte array tag, inherits from `ndarray`
    String    -- Represents a string tag, inherits from `str`
    List      -- Represents a generic list tag, inherits from `list`
    Compound  -- Represents a compound tag, inherits from `dict`
    IntArray  -- Represents an int array tag, inherits from `ndarray`
    LongArray -- Represents a long array tag, inherits from `ndarray`

Exported exceptions:
    EndInstantiation     -- Raised when instantiating an End tag
    OutOfRange           -- Raised when the value of a numerical tag is out of range
    IncompatibleItemType -- Raised when the type of a list item is incompatible
    CastError            -- Raised when casting a value to a tag fails
"""


__all__ = ['End', 'Byte', 'Short', 'Int', 'Long', 'Float', 'Double',
           'ByteArray', 'String', 'List', 'Compound', 'IntArray', 'LongArray',
           'EndInstantiation', 'OutOfRange', 'IncompatibleItemType',
           'CastError']


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
    """Raised when trying to instantiate an `End` tag."""

    def __init__(self):
        super().__init__('End tags can\'t be instantiated')


class OutOfRange(ValueError):
    """Raised when a numeric value is out of range."""

    def __init__(self, value):
        super().__init__(f'{value!r} is out of range')


class IncompatibleItemType(TypeError):
    """Raised when a list item is incompatible with the subtype of the list."""

    def __init__(self, item, subtype):
        super().__init__(f'{item!r} should be a {subtype.__name__} tag')
        self.item = item
        self.subtype = subtype


class CastError(ValueError):
    """Raised when an object couldn't be casted to the appropriate tag type."""

    def __init__(self, obj, tag_type):
        super().__init__(f'Couldn\'t cast {obj!r} to {tag_type.__name__}')
        self.obj = obj
        self.tag_type = tag_type


# Read/write helpers for numeric and string values

def read_numeric(fmt, buff, byteorder='big'):
    """Read a numeric value from a file-like object."""
    try:
        fmt = fmt[byteorder]
        return fmt.unpack(buff.read(fmt.size))[0]
    except StructError:
        return 0
    except KeyError as exc:
        raise ValueError('Invalid byte order') from exc


def write_numeric(fmt, value, buff, byteorder='big'):
    """Write a numeric value to a file-like object."""
    try:
        buff.write(fmt[byteorder].pack(value))
    except KeyError as exc:
        raise ValueError('Invalid byte order') from exc


def read_string(buff, byteorder='big'):
    """Read a string from a file-like object."""
    length = read_numeric(USHORT, buff, byteorder)
    return buff.read(length).decode('utf-8')


def write_string(value, buff, byteorder='big'):
    """Write a string to a file-like object."""
    data = value.encode('utf-8')
    write_numeric(USHORT, len(data), buff, byteorder)
    buff.write(data)


# Tag definitions

class Base:
    """Base class inherited by all nbt tags.

    This class is not meant to be instantiated. Derived classes that
    define a tag id are required to override the `parse` classmethod and
    the `write` method.

    Class attributes:
        all_tags -- Dictionnary mapping tag ids to child classes
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
        """Return the class corresponding to the given tag id."""
        return cls.all_tags[tag_id]

    @classmethod
    def parse(cls, buff, byteorder='big'):
        """Parse data from a file-like object and return a tag instance."""

    def write(self, buff, byteorder='big'):
        """Write the binary representation of the tag to a file-like object."""

    def match(self, other):
        """Check whether the tag recursively matches a specific subset of values."""
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
    """Nbt tag used to mark the end of a compound tag."""

    __slots__ = ()
    tag_id = 0

    def __new__(cls, *args, **kwargs):
        raise EndInstantiation()


class Numeric(Base):
    """Intermediate class that represents a numeric nbt tag.

    This class is not meant to be instantiated. It inherits from the
    `Base` class and defines an additional class attribute `fmt`.
    Derived classes must assign this attribute to the struct format
    corresponding to the tag type. They must also inherit from a builtin
    numeric type (`int` or `float`).

    The class overrides `parse` and `write` and uses the `fmt`
    attribute to pack and unpack the tag value.

    Class attributes:
        fmt -- The struct format used to pack and unpack the tag value
    """

    __slots__ = ()
    serializer = 'numeric'
    fmt = None
    suffix = ''

    @classmethod
    def parse(cls, buff, byteorder='big'):
        return cls(read_numeric(cls.fmt, buff, byteorder))

    def write(self, buff, byteorder='big'):
        write_numeric(self.fmt, self, buff, byteorder)


class NumericInteger(Numeric, int):
    """Intermediate class that represents a numeric integer nbt tag.

    This class is not meant to be instantiated. It inherits from the
    `Base` class and `int` and defines additional class attribute.
    Derived class will inherit the `as_unsigned` property and
    `from_unsigned` class method.

    Class attributes:
        range -- The supported range of values
        mask  -- The largest number that can be represented
        bits  -- The bit length of the largest number that can be represented
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
        """Create a tag from an unsigned integer."""
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

    This class is not meant to be instantiated. It inherits from the
    `Base` class and the numpy `ndarray` type.

    Class attributes:
        item_type    -- The numpy array data type
        array_prefix -- The literal array prefix
        wrapper      -- The tag used to wrap the integer
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
    def parse(cls, buff, byteorder='big'):
        item_type = cls.item_type[byteorder]
        data = buff.read(read_numeric(INT, buff, byteorder) * item_type.itemsize)
        return cls(np.frombuffer(data, item_type), byteorder=byteorder)

    def write(self, buff, byteorder='big'):
        write_numeric(INT, len(self), buff, byteorder)
        array = self if self.item_type[byteorder] is self.dtype else self.byteswap()
        buff.write(array.tobytes())

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
    def parse(cls, buff, byteorder='big'):
        return cls(read_string(buff, byteorder))

    def write(self, buff, byteorder='big'):
        write_string(self, buff, byteorder)


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

    The list can only hold a single type of tag. To enforce this
    constraint, the class must be subclassed and define an appropriate
    subtype. The `ListMeta` metaclass is used to seamlessly implement
    this operation. This means that accessing List[TagName] will return
    a subclass of List with the subtype TagName.

    On top of that, List inherits from Base and the python builtin list
    type. This means that all the usual list operations are supported
    on list tag instances. Mutating operations have been overwritten to
    include an isinstance() check. For instance, when calling the
    `append` method, the appended item will be wrapped by the defined
    subtype if isinstance(item, TagName) returns False.

    Class attributes:
        subtype -- The nbt tag that will be used to wrap list items
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
    def parse(cls, buff, byteorder='big'):
        tag = cls.get_tag(read_numeric(BYTE, buff, byteorder))
        length = read_numeric(INT, buff, byteorder)
        return cls[tag](tag.parse(buff, byteorder) for _ in range(length))

    def write(self, buff, byteorder='big'):
        write_numeric(BYTE, self.subtype.tag_id, buff, byteorder)
        write_numeric(INT, len(self), buff, byteorder)
        for elem in self:
            elem.write(buff, byteorder)

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
    def parse(cls, buff, byteorder='big'):
        self = cls()
        tag_id = read_numeric(BYTE, buff, byteorder)
        while tag_id != 0:
            name = read_string(buff, byteorder)
            self[name] = cls.get_tag(tag_id).parse(buff, byteorder)
            tag_id = read_numeric(BYTE, buff, byteorder)
        return self

    def write(self, buff, byteorder='big'):
        for name, tag in self.items():
            write_numeric(BYTE, tag.tag_id, buff, byteorder)
            write_string(name, buff, byteorder)
            tag.write(buff, byteorder)
        buff.write(self.end_tag)

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
