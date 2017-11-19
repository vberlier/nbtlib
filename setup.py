
from setuptools import setup, find_packages
from codecs import open
from os import path


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='nbtlib',
    version='0.1.0',
    description='A python package to read and edit nbt data',
    long_description=long_description,
    url='https://github.com/vberlier/nbtlib',
    author='Valentin Berlier',
    author_email='berlier.v@mail.com',
    platforms=['any'],
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='nbt schema minecraft package library parser reader module',
    python_requires='>=3.6',
)
