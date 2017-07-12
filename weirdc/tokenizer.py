import collections
import re

import weirdc


# TODO:
#    - write tests
#    - allow escaping quotes and other stuff in strings

# https://docs.python.org/3/library/re.html#writing-a-tokenizer
TOKEN_SPEC = [
    ('INTEGER', r'\d+'),                   # 123
    ('OP', r"[=(){}\[\],.]"),              # = ( ) { } [ ] , .
    ('NAME', r'[^\W\d]\w*'),               # message123
    ('STRING', r'"[^"\n]*"'),              # "hello world"
    ('NEWLINE', r'\n'),                    # a \n character
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
        >>> Token('OP', ')', Location(1, 2, 3)).startswith('wolololo')
        False
        """
        if len(other) > len(self):
            return False
        return all(a == b for a, b in zip(self, other))


def tokenize(code, trailing_newline=True):
    r"""Turn a string into an iterator of Token objects.

    If trailing_newline is True, a NEWLINE token will be added at the
    end if the code doesn't end with a \n.
    """
    lineno = 1
    line_start = 0

    # expanding tabs here means that they will also be expanded in
    # string literals, but it makes some things easier, see
    # implementation of CompileError
    for match in TOKEN_REGEX.finditer(code.expandtabs(4)):
        kind = match.lastgroup
        value = match.group(kind)

        # change this if you add multiline strings or something
        if kind == 'NEWLINE':
            # this needs to be handled specially because -1 is not a
            # valid line start, but the location's end can extend past
            # the real end of the line and will extend by 3 characters
            start = match.start() - line_start
            yield Token('NEWLINE', '\n',
                        weirdc.Location(start, start+3, lineno))

            lineno += 1
            line_start = match.end()
            continue

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
        location = weirdc.Location(start, end, lineno)

        if kind == 'ERROR':
            raise weirdc.CompileError("I don't know what this is", location)
        yield Token(kind, value, location)

    # i like how i get to (ab)use loop variables that aren't local to
    # the loop... feels good
    if kind != 'NEWLINE' and trailing_newline:
        yield Token('NEWLINE', '\n', weirdc.Location(0, 3, lineno+1))
