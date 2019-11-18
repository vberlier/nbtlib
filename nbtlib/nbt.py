"""Utilities for loading and creating nbt files.

.. testsetup::

    import nbtlib

The most common way to load nbt files is to use the :func:`load`
function. To create new nbt files you can instantiate the :class:`File`
class with the desired nbt data and call the :meth:`File.save` method.
"""


__all__ = ['load', 'File']


import gzip

from .tag import Compound


def load(filename, *, gzipped=None, byteorder='big'):
    """Load the nbt file at the specified location.

    .. doctest::

        >>> nbtlib.load('docs/nbt_files/bigtest.nbt')
        <File 'Level': Compound({...})>

    Arguments:
        gzipped: Whether the file is gzipped or not.

            If the argument is not specified, the function will read the
            magic number of the file to figure out if the file is
            gzipped.

            .. doctest::

                >>> nbt_file = nbtlib.load('docs/nbt_files/hello_world.nbt', gzipped=False)
                >>> nbt_file.gzipped
                False

            The function simply delegates to :meth:`File.load`
            when the argument is specified explicitly.

        byteorder: Whether the file is big-endian or little-endian.

            The default value is ``'big'`` so files are interpreted as
            big-endian if the argument is not specified. You can set the
            argument to ``'little'`` to use the little-endian encoding.

            .. doctest::

                >>> nbt_file = nbtlib.load('docs/nbt_files/hello_world_little.nbt', byteorder='little')
                >>> nbt_file.byteorder
                'little'

    Returns:
        An instance of the dict-like :class:`File` class holding all the
        data that could be parsed from the binary file. Data can be
        retrieved with the index operator just like with regular python
        dictionaries.

    You can use the resulting :class:`File` instance as a context
    manager. The :meth:`File.save` method will be called at the end of
    the ``with`` statement.

    .. doctest::

        >>> with nbtlib.load('docs/nbt_files/demo.nbt') as demo:
        ...     demo.root['counter'] = nbtlib.Int(demo.root['counter'] + 1)
    """
    # Delegate to `File.load` if the gzipped argument is set explicitly
    if gzipped is not None:
        return File.load(filename, gzipped, byteorder)

    # Read the magic number otherwise and call `File.from_fileobj` with
    # the appropriate file object
    with open(filename, 'rb') as fileobj:
        magic_number = fileobj.read(2)
        fileobj.seek(0)

        if magic_number == b'\x1f\x8b':
            fileobj = gzip.GzipFile(fileobj=fileobj)

        return File.from_fileobj(fileobj, byteorder)


class File(Compound):
    """Class representing a compound nbt file.

    .. doctest::

        >>> nbt_file = nbtlib.File({
        ...     'Data': nbtlib.Compound({
        ...         'hello': nbtlib.String('world')
        ...    })
        ... })

    The class inherits from :class:`nbtlib.tag.Compound`, so all the
    builtin ``dict`` operations inherited by
    :class:`nbtlib.tag.Compound` are also available on
    :class:`File` instances.

    .. doctest::

        >>> nbt_file.items()
        dict_items([('Data', Compound({'hello': String('world')}))])
        >>> nbt_file['Data']
        Compound({'hello': String('world')})

    You can use the inherited :meth:`write` method to write the binary
    data to a file-like object and create a :class:`File` instance from
    a file-like object with the inherited :meth:`parse` classmethod.

    .. testsetup::

        import io

    .. doctest::

        >>> fileobj = io.BytesIO()
        >>> nbt_file.write(fileobj)
        >>> fileobj.getvalue()
        b'\\n\\x00\\x04Data\\x08\\x00\\x05hello\\x00\\x05world\\x00'
        >>> fileobj.seek(0)
        0
        >>> nbtlib.File.parse(fileobj) == nbt_file
        True

    Attributes:
        filename:
            The name of the file, ``None`` by default. The attribute is
            set automatically when the file is returned from the
            :func:`load` helper function and can also be set in the
            constructor.

            .. doctest::

                >>> nbt_file.filename is None
                True
                >>> nbtlib.load('docs/nbt_files/demo.nbt').filename
                'docs/nbt_files/demo.nbt'

        gzipped:
            Boolean indicating if the file is gzipped. The attribute can
            also be set in the constructor. New files are uncompressed
            by default.

            .. doctest::

                >>> nbtlib.File(nbt_file, gzipped=True).gzipped
                True

        byteorder:
            The byte order, either ``'big'`` or ``'little'``. The
            attribute can also be set in the constructor. By default new
            files are big-endian.

            .. doctest::

                >>> nbtlib.File(nbt_file, byteorder='little').byteorder
                'little'

    .. automethod:: parse

    .. automethod:: write
    """

    # We remove the inherited end tag as the end of nbt files is
    # specified by the end of the file
    end_tag = b''

    def __init__(self, *args, gzipped=False, byteorder='big', filename=None):
        super().__init__(*args)
        self.filename = filename
        self.gzipped = gzipped
        self.byteorder = byteorder

    @property
    def root_name(self):
        """The name of the root nbt tag.

        Used by the :attr:`root` property to retrieve the first value of
        the root compound tag. You can also use the property to change
        the name of the root tag of the file.

        .. doctest::

            >>> nbt_file.root_name
            'Data'
            >>> nbt_file.root_name = 'NewData'
            >>> nbt_file
            <File 'NewData': Compound({'hello': String('world')})>
        """
        return next(iter(self), None)

    @root_name.setter
    def root_name(self, value):
        self[value] = self.pop(self.root_name)

    @property
    def root(self):
        """The root nbt tag of the file.

        .. doctest::

            >>> nbt_file.root
            Compound({'hello': String('world')})
            >>> nbt_file['Data']
            Compound({'hello': String('world')})
        """
        return self[self.root_name]

    @root.setter
    def root(self, value):
        self[self.root_name] = value

    @classmethod
    def from_fileobj(cls, fileobj, byteorder='big'):
        """Load an nbt file from a proper file object.

        The ``fileobj`` argument can be either a standard
        ``io.BufferedReader`` for uncompressed nbt or a
        ``gzip.GzipFile`` for gzipped nbt data. The function simply
        calls to the :meth:`parse` classmethod and sets the
        :attr:`filename` and :attr:`gzipped` attributes depending on the
        type of the ``fileobj`` argument.
        """
        self = cls.parse(fileobj, byteorder)
        self.filename = getattr(fileobj, 'name', self.filename)
        self.gzipped = isinstance(fileobj, gzip.GzipFile)
        self.byteorder = byteorder
        return self

    @classmethod
    def load(cls, filename, gzipped, byteorder='big'):
        """Read, parse and return the nbt file at the specified location.

        The ``gzipped`` argument should indicate whether the specified
        file is gzipped. The ``byteorder`` argument lets you specify
        if the file is big-endian or little-endian.

        .. doctest::

            >>> nbtlib.File.load('docs/nbt_files/bigtest.nbt', gzipped=True)
            <File 'Level': Compound({...})>

        The method is used by the :func:`load` helper function when the
        ``gzipped`` keyword-only argument is specified explicitly.
        """
        open_file = gzip.open if gzipped else open
        with open_file(filename, 'rb') as fileobj:
            return cls.from_fileobj(fileobj, byteorder)

    def save(self, filename=None, *, gzipped=None, byteorder=None):
        """Write the file at the specified location.

        The ``gzipped`` keyword-only argument indicates if the file
        should be gzipped. The ``byteorder`` keyword-only argument lets
        you specify whether the file should be big-endian or
        little-endian.

        Unspecified arguments will default to the instance's
        ``filename``, ``gzipped`` and ``byteorder`` attributes. Calling
        the method without a ``filename`` will raise a ``ValueError`` if
        the ``filename`` attribute is ``None``.

        .. doctest::

            >>> demo = nbtlib.load('docs/nbt_files/demo.nbt')

            # Overwrite
            >>> demo.save()

            # Make a gzipped copy
            >>> demo.save('docs/nbt_files/demo_copy.nbt', gzipped=True)

            # Convert the file to little-endian
            >>> demo.save('docs/nbt_files/demo_little.nbt', byteorder='little')

        Note that the method is called without any argument at the end
        ``with`` statement when the :class:`File` instance is used as a
        context manager.

        .. doctest::

            >>> with demo:
            ...     demo.root['counter'] = nbtlib.Int(0)

        In the above example the file would be overwritten at the end of
        the ``with`` statement.
        """
        if gzipped is None:
            gzipped = self.gzipped
        if filename is None:
            filename = self.filename

        if filename is None:
            raise ValueError('No filename specified')

        open_file = gzip.open if gzipped else open
        with open_file(filename, 'wb') as fileobj:
            self.write(fileobj, byteorder or self.byteorder)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.root_name!r}: {self.root!r}>'
