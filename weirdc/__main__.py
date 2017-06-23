#!/usr/bin/env python3
import argparse
import shlex
import subprocess
import sys
import tempfile
import os
import glob

from weirdc import tokenizer, ast, c_output

PROMPT = ("{} already exists. "
          "Do you want to overwrite it? [Y/n] ")


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
        '--cc', metavar='COMMAND', default='gcc {cfile} -Iobjects -o {outfile}',
        help=("c compiler command and options with {cfile} and {outfile} "
              "substituted, defaults to '%(default)s'"))
    args = parser.parse_args()

    with args.infile as file:
        code = file.read()

    print("Generating C code...")
    tokens = tokenizer.tokenize(code)
    node_list = ast.parse(tokens)
    c_code = c_output.PRELOAD + ''.join(map(c_output.unparse, node_list))

    if args.no_compile:
        # If we don't call basename, we get all of the path too. this way we
        # save to the current directory.
        basename = os.path.basename(os.path.splitext(args.infile.name)[0])
        filename = basename + ".c"

        if os.path.exists(filename):
            confirmation = input(PROMPT.format(filename))
            if confirmation and confirmation.lower() != "y":
                print("Okay, exiting.")
                sys.exit(1)

        print("Saving C code to", filename)
        with open(filename, "w") as file:
            file.write(c_code)
    else:
        print("Compiling...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c') as cfile:
            cfile.write(c_code)
            cfile.flush()

            compile_command = []

            for part in shlex.split(args.cc):
                if "{cfile}" in part:
                    # We want to add the object C files to the compile command
                    # with the regular C file. This does not really matter,
                    # but is the easiest way to do this.
                    # TODO: However, this feels very hack-ish and I'm sure
                    # there's a better and more beautiful way.
                    compile_command.extend(glob.glob("objects/*.c"))
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
