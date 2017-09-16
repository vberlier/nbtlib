
import struct
from array import array


__all__ = ['Byte', 'Short', 'Int', 'Long', 'Float', 'Double', 'ByteArray',
           'String', 'List', 'Compound', 'IntArray']


BYTE = struct.Struct('>b')
SHORT = struct.Struct('>h')
INT = struct.Struct('>i')
LONG = struct.Struct('>q')
FLOAT = struct.Struct('>f')
DOUBLE = struct.Struct('>d')


def read_numeric(fmt, buff):
    try:
        return fmt.unpack(buff.read(fmt.size))[0]
    except struct.error:
        return 0


def write_numeric(fmt, value, buff):
    buff.write(fmt.pack(value))


def read_string(buff):
    length = read_numeric(SHORT, buff)
    return buff.read(length).decode('utf-8')


def write_string(value, buff):
    data = value.encode('utf-8')
    write_numeric(SHORT, len(data), buff)
    buff.write(data)


class Base:
    __slots__ = ()
    tag_list = []
    id = None

    def __init_subclass__(cls, **kwargs):
        if cls.id is not None:
            if cls.id in (tag.id for tag in cls.tag_list):
                return
            cls.tag_list.append(cls)

    @classmethod
    def get_tag(cls, tag_id):
        return next(tag for tag in cls.tag_list if tag.id == tag_id)

    @classmethod
    def parse(cls, buff):
        pass

    def write(self, buff):
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}({super().__repr__()})'

    def __str__(self):
        return repr(self)


class End(Base):
    __slots__ = ()
    id = 0


class Numeric(Base):
    __slots__ = ()
    fmt = None

    @classmethod
    def parse(cls, buff):
        return cls(read_numeric(cls.fmt, buff))

    def write(self, buff):
        write_numeric(self.fmt, self, buff)


class Byte(Numeric, int):
    __slots__ = ()
    id = 1
    fmt = BYTE


class Short(Numeric, int):
    __slots__ = ()
    id = 2
    fmt = SHORT


class Int(Numeric, int):
    __slots__ = ()
    id = 3
    fmt = INT


class Long(Numeric, int):
    __slots__ = ()
    id = 4
    fmt = LONG


class Float(Numeric, float):
    __slots__ = ()
    id = 5
    fmt = FLOAT


class Double(Numeric, float):
    __slots__ = ()
    id = 6
    fmt = DOUBLE


class ByteArray(Base, array):
    __slots__ = ()
    id = 7

    def __new__(cls, *args, **kwargs):
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


class String(Base, str):
    __slots__ = ()
    id = 8

    @classmethod
    def parse(cls, buff):
        return cls(read_string(buff))

    def write(self, buff):
        write_string(self, buff)


class ListMeta(type):
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
    __slots__ = ()
    id = 9
    subtype = None

    def __init__(self, iterable=()):
        super().__init__(map(self._ensure_subtype, iterable))

    @classmethod
    def parse(cls, buff):
        tag = cls.get_tag(read_numeric(BYTE, buff))
        length = read_numeric(INT, buff)
        return cls[tag](tag.parse(buff) for _ in range(length))

    def write(self, buff):
        write_numeric(BYTE, self.subtype.id, buff)
        write_numeric(INT, len(self), buff)
        for elem in self:
            elem.write(buff)

    def __setitem__(self, key, value):
        super().__setitem__(key, self._ensure_subtype(value))

    def append(self, value):
        super().append(self._ensure_subtype(value))

    def extend(self, iterable):
        super().extend(map(self._ensure_subtype, iterable))

    def insert(self, index, value):
        super().insert(index, self._ensure_subtype(value))

    def _ensure_subtype(self, value):
        if not isinstance(value, self.subtype):
            return self.subtype(value)
        return value


class Compound(Base, dict):
    __slots__ = ()
    id = 10

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
            write_numeric(BYTE, tag.id, buff)
            write_string(name, buff)
            tag.write(buff)
        write_numeric(BYTE, End.id, buff)


class IntArray(Base, array):
    __slots__ = ()
    id = 11

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, 'i', *args, **kwargs)

    @classmethod
    def parse(cls, buff):
        int_array = cls()
        int_array.fromfile(buff, read_numeric(INT, buff))
        int_array.byteswap()
        return int_array

    def write(self, buff):
        write_numeric(INT, len(self), buff)
        self.byteswap()
        self.tofile(buff)
        self.byteswap()

    def __repr__(self):
        return f'{self.__class__.__name__}([{", ".join(map(str, self))}])'
