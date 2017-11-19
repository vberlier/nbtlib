nbtlib
======

|Build Status|

A python library to read and edit `nbt data <http://wiki.vg/NBT>`__.
Also provides an api to define compound tag schemas in order to save
some typing with recurring tag hierarchies. Requires python 3.6.

Installation
------------

The package can be installed with ``pip``.

.. code::

    $ pip install nbtlib

Basic usage
-----------

The following examples will give you a very basic overview of what you
can do. For more advanced examples, check out the
`Usage <https://github.com/vberlier/nbtlib/blob/master/docs/Usage.ipynb>`__
notebook in the docs folder.

Reading files
~~~~~~~~~~~~~

.. code:: py

    from nbtlib import nbt

    nbt_file = nbt.load('bigtest.nbt')
    assert nbt_file.root['intTest'] == 2147483647

Editing files
~~~~~~~~~~~~~

.. code:: py

    from nbtlib import nbt
    from nbtlib.tag import *

    with nbt.load('demo.nbt') as demo:
        demo.root['counter'] = Int(demo.root['counter'] + 1)

Using schemas
~~~~~~~~~~~~~

.. code:: py

    from nbtlib import schema
    from nbtlib.tag import *

    MySchema = schema('MySchema', {
        'foo': String,
        'bar': Short
    })

    my_object = MySchema({'foo': 'hello world', 'bar': 21})
    assert isinstance(my_object['foo'], String)

Contributing
------------

Contributions are welcome. Unit tests are built with ``pytest``. You can
run the test suite with:

.. code::

    $ python -m pytest tests

----

License: `MIT <https://github.com/vberlier/nbtlib/blob/master/LICENSE>`__

.. |Build Status| image:: https://travis-ci.org/vberlier/nbtlib.svg?branch=master
   :target: https://travis-ci.org/vberlier/nbtlib
