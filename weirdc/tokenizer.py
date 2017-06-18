import collections
import re

# TODO:
#   - names must not start with a number
#   - strings need to allow escaping quotes

# https://docs.python.org/3/library/re.html#writing-a-tokenizer
# MULTILINE_IGNORE is for counting newline characters
TOKEN_SPEC = [
    ('INTEGER', r'\d+'),                   # 123
    ('OP', r"[(){}\[\];,=]|'s|->"),        # ( ) { } [ ] ; , = 's ->
    ('NAME', r'\w+'),                      # message
    ('STRING', r'"[^"\n]*"'),              # "hello world"
    ('IGNORE', r'\s+|//[^\n]*|/\*.*\*/'),  # whitespace and comments
    ('ERROR', r'.'),                       # anything else
]
TOKEN_REGEX = re.compile(
    '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC), re.DOTALL)


class Token(collections.namedtuple('Token', 'start end kind value')):

    # don't allow setting random attributes
    __slots__ = ()

    @property
    def info(self):
        """A two-tuple of (kind, value).

        In other words, this is everything except information about
        where in code the token comes from.
        """
        return (self.kind, self.value)


# TODO: doctest examples!
def tokenize(code):
    """Turn a string into an iterator of Token objects.
    """
    lineno = 1
    line_start = 0

    for match in TOKEN_REGEX.finditer(code):
        kind = match.lastgroup
        value = match.group(kind)

        if kind == 'IGNORE':
            if '\n' in value:
                lineno += value.count('\n')
                # match.start() is where the start of the ignored value
                # is in the code, and value.rindex('\n')+1 is where the
                # last newline is in the value so line_start will be end
                # of that last newline, or beginning of the next line
                line_start = match.start() + value.rindex('\n') + 1

        elif kind == 'ERROR':
            raise ValueError("invalid syntax: " + match.group())

        else:
            startcol = match.start() - line_start
            endcol = match.end() - line_start
            yield Token((lineno, startcol), (lineno, endcol), kind, value)


if __name__ == '__main__':
    code = '''\
    /*print("hello world"'s capitalized);
      wololo
      */
    int a;
    a = 1;
    int b = 2;
    '''
    for token in tokenize(code):
        print(token)
