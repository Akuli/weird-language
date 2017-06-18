import argparse
import shlex
import subprocess
import sys
import tempfile

from weirdc import tokenizer, ast, c_output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', type=argparse.FileType('r'),
        help="the source code")
    parser.add_argument(
        '-o', '--outfile', default='a.out',
        help="name of the output file")
    parser.add_argument(
        '--cc', metavar='COMMAND', default='gcc {cfile} -o {outfile}',
        help=("c compiler command and options with {cfile} and {outfile} "
              "substituted, defaults to '%(default)s'"))
    args = parser.parse_args()

    with args.infile as file:
        code = file.read()

    print("Generating C code...")
    tokens = tokenizer.tokenize(code)
    node_list = ast.parse(tokens)
    c_code = c_output.PRELOAD + ''.join(map(c_output.unparse, node_list))

    print("Compiling...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c') as cfile:
        cfile.write(c_code)
        cfile.flush()

        compile_command = [
            part.format(cfile=cfile.name, outfile=args.outfile)
            for part in shlex.split(args.cc)]
        print(' '.join(map(shlex.quote, compile_command)))
        statuscode = subprocess.call(compile_command)

    if statuscode == 0:
        print("Compiling succeeded.")
    else:
        print("C compiler exited with status", statuscode, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
