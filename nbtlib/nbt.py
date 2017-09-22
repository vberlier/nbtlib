
import gzip

from .tag import Compound


__all__ = ['load', 'File']


def load(filename, *, gzipped=None):
    if gzipped is None:
        with open(filename, 'rb') as buff:
            magic_number = buff.read(2)
            gzipped = magic_number == b'\x1f\x8b'
    return File.load(filename, gzipped)


class File(Compound):
    end_tag = b''

    def __init__(self, *args, gzipped=False):
        super().__init__(*args)
        self.filename = None
        self.gzipped = gzipped

    @property
    def root_name(self):
        return next(iter(self), None)

    @root_name.setter
    def root_name(self, value):
        self[value] = self.pop(self.root_name)

    @property
    def root(self):
        return self[self.root_name]

    @root.setter
    def root(self, value):
        self[self.root_name] = value

    @classmethod
    def load(cls, filename, gzipped):
        open_file = gzip.open if gzipped else open
        with open_file(filename, 'rb') as buff:
            self = cls.parse(buff)

        self.filename = filename
        self.gzipped = gzipped
        return self

    def save(self, filename=None, *, gzipped=None):
        if gzipped is None:
            gzipped = self.gzipped
        if filename is None:
            filename = self.filename

        open_file = gzip.open if gzipped else open
        with open_file(filename, 'wb') as buff:
            self.write(buff)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.root_name!r}: {self.root!r}>'
