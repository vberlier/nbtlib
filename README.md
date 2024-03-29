# nbtlib

[![GitHub Actions](https://github.com/vberlier/nbtlib/workflows/CI/badge.svg)](https://github.com/vberlier/nbtlib/actions)
[![PyPI](https://img.shields.io/pypi/v/nbtlib.svg)](https://pypi.org/project/nbtlib/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nbtlib.svg)](https://pypi.org/project/nbtlib/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Discord](https://img.shields.io/discord/900530660677156924?color=7289DA&label=discord&logo=discord&logoColor=fff)](https://discord.gg/98MdSGMm8j)

> A python library to read and edit [nbt data](http://wiki.vg/NBT). Requires
> python 3.8.

**Features**

- Create, read and edit nbt files
- Supports gzipped and uncompressed files
- Supports big-endian and little-endian files
- Parse and serialize raw nbt data
- Define tag schemas that automatically enforce predefined tag types
- Convert nbt between binary form and literal notation
- Use nbt paths to access deeply nested properties
- Includes a CLI to quickly perform read/write/merge operations

## Installation

> **Notice 🚧**
>
> Version `2.0` is actively being worked on and is not stable yet. You should probably keep using version `1.12.1` for the moment. You can check out the `2.0` roadmap in the [`nbtlib 2.0` issue](https://github.com/vberlier/nbtlib/issues/156).

The package can be installed with `pip`.

```bash
$ pip install "nbtlib==1.12.1"
```

## Basic usage

The following examples will give you a very basic overview of what you
can do. For more advanced examples, check out the
"[Usage](https://github.com/vberlier/nbtlib/blob/main/docs/Usage.ipynb)"
notebook in the docs folder.

### Reading files

The `nbtlib.load` function can be used to load nbt files as `nbtlib.File` objects. Every nbt tag inherits from
its python counterpart. This means that all the builtin operations defined on the python counterpart can be used on nbt tags.

```python
import nbtlib

nbt_file = nbtlib.load('bigtest.nbt')
assert nbt_file['intTest'] == 2147483647
```

For example, instances of `nbtlib.File` inherit from regular `Compound` tags, which themselves inherit from the builtin python dictionary `dict`. Similarly, instances of `Int` tags inherit from the builtin class `int`.

For more details on loading nbt files and how to work with nbt tags check out the "[Usage](https://github.com/vberlier/nbtlib/blob/main/docs/Usage.ipynb)"
notebook.

### Editing files

You can use instances of `nbtlib.File` as context managers in order to save modifications
automatically at the end of the `with` statement.

```python
import nbtlib
from nbtlib.tag import Int

with nbtlib.load('demo.nbt') as demo:
    demo['counter'] = Int(demo['counter'] + 1)
```

You can also call the `save` method manually.

```python
import nbtlib
from nbtlib.tag import Int

demo = nbtlib.load('demo.nbt')
demo['counter'] = Int(demo['counter'] + 1)
demo.save()
```

For more details on the `save` method check out the "[Usage](https://github.com/vberlier/nbtlib/blob/main/docs/Usage.ipynb)"
notebook.

### Using schemas

`nbtlib` allows you to define `Compound` schemas that enforce a specific tag type
for any given key.

```python
from nbtlib import schema
from nbtlib.tag import Short, String

MySchema = schema('MySchema', {
    'foo': String,
    'bar': Short
})

my_object = MySchema({'foo': 'hello world', 'bar': 21})

assert isinstance(my_object, MySchema)
assert isinstance(my_object['foo'], String)
```

For more details on schemas check out the "[Usage](https://github.com/vberlier/nbtlib/blob/main/docs/Usage.ipynb)"
notebook.

### Nbt literals

You can parse nbt literals using the `nbtlib.parse_nbt` function.

```python
from nbtlib import parse_nbt
from nbtlib.tag import String, List, Compound, IntArray

my_compound = parse_nbt('{foo: [hello, world], bar: [I; 1, 2, 3]}')
assert my_compound == Compound({
    'foo': List[String](['hello', 'world']),
    'bar': IntArray([1, 2, 3])
})
```

Nbt tags can be serialized to their literal representation with the `nbtlib.serialize_tag` function.

```python
from nbtlib import serialize_tag
from nbtlib.tag import String, List, Compound, IntArray

my_compound = Compound({
    'foo': List[String](['hello', 'world']),
    'bar': IntArray([1, 2, 3])
})
assert serialize_tag(my_compound) == '{foo: ["hello", "world"], bar: [I; 1, 2, 3]}'
```

For more details on nbt literals check out the "[Usage](https://github.com/vberlier/nbtlib/blob/main/docs/Usage.ipynb)"
notebook.

### Nbt paths

Nbt paths can be used to access deeply nested properties in nbt data. The implementation is based on information available on the [Minecraft wiki](https://minecraft.gamepedia.com/Commands/data#NBT_path).

```python
from nbtlib import parse_nbt, Path

data = parse_nbt('{a: [{b: {c: 42}}]}')
assert data['a'][0]['b']['c'] == 42
assert data[Path('a[0].b.c')] == 42
```

You can retrieve, modify and delete multiple properties at the same time.

```python
from nbtlib import parse_nbt, Path
from nbtlib.tag import Int

data = parse_nbt('{foo: [{a: 1, b: {c: 42}}, {a: 2, b: {c: 0}}]}')

data[Path('foo[].a')] = Int(99)
assert str(data) == '{foo: [{a: 99, b: {c: 42}}, {a: 99, b: {c: 0}}]}'

assert data.get_all(Path('foo[].b.c')) == [42, 0]

del data[Path('foo[].b{c: 0}')]
assert str(data) == '{foo: [{a: 99, b: {c: 42}}, {a: 99}]}'
```

Nbt paths are immutable but can be manipulated and combined together to form new paths.

```python
from nbtlib import Path
from nbtlib.tag import Compound

path = Path()['hello']['world']
assert path[:][Compound({'a': Int(0)})] == 'hello.world[{a: 0}]'

assert path + path == 'hello.world.hello.world'
assert sum('abcdef', Path()) == 'a.b.c.d.e.f'

assert Path()[0] + 'foo{a: 1}' + '{b: 2}.bar' == '[0].foo{a: 1, b: 2}.bar'

assert path['key.with.dots'] == 'hello.world."key.with.dots"'
assert path + 'key.with.dots' == 'hello.world.key.with.dots'

```

## Command-line interface

The package comes with a small CLI that makes it easy to quickly perform
basic operations on nbt files.

```
$ nbt --help
usage: nbt [-h] [-r | -s] [-w <nbt> | -m <nbt>] [--plain] [--little]
           [--compact] [--pretty] [--unpack] [--json]
           [--path <path>] [--find <path>]
           <file>

Perform operations on nbt files.

positional arguments:
  <file>         the target file

optional arguments:
  -h, --help     show this help message and exit
  -r             read nbt data from a file
  -s             read snbt from a file
  -w <nbt>       write nbt to a file
  -m <nbt>       merge nbt into a file
  --plain        don't use gzip compression
  --little       use little-endian format
  --compact      output compact snbt
  --pretty       output indented snbt
  --unpack       output interpreted nbt
  --json         output nbt as json
  --path <path>  output all the matching tags
  --find <path>  recursively find the first matching tag
```

### Read nbt data

You can read nbt files by using the `-r` option. This will print the
literal notation of the binary nbt data.

```bash
$ nbt -r my_file.nbt
{foo: [1, 2, 3], bar: "Hello, world!"}
```

You can use the following command if you want to save the output into a
file.

```bash
$ nbt -r my_file.nbt > my_file.snbt
```

Using the `--compact` argument will remove all the extra whitespace from the output.

```bash
$ nbt -r my_file.nbt --compact
{foo:[1,2,3],bar:"Hello, world!"}
```

You can use the `--pretty` argument if you want the command to output indented snbt.

```bash
$ nbt -r my_file.nbt --pretty
{
    foo: [1, 2, 3],
    bar: "Hello, world!"
}
```

The output can be converted to json with the `--json` flag.

```bash
$ nbt -r my_file.nbt --json
{"foo": [1, 2, 3], "bar": "Hello, world!"}
```

The `--path` option lets you output tags that match a given path.

```bash
$ nbt -r my_file.nbt --path "bar"
"Hello, world!"
$ nbt -r my_file.nbt --path "foo[]"
1
2
3
```

You can combine this with the `--unpack` flag to print out the unpacked python objects.

```bash
$ nbt -r my_file.nbt --path "bar" --unpack
Hello, world!
```

If you don't know exactly how to access the data you're interested in you can use the `--find` option to recursively try to match a given path.

```bash
$ nbt -r my_file.nbt --find "[1]"
2
```

You can also perform all these operations on snbt by using the `-s` option instead of the `-r` option.

```bash
$ nbt -s foo.snbt --path bar
"Hello, world!"
```

### Write nbt data

You can write nbt data to a file by using the `-w` option. This will
convert the literal nbt notation to its binary form and save it in the
specified file.

```bash
$ nbt -w '{foo:[1,2,3],bar:{hello:[B;1b,1b,0b,1b]}}' my_file.nbt
```

The file will be created if it doesn't already exist.

You can combine the `-w` flag with other flags to read, filter and write nbt data.

```bash
$ nbt -r my_file.nbt --path "bar" -w bar.nbt
```

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
{foo: [1, 2, 3], bar: {hello: [B; 1B, 1B, 0B, 1B], "new key": 56.0f}}
```

Here, the compound values that aren't present in the input literal are
left untouched. Using the `-w` option instead of `-m` would
overwrite the whole file.

You can combine the `-m` flag with other flags to read, filter and merge nbt data.

```bash
$ nbt -s foo.snbt -m my_file.nbt
```

### Compression and byte order

By default, the CLI will assume that you're working with gzipped nbt
files. If you want to read, write or merge uncompressed nbt files, you
can use the `--plain` option. Similarly, the default byte order is
big-endian so you'll need to use the `--little` option to perform
operations on little-endian files.

**Reading**

```bash
$ nbt -r my_file.nbt --plain --little
{name: "Reading an uncompressed little-endian file"}
```

**Writing**

```bash
$ nbt -w '{name:"Writing in an uncompressed little-endian file"}' my_file.nbt --plain --little
```

**Merging**

```bash
$ nbt -m '{name:"Merging in an uncompressed little-endian file"}' my_file.nbt --plain --little
```

## Contributing

Contributions are welcome. This project uses [`poetry`](https://poetry.eustace.io/) so you'll need to install it first if you want to be able to work with the project locally.

```sh
$ curl -sSL https://raw.githubusercontent.com/sdispater/poetry/main/get-poetry.py | python
```

You should now be able to install the required dependencies.

```sh
$ poetry install
```

You can run the tests with `poetry run pytest`.

```sh
$ poetry run pytest
```

---

License - [MIT](https://github.com/vberlier/nbtlib/blob/main/LICENSE)
