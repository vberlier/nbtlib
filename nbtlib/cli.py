from argparse import ArgumentParser, ArgumentTypeError

from nbtlib import nbt, parse_nbt, serialize_tag, InvalidLiteral
from nbtlib.tag import Compound


# Validation helper

def compound_literal(literal):
    try:
        nbt_data = parse_nbt(literal)
    except InvalidLiteral as exc:
        raise ArgumentTypeError(exc) from exc
    else:
        if not isinstance(nbt_data, Compound):
            raise ArgumentTypeError('The root nbt tag must be a compound tag')
        return nbt_data


# Create the argument parser

parser = ArgumentParser(prog='nbt',
                        description='Perform basic operations on nbt files.')

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-r', action='store_true',
                   help='read nbt data from a file')
group.add_argument('-w', metavar='<nbt>', type=compound_literal,
                   help='write nbt to a file')
group.add_argument('-m', metavar='<nbt>', type=compound_literal,
                   help='merge nbt into an nbt file')

parser.add_argument('--plain', action='store_true',
                    help='don\'t use gzip compression')
parser.add_argument('--little', action='store_true',
                    help='use little-endian format')

parser.add_argument('--compact', action='store_true',
                    help='output compact snbt')
parser.add_argument('--pretty', action='store_true',
                    help='output indented snbt')

parser.add_argument('file', metavar='<file>',
                    help='the target file')


# Define command-line interface

def main():
    args = parser.parse_args()
    gzipped, byteorder = not args.plain, 'little' if args.little else 'big'
    try:
        if args.r:
            read(args.file, gzipped, byteorder, args.compact, args.pretty)
        elif args.w:
            write(args.w, args.file, gzipped, byteorder)
        elif args.m:
            merge(args.m, args.file, gzipped, byteorder)
    except IOError as exc:
        parser.exit(1, str(exc) + '\n')


def read(filename, gzipped, byteorder, compact, pretty):
    nbt_file = nbt.load(filename, gzipped=gzipped, byteorder=byteorder)
    print(serialize_tag(nbt_file, indent=4 if pretty else None, compact=compact))


def write(nbt_data, filename, gzipped, byteorder):
    nbt.File(nbt_data).save(filename, gzipped=gzipped, byteorder=byteorder)


def merge(nbt_data, filename, gzipped, byteorder):
    nbt_file = nbt.load(filename, gzipped=gzipped, byteorder=byteorder)
    nbt_file.merge(nbt_data)
    nbt_file.save()
