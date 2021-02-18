from argparse import ArgumentParser, ArgumentTypeError
from json import dumps as json_dumps
from pprint import pprint

from nbtlib import InvalidLiteral, Path, nbt, parse_nbt, serialize_tag
from nbtlib.tag import Compound, find_tag

# Validation helper


def nbt_data(literal):
    try:
        nbt_data = parse_nbt(literal)
    except InvalidLiteral as exc:
        raise ArgumentTypeError(exc) from exc
    else:
        if not isinstance(nbt_data, Compound):
            raise ArgumentTypeError("the root nbt tag must be a compound tag")
        return nbt_data


# Create the argument parser

parser = ArgumentParser(prog="nbt", description="Perform operations on nbt files.")

inputs = parser.add_mutually_exclusive_group()
inputs.add_argument("-r", action="store_true", help="read nbt data from a file")
inputs.add_argument("-s", action="store_true", help="read snbt from a file")

outputs = parser.add_mutually_exclusive_group()
outputs.add_argument("-w", metavar="<nbt>", help="write nbt to a file")
outputs.add_argument("-m", metavar="<nbt>", help="merge nbt into a file")

parser.add_argument("--plain", action="store_true", help="don't use gzip compression")
parser.add_argument("--little", action="store_true", help="use little-endian format")

parser.add_argument("--compact", action="store_true", help="output compact snbt")
parser.add_argument("--pretty", action="store_true", help="output indented snbt")
parser.add_argument("--unpack", action="store_true", help="output interpreted nbt")
parser.add_argument("--json", action="store_true", help="output nbt as json")
parser.add_argument("--path", metavar="<path>", help="output all the matching tags")
parser.add_argument(
    "--find", metavar="<path>", help="recursively find the first matching tag"
)

parser.add_argument("file", metavar="<file>", help="the target file")


# Define command-line interface


def main():
    args = parser.parse_args()
    gzipped, byteorder = not args.plain, "little" if args.little else "big"
    try:
        if args.r or args.s:
            for tag in read(
                args.file, gzipped, byteorder, args.s, args.path, args.find
            ):
                if args.w:
                    write(tag, args.w, gzipped, byteorder)
                elif args.m:
                    merge(tag, args.m, gzipped, byteorder)
                else:
                    display(tag, args.compact, args.pretty, args.unpack, args.json)
        elif args.w:
            write(nbt_data(args.w), args.file, gzipped, byteorder)
        elif args.m:
            merge(nbt_data(args.m), args.file, gzipped, byteorder)
        else:
            parser.error("one of the following arguments is required: -r -s -w -m")
    except (ArgumentTypeError, IOError) as exc:
        parser.error(f"{exc}")


def read(filename, gzipped, byteorder, snbt, path, find):
    if snbt:
        with open(filename) as f:
            nbt_file = parse_nbt(f.read())
    else:
        nbt_file = nbt.load(filename, gzipped=gzipped, byteorder=byteorder)

    tags = nbt_file.get_all(Path(path)) if path else [nbt_file]

    for tag in tags:
        if find:
            tag = tag.find(Path(find))
        if tag is not None:
            yield tag


def display(tag, compact, pretty, unpack, json):
    if unpack:
        if pretty:
            pprint(tag.unpack())
        else:
            print(tag.unpack())
    elif json:
        print(json_dumps(tag.unpack(json=True), indent=4 if pretty else None))
    else:
        print(serialize_tag(tag, indent=4 if pretty else None, compact=compact))


def write(nbt_data, filename, gzipped, byteorder):
    nbt.File(nbt_data).save(filename, gzipped=gzipped, byteorder=byteorder)


def merge(nbt_data, filename, gzipped, byteorder):
    nbt_file = nbt.load(filename, gzipped=gzipped, byteorder=byteorder)
    nbt_file.merge(nbt_data)
    nbt_file.save()
