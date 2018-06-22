# nbtlib

[![Build Status](https://travis-ci.org/vberlier/nbtlib.svg?branch=master)](https://travis-ci.org/vberlier/nbtlib)
[![PyPI](https://img.shields.io/pypi/v/nbtlib.svg)](https://pypi.org/project/nbtlib/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nbtlib.svg)](https://pypi.org/project/nbtlib/)

> A python library to read and edit [nbt data](http://wiki.vg/NBT). Requires
python 3.6.

**Features**

- Create, read and edit nbt files
- Supports gzipped and uncompressed files
- Parse and serialize raw nbt data
- Define tag schemas that automatically enforce predefined tag types
- Convert nbt between binary form and literal notation
- Includes a CLI to quickly perform read/write/merge operations

## Installation

The package can be installed with `pip`.

```bash
$ pip install nbtlib
```

## Basic usage

The following examples will give you a very basic overview of what you
can do. For more advanced examples, check out the
"[Usage](https://github.com/vberlier/nbtlib/blob/master/docs/Usage.ipynb)"
notebook in the docs folder.

### Reading files

Reading files can be done directly with the `load()` function. The
`root` property contains the root nbt tag. Every nbt tag inherits from
its python counterpart so you can use all the usual builtin operations
on nbt tags.

```python
from nbtlib import nbt

nbt_file = nbt.load('bigtest.nbt')
assert nbt_file.root['intTest'] == 2147483647
```

### Editing files

You can use nbt files as context managers in order to save modifications
automatically at the end of the `with` block.

```python
from nbtlib import nbt
from nbtlib.tag import *

with nbt.load('demo.nbt') as demo:
    demo.root['counter'] = Int(demo.root['counter'] + 1)
```

You can also use the `save()` method.

```python
from nbtlib import nbt
from nbtlib.tag import *

demo = nbt.load('demo.nbt')
demo.root['counter'] = Int(demo.root['counter'] + 1)
demo.save()
```

For more details check out the "[Usage](https://github.com/vberlier/nbtlib/blob/master/docs/Usage.ipynb)"
notebook.

### Using schemas

A schema lets you create compound tags that enforce a specific tag type
for any given key.

```python
from nbtlib import schema
from nbtlib.tag import *

MySchema = schema('MySchema', {
    'foo': String,
    'bar': Short
})

my_object = MySchema({'foo': 'hello world', 'bar': 21})
assert isinstance(my_object['foo'], String)
```

### Nbt literals

`nbtlib` also defines utilities to deal with literal nbt data. For
instance, you can parse nbt literals using the `parse_nbt()` function.

```python
from nbtlib import parse_nbt
from nbtlib.tag import *

my_compound = parse_nbt('{foo:[hello,world],bar:[I;1,2,3]}')
assert my_compound == Compound({
    'foo': List[String](['hello', 'world']),
    'bar': IntArray([1, 2, 3])
})
```

## Command-line interface

The package comes with a small CLI that makes it easy to quickly perform
basic operations on nbt files.

```
$ nbt --help
usage: nbt [-h] (-r | -w <nbt> | -m <nbt>) [--plain] <file>

Perform basic operations on nbt files.

positional arguments:
    <file>      the target file

optional arguments:
    -h, --help  show this help message and exit
    -r          read nbt data from a file
    -w <nbt>    write nbt to a file
    -m <nbt>    merge nbt into an nbt file
    --plain     don't use gzip compression
```

### Read nbt data

You can read nbt files by using the `-r` option. This will print the
literal notation of the binary nbt data.

```bash
$ nbt -r demo.nbt
{counter:42}
```

You can use the following command if you want to save the output into a
file.

```bash
$ nbt -r my_file.nbt > my_file.txt
```

### Write nbt data

You can write nbt data to a file by using the `-w` option. This will
convert the literal nbt notation to its binary form and save it in the
specified file.

```bash
$ nbt -w '{foo:[1,2,3],bar:{hello:[B;1b,1b,0b,1b]}}' my_file.nbt
```

The file will be created if it doesn't already exist.

### Merge nbt data

Finally, you can merge some nbt data into an already existing file by
using the `-m` option. This will recursively update the file with
the values parsed from the literal argument.

```bash
$ nbt -m '{bar:{"new key":56f}}' my_file.nbt
```

You can check the result by using the `-r` option.

```bash
$ nbt -r my_file.nbt
{foo:[1,2,3],bar:{hello:[B;1b,1b,0b,1b],"new key":56.0f}}
```

Here, the compound values that aren't present in the input literal are
left untouched. Using the `-w` option instead of `-m` would
overwrite the whole file.

### Compression

By default, the CLI will assume that you're working with gzipped nbt
files. If you want to read, write or merge uncompressed nbt files, you
can use the `--plain` option.

**Reading**

```bash
$ nbt -r my_file.nbt --plain
{name:"Reading from an uncompressed file"}
```

**Writing**

```bash
$ nbt -w '{name:"Writing in an uncompressed file"} my_file.nbt --plain
```

**Merging**

```bash
$ nbt -m '{name:"Merging in an uncompressed file"} my_file.nbt --plain
```

## Contributing

Contributions are welcome. Unit tests are built with `pytest`. You can
run the test suite with:

```bash
$ python -m pytest tests
```

----

License - [MIT](https://github.com/vberlier/nbtlib/blob/master/LICENSE)
