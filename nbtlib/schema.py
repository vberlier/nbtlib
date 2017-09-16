
from itertools import chain

from .tag import Compound


__all__ = ['schema', 'CompoundSchema']


def schema(name, dct):
    return type(name, (CompoundSchema,), {'__slots__': (), 'schema': dct})


class CompoundSchema(Compound):
    __slots__ = ()
    schema = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for key, value in self.items():
            correct_value = self._match_schema(key, value)
            if correct_value is not value:
                super().__setitem__(key, correct_value)

    def __setitem__(self, key, value):
        super().__setitem__(key, self._match_schema(key, value))

    def update(self, mapping, **kwargs):
        pairs = chain(mapping.items(), kwargs.items())
        super().update(
            (key, self._match_schema(value)) for key, value in pairs
        )

    def _match_schema(self, key, value):
        schema_type = self.schema.get(key, None)
        if schema_type and not isinstance(value, schema_type):
            return schema_type(value)
        return value
