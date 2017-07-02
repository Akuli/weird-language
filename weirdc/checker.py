"""Check for errors and add decrefs.

This takes AST nodes and outputs its own nodes.
"""

import collections
import itertools
import string as string_module

from weirdc import ast


def _miniclass(name, fields, *, inherits=None, default_attrs=None):
    # __slots__ can be a list, but mutating it afterwards doesn't change
    # anything so it just confuses stuff
    fields = tuple(fields)
    if default_attrs is None:
        default_attrs = {}

    if inherits is None:
        all_fields = fields
    else:
        all_fields = tuple(inherits.__slots__) + fields

    def dunder_init(self, *args, **kwargs):
        assert len(args) == len(all_fields)
        assert set(kwargs.keys()).issubset(default_attrs.keys())

        for name, value in zip(all_fields, args):
            setattr(self, name, value)
        for name, value in collections.ChainMap(kwargs, default_attrs).items():
            setattr(self, name, value)

    def dunder_repr(self):
        values = [repr(getattr(self, name)) for name in all_fields]
        this_module_name = __name__.split('.')[-1]
        return '%s.%s(%s)' % (this_module_name, name, ', '.join(values))

    def dunder_eq(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        for name in all_fields:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    return type(name, (() if inherits is None else (inherits,)), {
        '__slots__': fields + tuple(default_attrs),
        '__init__': dunder_init,
        '__repr__': dunder_repr,
        '__eq__': dunder_eq,
        # __ne__ works automagically
    })


# if the type attribute is None, it means that the object is a class
Type = _miniclass('Type', ['name'])
Type.type = None

# "Int a = 1;" doesn't actually track the value of a, it just makes a an
# Instance(INT_TYPE)
Instance = _miniclass('Instance', ['type'])

# "hello", 123
Literal = _miniclass('Literal', ['constructor_args'], inherits=Instance)

FunctionType = _miniclass(
    'FunctionType', ['argtypes', 'returntype'], inherits=Type)

INT_TYPE = Type('Int')
STRING_TYPE = Type('String')     # TODO: rename to just Str?

Variable = _miniclass(
    'Variable', ['id', 'value', 'definition_start', 'definition_end'],
    default_attrs={'initialized': False, 'used_somewhere': False})


class CompileError(Exception):
    """This is raised and displayed to the user during compilation.

    CompileError objects have ``message``, ``lineno``, ``start`` and
    ``end`` attributes. ``message`` is a string, ``endcolumn`` is an
    integer or None and other attributes are integers.

    ``start`` and ``end`` are column numbers. Note that None behaves
    nicely in slices, so ``line[error.start:error.end]`` always works::

        >>> 'hello'[2:None]      # same as 'hello'[2:]
        'llo'
    """

    # this throws away the end's lineno, but usually this is good enough
    def __init__(self, message, location):
        self.message = message

        if location is None:
            start = end = None
        else:
            try:
                start, end = location.start, location.end
            except AttributeError:
                # assume a (start, end) tuple
                start, end = location

        if start is None or end is None:
            print("WARNING: missing start or end")
            self.lineno = None
            self.start = None
            self.end = None
            return

        # (line, column) tuples compare nicely
        if start > end:
            raise ValueError("the error ends before it starts")

        self.lineno, self.start = start

        endlineno, endcolumn = end
        if start == end:
            # let's highlight the character right after the spot that
            # start and end point at
            endcolumn += 1

        if endlineno == self.lineno:
            self.end = endcolumn
        else:
            # it's never-ending :D
            # we can only display the first line in an error message, so
            # we'll just display until its end
            self.end = None


def _add_article(string):
    # if the string is prefixed with e.g. quotes, handle that
    first_letter = string.lstrip(string_module.punctuation)[0]
    article = 'an' if first_letter in 'AEIOUYaeiouy' else 'a'
    return article + ' ' + string


# TODO: support some kind of inheritance? currently == is used for
# comparing types everywhere
class Scope:

    def __init__(self, parent):
        self.parent = parent

        # self._variables is {name: Variable}
        if parent is None:
            # this is the built-in scope
            self._variables = {}
            self.counter = itertools.count(1)
            self.kind = 'builtin'
        else:
            # defining a variable here must no go to the parent scope's
            # variables, that's why {} here
            self._variables = collections.ChainMap({}, parent._variables)
            self.counter = parent.counter

            if parent.kind == 'builtin':
                self.kind = 'file'
            else:
                assert parent.kind in {'file', 'inner'}
                self.kind = 'inner'

    def _find_scope(self, varname):
        """Return the scope where a variable is defined."""
        scope = self
        while varname not in scope._variables.maps[0]:
            scope = scope.parent
        return scope

    def _error_if_defined(self, name, node):
        """Raise CompileError if a variable exists already.

        The node's start and end will be used in the error message if
        the var exists.
        """
        # TODO: include information about where the variable was defined
        if name not in self._variables:
            return

        variable = self._variables[name]
        what = ('function' if isinstance(variable.value.type, FunctionType)
                else 'variable')
        msg = "there's already a %s named '%s'" % (what, name)
        raise CompileError(msg, node)

    def _get_var(self, name, node, *,
                 require_initialized=True, mark_used=True):
        """Get the value of a variable.

        If mark_used is true, the variable won't look like it's
        undefined. An error is raised if require_initialized is true and
        the value doesn't necessarily have a value yet.
        """
        try:
            var = self._variables[name]
        except KeyError:
            raise CompileError("no variable named '%s'" % name, node)
        if require_initialized and not var.initialized:
            # TODO: better error message
            raise CompileError("variable '%s' is not initialized")

        if mark_used:
            var.used_somewhere = True
        return var

    def check_unused_vars(self):
        defined_vars = self._variables.maps[0]
        for name, var in defined_vars.items():
            if not var.used_somewhere:
                # TODO: remove everything that uses this var from the AST
                print("WARNING: unused variable '%s' defined on line %d"
                      % (name, var.definition_start[0]))

    def evaluate(self, expression, *, allow_no_value=False):
        """Pseudo-run an expression."""
        if isinstance(expression, ast.Name):
            var = self._get_var(expression.name, expression)
            if var.value is not None:
                # we know its value already for some reason
                return var.value
            return Instance(var.type)

        if isinstance(expression, ast.Integer):
            return Literal(INT_TYPE, [str(expression.value)])

        if isinstance(expression, ast.String):
            # TODO: use wchars to fix unicode issues
            return Literal(
                STRING_TYPE, [str(expression.value), len(expression.value)])

        if isinstance(expression, ast.FunctionCall):
            func = self.evaluate(expression.function)
            if not isinstance(func.type, FunctionType):
                raise CompileError(
                    "'%s' is not a function", expression.function)

            args = list(map(self.evaluate, expression.args))

            error = (len(args) != len(func.type.argtypes))
            if not error:
                # we got the correct number of arguments, so we need to
                # check their types too
                for arg, expected_type in zip(args, func.type.argtypes):
                    if arg.type != expected_type:
                        error = True
            if error:
                good = ', '.join(t.name for t in func.type.argtypes)
                bad = ', '.join(arg.type.name for arg in args)
                raise CompileError(
                    "should be {name}({}), not {name}({})"
                    .format(good, bad, name=func.type.name),
                    expression)

            if func.type.returntype is None:
                if not allow_no_value:
                    raise CompileError("this returns nothing", expression)
                return None
            else:
                return Instance(func.type.returntype)

        else:
            raise NotImplementedError(expression)

    def execute(self, statement):
        """Pseudo-run a statement."""
        if isinstance(statement, ast.Declaration):
            self._error_if_defined(statement.name, statement)
            assert self.kind == 'inner', "global vars aren't supported yet"

            vartype = self.evaluate(statement.type)
            assert vartype is not None
            self._variables[statement.name] = Variable(
                next(self.counter), Instance(vartype),
                statement.start, statement.end)

        elif isinstance(statement, ast.Assignment):
            assert isinstance(statement.target, ast.Name)  # TODO

            # TODO: suggest "Int a = 123;" instead of "a = 123;" in the
            # error message
            variable = self._get_var(
                statement.target.name, statement.target,
                mark_used=False, require_initialized=False)

            new_value = self.evaluate(statement.value)
            if new_value is None:
                # TODO: better error message
                raise CompileError("this returns nothing", statement.value)

            if new_value.type != variable.value.type:
                # when implementing this, remember to do something
                # (disallow?) assigning to defined functions
                correct_typename = _add_article(
                    "function" if isinstance(variable.type, FunctionType)
                    else variable.type.name)
                wrong_typename = _add_article(
                    "function" if isinstance(new_value.type, FunctionType)
                    else new_type.name)

                msg = "%s needs to be %s, not %s" % (
                    statement.target.name, correct_typename, wrong_typename)
                raise CompileError(msg, statement)

            if self._find_scope(statement.target.name).kind != 'inner':
                raise CompileError(
                    "sorry, global variables aren't supported yet :(",
                    statement)

            self._variables[statement.target.name].initialized = True

        elif isinstance(statement, ast.If):
            subscope = Scope(self)
            for substatement in statement.body:
                subscope.execute(substatement)
            subscope.check_unused_vars()

        elif isinstance(statement, ast.FunctionDef):
            assert self.kind != 'builtin'
            raise CompileError(
                "cannot define a function inside a function", statement)

        elif isinstance(statement, ast.ExpressionStatement):
            value = self.evaluate(statement.expression, allow_no_value=True)
            if value is not None:
                pass   # TODO: decref it
        else:
            raise NotImplementedError(statement)

    # TODO: allow defining functions after using them
    #   function thingy() { stuff(); }
    #   function stuff() { ... }
    def declare_function(self, function):
        self._error_if_defined(function.name, function)

        # TODO: handle these
        assert function.returntype is None
        argtypes = [self.evaluate(argtype)
                    for argtype, name in function.args]

        # this must be done before going through the body because
        # otherwise this passes silently:
        #   function lel() { Int lel = 123; }
        functype = FunctionType(function.name, argtypes, None)
        self._variables[function.name] = Variable(
            next(self.counter), Instance(functype),
            function.start, function.end, initialized=True)

    def execute_function_def(self, function):
        scope = Scope(self)
        for statement in function.body:
            scope.execute(statement)
        scope.check_unused_vars()


#['id', 'value', 'definition_start', 'definition_end'],
_BUILTIN_SCOPE = Scope(None)
_BUILTIN_SCOPE._variables.update({
    'Int': Variable(next(_BUILTIN_SCOPE.counter), INT_TYPE, None, None, initialized=True),
    'String': Variable(next(_BUILTIN_SCOPE.counter), STRING_TYPE, None, None, initialized=True),
})


def check(ast_nodes):
    global_scope = Scope(_BUILTIN_SCOPE)

    # all functions need to be declared before using them in C, so we'll
    # just forward-declare everything
    for function in ast_nodes:
        global_scope.declare_function(function)
    for function in ast_nodes:
        global_scope.execute_function_def(function)


if __name__ == '__main__':
    try:
        import readline
    except ImportError:
        pass
    import traceback
    from weirdc import tokenizer

    while True:
        code = '''
        function lel(Int a) { }

        function main() {
            %s
        }
        ''' % input('> ')

        try:
            tokens = tokenizer.tokenize(code)
            ast_tree = list(ast.parse(tokens, code.splitlines()))
            check(ast_tree)
        except CompileError as error:
            # minimal but cool error handling :)
            if error.lineno is None:
                # there's no information about where it came from :( this
                # should probably be fixed
                raise error

            line = code.splitlines()[error.lineno-1]

            # tab expanding makes this a bit tricky... '\tlol\t' is 8
            # characters long with 4-character tabs, not 11 characters
            before_error_part = line[:error.start].expandtabs(4)
            error_part = line[:error.end].expandtabs(4)[len(before_error_part):]

            padding = ' ' * len(before_error_part.lstrip())
            underline = '^' * len(error_part)

            print("error on line %d: %s" % (error.lineno, error.message))
            print('  ' + line.expandtabs(4).lstrip())
            print('  ' + padding + underline)
            print()

        except Exception:
            traceback.print_exc()
