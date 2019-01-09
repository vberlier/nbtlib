"""This module contains utilities for loading and creating nbt files.

Exported items:
    load -- Helper function to load nbt files
    File -- Class that represents an nbt file, inherits from `Compound`
"""


__all__ = ['load', 'File']


import gzip

from .tag import Compound


def load(filename, *, gzipped=None, byteorder='big'):
    """Load the nbt file at the specified location.

    By default, the function will figure out by itself if the file is
    gzipped before loading it. You can pass a boolean to the `gzipped`
    keyword only argument to specify explicitly whether the file is
    compressed or not. You can also use the `byteorder` keyword only
    argument to specify whether the file is little-endian or big-endian.
    """
    if gzipped is not None:
        return File.load(filename, gzipped, byteorder)

    # if we don't know we read the magic number
    with open(filename, 'rb') as buff:
        magic_number = buff.read(2)
        buff.seek(0)

        if magic_number == b'\x1f\x8b':
            buff = gzip.GzipFile(fileobj=buff)

        return File.from_buffer(buff, byteorder)


class File(Compound):
    """Class representing a compound nbt file.

    The class inherits from `Compound`, so all of the dict operations
    inherited by `Compound` are also available on `File` instances.

    The `load` class method can be use to load files from disk. If
    you need to create the file from a file-like object you can use the
    inherited `parse` method. Getting the root tag of the file can be
    done with the `root` property. You can use the `save` method to save
    modifications.

    Using the `File` instance as a context manager will automatically
    save modifications when the `__exit__` method is called.

    Attributes:
        filename  -- The name of the file
        gzipped   -- Boolean indicating if the file is gzipped
        byteorder -- The byte order (either 'big' or 'little')
    """

    # We remove the inherited end tag as the end of nbt files is
    # specified by the end of the file buffer
    end_tag = b''

    def __init__(self, *args, gzipped=False, byteorder='big'):
        super().__init__(*args)
        self.filename = None
        self.gzipped = gzipped
        self.byteorder = byteorder

    @property
    def root_name(self):
        """The name of the root nbt tag."""
        return next(iter(self), None)

    @root_name.setter
    def root_name(self, value):
        self[value] = self.pop(self.root_name)

    @property
    def root(self):
        """The root nbt tag of the file."""
        return self[self.root_name]

    @root.setter
    def root(self, value):
        self[self.root_name] = value

    @classmethod
    def from_buffer(cls, buff, byteorder='big'):
        """Load nbt file from a file-like object.

        The `buff` argument can be either a standard `io.BufferedReader`
        for uncompressed nbt or a `gzip.GzipFile` for gzipped nbt data.
        """
        self = cls.parse(buff, byteorder)
        self.filename = getattr(buff, 'name', self.filename)
        self.gzipped = isinstance(buff, gzip.GzipFile)
        self.byteorder = byteorder
        return self

    @classmethod
    def load(cls, filename, gzipped, byteorder='big'):
        """Read, parse and return the file at the specified location.

        The `gzipped` argument is used to indicate if the specified
        file is gzipped. The `byteorder` argument lets you specify
        whether the file is big-endian or little-endian.
        """
        open_file = gzip.open if gzipped else open
        with open_file(filename, 'rb') as buff:
            return cls.from_buffer(buff, byteorder)

    def save(self, filename=None, *, gzipped=None, byteorder=None):
        """Write the file at the specified location.

        The `gzipped` keyword only argument indicates if the file should
        be gzipped. The `byteorder` keyword only argument lets you
        specify whether the file should be big-endian or little-endian.

        If the method is called without any argument, it will default to
        the instance attributes and use the file's `filename`,
        `gzipped` and `byteorder` attributes. Calling the method without
        a `filename` will raise a `ValueError` if the `filename` of the
        file is `None`.
        """
        if gzipped is None:
            gzipped = self.gzipped
        if filename is None:
            filename = self.filename

        if filename is None:
            raise ValueError('No filename specified')

        open_file = gzip.open if gzipped else open
        with open_file(filename, 'wb') as buff:
            self.write(buff, byteorder or self.byteorder)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.root_name!r}: {self.root!r}>'
