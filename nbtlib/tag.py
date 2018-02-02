
"""This module contains nbt tag definitions.

All the tag classes defined here can be used to instantiate nbt tags.
They also all have a `parse` classmethod that reads nbt data from a
file-like object and returns a tag instance. Tag instances can write
their binary representation to file-like objects using the `write`
method.

Each tag inherits from the equivalent python builtin type. This means
that all the operations that are commonly used on the base types are
available on nbt tags.

Exported classes:
    End       -- Represents the end of a compound tag
    Byte      -- Represents a byte tag, inherits from `int`
    Short     -- Represents a short tag, inherits from `int`
    Int       -- Represents an int tag, inherits from `int`
    Long      -- Represents a long tag, inherits from `int`
    Float     -- Represents a float tag, inherits from `float`
    Double    -- Represents a double tag, inherits from `float`
    ByteArray -- Represents a byte array tag, inherits from `array`
    String    -- Represents a string tag, inherits from `str`
    List      -- Represents a generic list tag, inherits from `list`
    Compound  -- Represents a compound tag, inherits from `dict`
    IntArray  -- Represents an int array tag, inherits from `array`
"""


__all__ = ['End', 'Byte', 'Short', 'Int', 'Long', 'Float', 'Double',
           'ByteArray', 'String', 'List', 'Compound', 'IntArray']


import sys
import re
import json
import struct
from array import array


# Regex to detect if a string can be represented unquoted

UNQUOTED_STRING = re.compile(r'^[a-zA-Z0-9._+-]+$')


# Struct formats used to pack and unpack numeric values

BYTE = struct.Struct('>b')
SHORT = struct.Struct('>h')
INT = struct.Struct('>i')
LONG = struct.Struct('>q')
FLOAT = struct.Struct('>f')
DOUBLE = struct.Struct('>d')


# Escape nbt strings that must be quoted

def escape_string(string):
    """Escape nbt strings that cannot be written unquoted in nbt literals."""
    return json.dumps(string).replace('\\', r'\\').replace(r'\\"', r'\"')


# Read/write helpers for numeric and string values

def read_numeric(fmt, buff):
    """Read a numeric value from a file-like object."""
    try:
        return fmt.unpack(buff.read(fmt.size))[0]
    except struct.error:
        return 0


def write_numeric(fmt, value, buff):
    """Write a numeric value to a file-like object."""
    buff.write(fmt.pack(value))


def read_string(buff):
    """Read a string from a file-like object."""
    length = read_numeric(SHORT, buff)
    return buff.read(length).decode('utf-8')


def write_string(value, buff):
    """Write a string to a file-like object."""
    data = value.encode('utf-8')
    write_numeric(SHORT, len(data), buff)
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

    def __init_subclass__(cls):
        # Add class to the `all_tags` dictionnary if it has a tag id
        if cls.tag_id is not None and cls.tag_id not in cls.all_tags:
            cls.all_tags[cls.tag_id] = cls

    @classmethod
    def get_tag(cls, tag_id):
        """Return the class corresponding to the given tag id."""
        return cls.all_tags[tag_id]

    @classmethod
    def parse(cls, buff):
        """Parse data from a file-like object and return a tag instance."""
        pass

    def write(self, buff):
        """Write the binary representation of the tag to a file-like object."""
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'


class End(Base):
    """Nbt tag used to mark the end of a compound tag."""

    __slots__ = ()
    tag_id = 0


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
    fmt = None
    suffix = ''

    @classmethod
    def parse(cls, buff):
        return cls(read_numeric(cls.fmt, buff))

    def write(self, buff):
        write_numeric(self.fmt, self, buff)

    def __str__(self):
        return super().__str__() + self.suffix


class Byte(Numeric, int):
    """Nbt tag representing a signed byte."""

    __slots__ = ()
    tag_id = 1
    fmt = BYTE
    suffix = 'b'


class Short(Numeric, int):
    """Nbt tag representing a signed 16 bit integer."""

    __slots__ = ()
    tag_id = 2
    fmt = SHORT
    suffix = 's'


class Int(Numeric, int):
    """Nbt tag representing a signed 32 bit integer."""

    __slots__ = ()
    tag_id = 3
    fmt = INT


class Long(Numeric, int):
    """Nbt tag representing a signed 64 bit integer."""

    __slots__ = ()
    tag_id = 4
    fmt = LONG
    suffix = 'l'


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


class ByteArray(Base, array):
    """Nbt tag representing an array of signed bytes.

    The class inherits from the python array type. It passes the 'b'
    type code to the parent `__new__` method.
    """

    __slots__ = ()
    tag_id = 7

    def __new__(cls, *args, **kwargs):
        # The `b` type code is used to specify a signed byte
        return super().__new__(cls, 'b', *args, **kwargs)

    @classmethod
    def parse(cls, buff):
        byte_array = cls()
        byte_array.fromfile(buff, read_numeric(INT, buff))
        return byte_array

    def write(self, buff):
        write_numeric(INT, len(self), buff)
        self.tofile(buff)

    def __repr__(self):
        return f'{self.__class__.__name__}([{", ".join(map(str, self))}])'

    def __str__(self):
        elements = ','.join(f'{el}b' for el in self)
        return f'[B;{elements}]'


class String(Base, str):
    """Nbt tag representing a string."""

    __slots__ = ()
    tag_id = 8

    @classmethod
    def parse(cls, buff):
        return cls(read_string(buff))

    def write(self, buff):
        write_string(self, buff)

    def __str__(self):
        if UNQUOTED_STRING.match(self):
            return super().__str__()
        else:
            return escape_string(self)


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
    on list tag instances. Mutating operations have been overwrote to
    include an isinstance() check. For instance, when calling the
    `append` method, the appended item will be wrapped by the defined
    subtype if isinstance(item, TagName) returns False.

    Class attributes:
        subtype -- The nbt tag that will be used to wrap list items
    """

    __slots__ = ()
    tag_id = 9
    subtype = Base

    def __init__(self, iterable=()):
        super().__init__(map(self._cast, iterable))

    @classmethod
    def parse(cls, buff):
        tag = cls.get_tag(read_numeric(BYTE, buff))
        length = read_numeric(INT, buff)
        return cls[tag](tag.parse(buff) for _ in range(length))

    def write(self, buff):
        write_numeric(BYTE, self.subtype.tag_id, buff)
        write_numeric(INT, len(self), buff)
        for elem in self:
            elem.write(buff)

    def __setitem__(self, key, value):
        super().__setitem__(key, self._cast(value))

    def append(self, value):
        super().append(self._cast(value))

    def extend(self, iterable):
        super().extend(map(self._cast, iterable))

    def insert(self, index, value):
        super().insert(index, self._cast(value))

    def _cast(self, value):
        if not isinstance(value, self.subtype):
            return self.subtype(value)
        return value

    def __str__(self):
        return f'[{",".join(map(str, self))}]'


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
    end_tag = BYTE.pack(End.tag_id)

    @classmethod
    def parse(cls, buff):
        self = cls()
        tag_id = read_numeric(BYTE, buff)
        while tag_id != 0:
            name = read_string(buff)
            self[name] = cls.get_tag(tag_id).parse(buff)
            tag_id = read_numeric(BYTE, buff)
        return self

    def write(self, buff):
        for name, tag in self.items():
            write_numeric(BYTE, tag.tag_id, buff)
            write_string(name, buff)
            tag.write(buff)
        buff.write(self.end_tag)

    def merge(self, other):
        """Recursively merge tags from another compound."""
        for key, value in other.items():
            if key in self and (isinstance(self[key], Compound)
                                and isinstance(value, dict)):
                self[key].merge(value)
            else:
                self[key] = value

    def __str__(self):
        pairs = ','.join(f'{self.stringify_key(key)}:{value}'
                         for key, value in self.items())
        return '{' + pairs + '}'

    @staticmethod
    def stringify_key(key):
        if UNQUOTED_STRING.match(key):
            return key
        else:
            return escape_string(key)


class IntArray(Base, array):
    """Nbt tag representing an array of signed integers.

    The class inherits from the python array type. It passes the 'i'
    type code to the parent `__new__` method.
    """

    __slots__ = ()
    tag_id = 11

    def __new__(cls, *args, **kwargs):
        # The `i` type code is used to specify a signed 32 bit integer
        return super().__new__(cls, 'i', *args, **kwargs)

    @classmethod
    def parse(cls, buff):
        int_array = cls()
        int_array.fromfile(buff, read_numeric(INT, buff))
        int_array._swap_little_endian()
        return int_array

    def write(self, buff):
        write_numeric(INT, len(self), buff)
        self._swap_little_endian()
        self.tofile(buff)
        self._swap_little_endian()

    def _swap_little_endian(self):     # Python arrays use the system's endianness
        if sys.byteorder == 'little':  # so we need to perform a byteswap if the
            self.byteswap()            # system doesn't use big-endian integers

    def __repr__(self):
        return f'{self.__class__.__name__}([{", ".join(map(str, self))}])'

    def __str__(self):
        return f'[I;{",".join(map(str, self))}]'
