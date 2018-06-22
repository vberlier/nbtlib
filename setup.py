from setuptools import setup, find_packages


with open('README.md') as readme:
    long_description = readme.read()


setup(
    name='nbtlib',
    version='1.0.3',
    license='MIT',
    description='A python package to read and edit nbt data',
    long_description=long_description,
    long_description_content_type='text/markdown',

    author='Valentin Berlier',
    author_email='berlier.v@mail.com',
    url='https://github.com/vberlier/nbtlib',

    platforms=['any'],
    python_requires='>=3.6',
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

    entry_points={
        'console_scripts': [
            'nbt=nbtlib.cli:main',
        ],
    }
)
