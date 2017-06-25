#!/usr/bin/env python3
import argparse
import shlex
import subprocess
import sys
import tempfile
import os
import glob

from weirdc import tokenizer, ast, c_output, scoping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', type=argparse.FileType('r'),
        help="the source code")
    parser.add_argument(
        '-o', '--outfile', default='a.out',
        help="name of the output file")
    parser.add_argument(
        "--no-compile", action="store_true",
        help="If specified, saves the C code to a file instead of compiling.")
    parser.add_argument(
        '--cc', metavar='COMMAND', default='gcc {cfile} -std=c99 -Iobjects -o {outfile}',
        help=("c compiler command and options with {cfile} and {outfile} "
              "substituted, defaults to '%(default)s'"))
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help="produce more output")
    args = parser.parse_args()

    def debug(msg):
        if args.verbose:
            print(msg)

    debug("Reading '%s'..." % args.infile.name)
    with args.infile as file:
        code = file.read()

    debug("Generating C code...")
    tokens = tokenizer.tokenize(code)
    node_list = scoping.scope_ast(ast.parse(tokens))
    c_code = c_output.make_c_code(node_list)

    if args.no_compile:
        debug("Saving C code to '%s'..." % args.outfile)
        with open(args.outfile, 'w') as file:
            file.write(c_code)
        print("Generating the C code succeeded.")
    else:
        debug("Compiling...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c') as cfile:
            cfile.write(c_code)
            cfile.flush()

            compile_command = []

            for part in shlex.split(args.cc):
                if "{cfile}" in part:
                    # TODO: is there a nicer way to do this?
                    compile_command.extend(glob.glob("objects/*.o"))
                part = part.format(cfile=cfile.name, outfile=args.outfile)
                compile_command.append(part)
            print(' '.join(map(shlex.quote, compile_command)))
            statuscode = subprocess.call(compile_command)

        if statuscode == 0:
            print("Compiling succeeded.")
        else:
            print("C compiler exited with status", statuscode, file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
