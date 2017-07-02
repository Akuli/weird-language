import collections


class Location(collections.namedtuple('Location', 'lineno start end')):
    r"""Information about where a token or AST node comes from.

    *lineno* is the line number as an integer. Note that the first line
    is 1, not 0.

    The *start* and *end* should be integers that represent column
    counts, where the size of each tab is 1. For example, to highlight
    ``hello`` in ``(tab)hello there``, use ``Location(lineno, 1, 6)``.

    If ``end`` is None, it means the end of the line. Note that None
    behaves nicely with slices::

        >>> "hello world"[3:None]
        'lo world'
    """

    # don't allow random attributes
    __slots__ = ()

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
            return Location(start.lineno, start.start, None)

        assert start.lineno == end.lineno, "end is on a line before start"
        return Location(start.lineno, start.start, end.end)


class CompileError(Exception):
    """This is raised and displayed to the user during compilation.

    *message* should be a human-readable string like
    ``"no variable named 'lol'"``.

    The *location* should be a :class:`.Location` object that represents
    the line and column numbers where the error comes from.
    """

    # this throws away the end's lineno, but usually this is good enough
    def __init__(self, message: str, location: Location):
        self.message = message
        self.lineno, self.start, self.end = location

    # this isn't __str__ because this way the arguments don't need to be
    # passed to __init__()
    def show(self, line_of_code, this_is='error'):
        r"""Get a string suitable for displaying to the user.

        *line_of_code* should be the line where this error occurred as a
        string with or without trailing ``\n``. The error message will start
        with *this_is*; usually it should be ``'error'`` or
        ``'warning'``.

        >>> code = "\tbla bla bla"
        >>> error = CompileError("something went wrong", Location(123, 5, 8))
        >>> print(error.show(code))
        error on line 123: something went wrong
          bla bla bla
              ^^^
        """
        # tab expanding makes this a bit tricky... '\tlol\t' is 8
        # characters long with 4-character tabs, not 11 characters
        before_problem = line_of_code[:self.start].expandtabs(4)
        problem = line_of_code[:self.end].expandtabs(4)[len(before_problem):]

        padding = ' ' * len(before_problem.lstrip())
        underline = '^' * len(problem)

        return '\n'.join([
            "%s on line %d: %s" % (this_is, self.lineno, self.message),
            '  ' + line_of_code.expandtabs(4).strip(),
            '  ' + padding + underline,
        ])
