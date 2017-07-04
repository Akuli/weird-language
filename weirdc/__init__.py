import collections


class Location(collections.namedtuple('Location', 'start end lineno')):
    r"""Information about where a token or AST node comes from.

    The *start* and *end* should be integers that represent column
    counts with tabs expanded to 4 spaces. For example, to highlight
    ``hello`` in ``(tab)hello there``, use ``Location(4, 9, lineno)``.

    If ``end`` is None, it means the end of the line. Note that None
    behaves nicely with slices::

        >>> "hello world"[3:None]
        'lo world'

    *lineno* is the line number as an integer. Note that the first line
    is 1, not 0. It defaults to 1 mostly for convenience with tests.
    """

    # don't allow random attributes
    __slots__ = ()

    def __new__(cls, start, end, lineno=1):
        # Python 3.5 and older or something requires this explicit super
        # argument thing
        return super(Location, cls).__new__(cls, start, end, lineno)

    @classmethod
    def between(cls, start, end):
        """Create a Location that represents the area between two locations.

        For convenience, *start* and *end* can be not only Location
        objects, but any objects with a ``Location`` attribute that is a
        Location object.
        """
        if not isinstance(start, Location):
            start = start.location
        if not isinstance(end, Location):
            end = end.location

        if start.lineno < end.lineno:
            # extend all the way to end of the start line
            return cls(start.start, None, start.lineno)

        assert start.lineno == end.lineno, "end is on a line before start"
        return cls(start.start, end.end, start.lineno)


class CompileError(Exception):
    """This is raised and displayed to the user during compilation.

    *message* should be a human-readable string like
    ``"no variable named 'lol'"``.

    The *location* should be a :class:`.Location` object that represents
    the line and column numbers where the error comes from. It can also
    be None, but it should be None **only** when the error doesn't come
    from a specific location and there's something wrong with the whole
    file, e.g., missing main function.
    """

    # this throws away the end's lineno, but usually this is good enough
    def __init__(self, message, location=None):
        # CompileError(location, message) must be easy to debug
        assert location is None or isinstance(location, Location)
        self.message = message
        self.location = location

    # this isn't __str__ because this way the arguments don't need to be
    # passed to __init__()
    def show(self, filename, line=None, kind='error'):
        r"""Get a string suitable for displaying to the user.

        *filename* will be displayed in the error message. Later it
        could be something like '<console>' or '<stdin>' if the code
        doesn't come from a file.

        *line* should be the line of code where this error occurred as a
        string with tabs expanded to 4 spaces. Trailing whitespace is
        ignored. It must be given if the *location* attribute is set,
        and it must be omitted if *location* is None.

        The error message will start with *kind*; usually it should be
        ``'error'`` or ``'warning'``.

        >>> code = "    bla bla bla"
        >>> error = CompileError("this is the 2nd bla", Location(8, 11, 123))
        >>> print(error.show('test', code, 'warning'))
        warning in file 'test', line 123: this is the 2nd bla
          bla bla bla
              ^^^
        >>> error = CompileError("missing semicolon", Location(15, 18, 123))
        >>> print(error.show('test', code))
        error in file 'test', line 123: missing semicolon
          bla bla bla
                     ^^^
        >>> print(CompileError("missing main() function").show('test'))
        error in file 'test': missing main() function
        >>>
        """
        if self.location is None:
            assert line is None
            return "%s in file '%s': %s" % (kind, filename, self.message)

        assert line is not None
        leading_spaces = len(line) - len(line.lstrip())
        line = line.strip()

        start = self.location.start - leading_spaces
        if self.location.end is None:
            end = len(line)
        else:
            end = self.location.end - leading_spaces

        # this is indented weirdly because pep8 line length
        return '\n'.join([
            "%s in file '%s', line %d: %s"
                % (kind, filename, self.location.lineno, self.message),
            '  ' + line,
            '  ' + ' '*start + '^'*(end - start),
        ])
