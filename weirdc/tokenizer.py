import collections
import re

import weirdc


# TODO:
#    - write tests
#    - allow escaping quotes and other stuff in strings

# https://docs.python.org/3/library/re.html#writing-a-tokenizer
TOKEN_SPEC = [
    ('INTEGER', r'\d+'),                   # 123
    ('OP', r"==|[=(){}\[\];,=]"),          # == = ( ) { } [ ] ; ,
    ('NAME', r'[^\W\d]\w*'),               # message123
    ('STRING', r'"[^"\n]*"'),              # "hello world"
    ('IGNORE', r'\s+|//[^\n]*|/\*.*\*/'),  # whitespace and comments
    ('ERROR', r'.'),                       # anything else
]
TOKEN_REGEX = re.compile(
    '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC), re.DOTALL)


class Token(collections.namedtuple('Token', 'kind value location')):
    """A namedtuple that :func:`.tokenize` yields."""

    # don't allow setting random attributes
    __slots__ = ()

    # why don't tuples have this :(
    def startswith(self, other):
        """Like :meth:`str.startswith`, but for tuples.

        >>> from weirdc import Location
        >>> Token('OP', ')', Location(1, 2, 3)).startswith(['OP', ')'])
        True
        """
        if len(self) < len(other):
            return False
        return all(a == b for a, b in zip(self, other))


def tokenize(code):
    """Turn a string into an iterator of Token objects."""
    lineno = 1
    line_start = 0

    for match in TOKEN_REGEX.finditer(code):
        kind = match.lastgroup
        value = match.group(kind)

        # change this if you add multiline strings or something
        if kind == 'IGNORE':
            if '\n' in value:
                lineno += value.count('\n')
                # match.start() is where the start of the ignored value
                # is in the code, and value.rindex('\n')+1 is where the
                # last newline is in the value so line_start will be end
                # of that last newline, or beginning of the next line
                line_start = match.start() + value.rindex('\n') + 1
            continue

        start = match.start() - line_start
        end = match.end() - line_start
        location = weirdc.Location(lineno, start, end)

        if kind == 'ERROR':
            raise weirdc.CompileError("I don't know what this is", location)
        yield Token(kind, value, location)


if __name__ == '__main__':
    while True:
        for token in tokenize(input('> ')):
            print(token)
