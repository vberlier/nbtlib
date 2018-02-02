
from argparse import ArgumentParser, ArgumentTypeError

from nbtlib import nbt, parse_nbt, InvalidLiteral
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
parser.add_argument('file', metavar='<file>',
                    help='the target file')


# Define command-line interface

def main():
    args = parser.parse_args()
    try:
        if args.r:
            read(args.file, not args.plain)
        elif args.w:
            write(args.w, args.file, not args.plain)
        elif args.m:
            merge(args.m, args.file, not args.plain)
    except IOError as exc:
        parser.exit(1, str(exc) + '\n')


def read(filename, compressed):
    print(nbt.load(filename, gzipped=compressed))


def write(nbt_data, filename, compressed):
    nbt.File(nbt_data).save(filename, gzipped=compressed)


def merge(nbt_data, filename, compressed):
    nbt_file = nbt.load(filename, gzipped=compressed)
    nbt_file.merge(nbt_data)
    nbt_file.save()
