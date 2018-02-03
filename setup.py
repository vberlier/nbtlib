
from setuptools import setup, find_packages


setup(
    name='nbtlib',
    version='0.1.13',
    description='A python package to read and edit nbt data',
    long_description=open('README.rst').read(),
    url='https://github.com/vberlier/nbtlib',
    author='Valentin Berlier',
    author_email='berlier.v@mail.com',
    platforms=['any'],
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='nbt schema minecraft package library parser reader module',
    packages=find_packages(),
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'nbt=nbtlib.cli:main',
        ],
    }
)
