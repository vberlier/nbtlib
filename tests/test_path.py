import pytest

from nbtlib import Path, parse_nbt, load


path_strings_to_keys = [
    ('', ()),
    ('hello', ('hello',)),
    ('hello.world', ('hello', 'world')),
    ('with.trailing.dot.', ('with', 'trailing', 'dot')),
    ('using."quoted.keys"', ('using', 'quoted.keys')),
    ('"escape \\"quotes\\""."in.quoted".key', ('escape "quotes"', 'in.quoted', 'key')),
    ('...with..redundant..dots', ('with', 'redundant', 'dots')),
]


@pytest.mark.parametrize('path_string, keys', path_strings_to_keys)
def test_path_with_named_keys(path_string, keys):
    assert tuple(p.key for p in Path(path_string)) == keys


@pytest.fixture(scope='module')
def bigtest():
    return load('tests/nbt_files/bigtest.nbt')


@pytest.fixture
def biglist():
    return parse_nbt("""[
        [{a: [{value: 0}, {value: 1, thing: 42}], flag: 1}],
        [{spam: {egg: [{foo: 0}, {foo: 2}], checked: 1b}}, {spam: {egg: [{foo: 7}]}}],
        [{a: [{value: 1}, {value: 2, thing: 42}]}, {a: [], flag: 1}],
        [{a: [{value: 3, thing: 42}], flag: 1}],
        [{spam: {egg: [{foo: 1}], checked: 1b}}],
        [{spam: {egg: [{foo: 2}]}}, {spam: {egg: [{foo: 9}, {foo: 5}], checked: 1b}}]
    ]""")


bigtest_path_to_items = [
    ('Level.longTest', [9223372036854775807]),
    ('Level."nested compound test".egg.name', ["Eggbert"]),
    ('Level."nested compound test".ham.value', [0.75]),
    ('Level."byteArrayTest (the first 1000 values of (n*n*255+n*7)%100, starting with n=0 (0, 62, 34, 16, 8, ...))"[1]', [62]),
    ('Level."listTest (long)"', [[11, 12, 13, 14, 15]]),
    ('Level."listTest (long)"[3]', [14]),
    ('Level."listTest (long)"[]', [11, 12, 13, 14, 15]),
    ('{Level: {byteTest: 127b}}.Level."listTest (long)"[1]', [12]),
    ('{Level: {byteTest: 127}}.Level."listTest (long)"[1]', []),
    ('{random: "value"}.Level."listTest (long)"[1]', []),
    ('{}.Level."listTest (long)"[1]', [12]),
    ('Level{intTest: 2147483647}."listTest (long)"[1]', [12]),
    ('Level{"nested compound test": {egg: {value: 0.5f}}}."listTest (long)"[1]', [12]),
    ('Level."listTest (compound)"', [[{'created-on': 1264099775885, 'name': 'Compound tag #0'}, {'created-on': 1264099775885, 'name': 'Compound tag #1'}]]),
    ('Level."listTest (compound)"[]', [{'created-on': 1264099775885, 'name': 'Compound tag #0'}, {'created-on': 1264099775885, 'name': 'Compound tag #1'}]),
    ('Level."listTest (compound)"[1]', [{'created-on': 1264099775885, 'name': 'Compound tag #1'}]),
    ('Level."listTest (compound)"[-1]', [{'created-on': 1264099775885, 'name': 'Compound tag #1'}]),
    ('Level."listTest (compound)"[-2]', [{'created-on': 1264099775885, 'name': 'Compound tag #0'}]),
    ('Level."listTest (compound)"[-3]', []),
    ('Level."listTest (compound)"[{name: "Compound tag #0"}]', [{'created-on': 1264099775885, 'name': 'Compound tag #0'}]),
    ('Level."listTest (compound)"[{name: "Compound tag #3"}]', []),
    ('Level."listTest (compound)"[{random: "data"}].property', []),
    ('Level."listTest (compound)"[].name', ['Compound tag #0', 'Compound tag #1']),
    ('Level."listTest (compound)"[]."created-on"', [1264099775885, 1264099775885]),
]


biglist_path_to_items = [
    ('[][].a[].value', [0, 1, 1, 2, 3]),
    ('[][{flag: 1}].a[].value', [0, 1, 3]),
    ('[][].a[{thing: 42}].value', [1, 2, 3]),
    ('[][{a: []}].flag', [1]),
    ('[][{a: [{}, {}]}].flag', [1]),
    ('[][{a: [{}, {}]}].a[].value', [0, 1, 1, 2]),
    ('[][{a: [{}]}].a[].value', [3]),
    ('[1][{a: [{}]}].a[].value', []),
]


@pytest.mark.parametrize('path, items', bigtest_path_to_items)
def test_path_get_bigtest(bigtest, path, items):
    assert bigtest.get_all(Path(path)) == items


@pytest.mark.parametrize('path, items', biglist_path_to_items)
def test_path_get_biglist(biglist, path, items):
    assert biglist.get_all(Path(path)) == items


path_set_and_get = [
    ('[][].a[].value', '42', '[][].a[].value', [42, 42, 42, 42, 42]),
    ('[][{flag: 1}].a[].value', '42', '[][].a[].value', [42, 42, 1, 2, 42]),
    ('[][].a[{thing: 42}].value', '42', '[][].a[].value', [0, 42, 1, 42, 42]),
    ('[][].a[{thing: 42}]', '{value: 42}', '[][].a[].value', [0, 42, 1, 42, 42]),
    ('[][].a[]', '{value: 42}', '[][].a[].value', [42, 42, 42, 42, 42]),
    ('[][].a[0]', '{value: 42}', '[][].a[].value', [42, 1, 42, 2, 42]),
    ('[][].a[1]', '{value: 42}', '[][].a[].value', [0, 42, 1, 42, 3]),
    ('[][].a[2]', '{value: 42}', '[][].a[].value', [0, 1, 1, 2, 3]),
    ('[0][].a[]', '{value: 42}', '[][].a[].value', [42, 42, 1, 2, 3]),
    ('[][0].a[]', '{value: 42}', '[][].a[].value', [42, 42, 42, 42, 42]),
    ('[][].spam{checked: 1b}.egg[{foo: 2}]', '{foo: 42}', '[][].spam.egg[].foo', [0, 42, 7, 1, 2, 9, 5]),
    ('[][].spam{checked: 1b}.egg[]', '{foo: 42}', '[][].spam.egg[].foo', [42, 42, 7, 42, 2, 42, 42]),
    ('[][].spam{checked: 1b}.egg[0]', '{foo: 42}', '[][].spam.egg[].foo', [42, 2, 7, 42, 2, 42, 5]),
    ('[][].spam{checked: 1b}', '{egg: []}', '[][].spam.egg[].foo', [7, 2]),
]


@pytest.mark.parametrize('path, value, select, results', path_set_and_get)
def test_path_set(biglist, path, value, select, results):
    biglist[Path(path)] = parse_nbt(value)
    assert biglist.get_all(Path(select)) == results


path_del_and_get = [
    ('[][].spam{checked: 1b}', '[][].spam.egg[].foo', [7, 2]),
    ('[][1]', '[][].spam.egg[].foo', [0, 2, 1, 2]),
    ('[][{spam: {checked: 1b}}]', '[][].spam.egg[].foo', [7, 2]),
    ('[1]', '[][].spam.egg[].foo', [1, 2, 9, 5]),
    ('[][].spam.egg[0].foo', '[][].spam.egg[].foo', [2, 5]),
]


@pytest.mark.parametrize('path, select, results', path_del_and_get)
def test_path_set(biglist, path, select, results):
    del biglist[Path(path)]
    assert biglist.get_all(Path(select)) == results


normalized_path_strings = [
    'foo',
    'foo.bar',
    'foo.bar[0]',
    'foo.bar[0]."A [crazy name]!"',
    'foo.bar[0]."A [crazy name]!".baz',
    'foo.bar[]',
    'foo.bar[].baz',
    'foo.bar[{baz: 5b}]',
    '{}',
    '{}.foo',
    '{foo: 4.0f}',
    'foo{bar: "baz"}',
    'foo{bar: "baz"}.bar',
    'a[-3].c{a: [1b, 2b]}.d[].e{a: {e: 5b}}[8]',
    'a[-3].c{a: [1b, 2b]}.d[].e{a: {e: 5b}}[8].d',
    'a[-3].c{a: [1b, 2b]}.d[].e{a: {e: 5b}}[8][5]',
    'a[-3].c{a: [1b, 2b]}.d[].e{a: {e: 5b}}[].d{a: {m: 4.0f}}',
    'Items[].a[]',
    '[{}]',
] + [
    path for entries in [bigtest_path_to_items, biglist_path_to_items]
    for path, _ in entries
] + [
    path for path, _, _, _ in path_set_and_get
] + [
    path for _, _, path, _ in path_set_and_get
] + [
    path for path, _, _ in path_del_and_get
] + [
    path for _, path, _ in path_del_and_get
]


@pytest.mark.parametrize('path_string', normalized_path_strings)
def test_normalized_path_strings(path_string):
    assert str(Path(path_string)) == path_string


equivalent_paths = [
    [Path(p) for p in paths]
    for paths in [
        ['a.b.c', 'a b c', 'a. b. c', '"a""b""c"', ' "a"  ..  "b" .c  ', 'a\nb\nc'],
        ['[]{a: 1}', '[{a: 1}]', '[{a: 1}]{}', '[{a: 42}]{a: 1}', '[{}]{a: 42}{}{a: 1}'],
        ['{a: {foo: "bar"}, value: 0}', '{a: {foo: "bar"}, value: 0}{a: {foo: "bar"}}'],
        ['{a: {b: {c: 1}, foo: 42}}', '{a: {b: {c: 1}}}{a: {foo: 42}}', '{a: {b: {c: "thing"}, foo: 42}}{a: {b: {c: 1}}}'],
    ]
]


equivalent_path_pairs = [
    (path1, path2)
    for paths in equivalent_paths
    for path1, path2 in zip(paths, paths[1:])
]


@pytest.mark.parametrize('path1, path2', equivalent_path_pairs)
def test_equivalent_paths(path1, path2):
    assert path1 == path2
