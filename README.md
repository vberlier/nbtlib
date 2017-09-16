
# nbtlib

> A python library to read and edit nbt data.

:warning: In early development, use at your own risk.

## Basic usage

The following examples will give you a very basic overview of what you can do. For more advanced examples, check out the docs.

### Reading files

```py
from nbtlib import nbt

nbt_file = nbt.load('bigtest.nbt')
assert nbt_file.root['intTest'] == 2147483647
```

### Editing files

```py
from nbtlib import nbt
from nbtlib.tag import *

with nbt.load('demo.nbt') as demo:
    demo.root['counter'] = Int(demo.root['counter'] + 1)
```

### Using schemas

```py
from nbtlib import schema
from nbtlib.tag import *

MySchema = schema('MySchema', {
    'foo': String,
    'bar': Short
})

my_object = MySchema({'foo': 'hello world', 'bar': 21})
assert isinstance(my_object['foo'], String)
```
