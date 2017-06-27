"""Check for errors and fill in missing information.

This adds stuff like return types of function calls.
"""

import collections
import itertools

from weirdc import ast


def _miniclass(name, fields, inherit=None):
    # __slots__ can be a list, but mutating it afterwards doesn't change
    # anything so it just confuses stuff
    fields = tuple(fields)

    if inherit is None:
        all_fields = fields
    else:
        all_fields = tuple(inherit.__slots__) + fields

    def dunder_init(self, *args):
        assert len(args) == len(all_fields)
        for name, value in zip(all_fields, args):
            setattr(self, name, value)

    def dunder_repr(self):
        values = [repr(getattr(self, name)) for name in all_fields]
        this_module_name = __name__.split('.')[-1]
        return '%s.%s(%s)' % (this_module_name, name, ', '.join(values))

    return type(name, (() if inherit is None else (inherit,)), {
        '__slots__': fields,
        '__init__': dunder_init,
        '__repr__': dunder_repr,
    })


Type = _miniclass('Type', ['weirdname'])
Function = _miniclass('Function', ['argtypes', 'returntype'], inherit=Type)

# weirdtype can be ast.Name or None, this declares a new type if it's None
# if value is None, the variable is declared like Int a; but nothing has
# been assigned to it yet
Variable = _miniclass('Variable', [
    'type', 'initialized', 'definition_start', 'definition_end'])

INT_TYPE = Type('Int')
STRING_TYPE = Type('String')     # TODO: rename to just Str?


def typeof(node):
    if isinstance(node, ast.Integer):
        return INT_TYPE
    if isinstance(node, ast.String):
        return STRING_TYPE
    raise NotImplementedError(node)


def _add_article(string):
    if string.lower()[0] in 'AEIOUYaeiouy':
        return 'an ' + string
    return 'a ' + string


class Scope:

    def __init__(self, parent):
        self.parent = parent

        # self.variables is {weirdname: Variable}
        if parent is None:
            # this is the built-in scope
            self.variables = {}
            self.kind = 'builtin'
        else:
            # defining a variable here must no go to the parent scope's
            # variables, that's why {} here
            self.variables = collections.ChainMap({}, parent.variables)

            if parent.kind == 'builtin':
                self.kind = 'file'
            else:
                assert parent.kind in {'file', 'inner'}
                self.kind = 'inner'

    def _error_if_defined(self, name, node):
        """Raise CompileError if a variable exists already.

        The node's start and end will be used in the error message if
        the var exists.
        """
        # TODO: include information about where the variable was defined
        if name not in self.variables:
            return

        variable = self.variables[name]
        what = ('function' if isinstance(variable.type, Function)
                else 'variable')
        raise CompileError(
            "there's already a %s named '%s'" % (what, name),
            node.start, node.end)

    def _error_if_undefined(self, name, node):
        if name not in self.variables:
            raise CompileError(
                "no variable or function '%s'" % name, node.start, node.end)

    def _check_unused_vars(self):
        defined_vars = self.variables.maps[0]
        for name, var in defined_vars.items():
            # TODO: remove the variable definition from the AST
            # TODO: handle "Int a = 1;" (Declaration and Assignment)
            if not var.initialized:
                print("WARNING: unused variable '%s' defined on line %d"
                        % (name, var.definition_start[0]))

    def evaluate(self, expression):
        """Pseudo-run an expression."""
        #print('   evaluating', expression)
        if isinstance(expression, ast.Name):
            try:
                return self.variables[expression.name]
            except KeyError:
                raise CompileError(
                    "unknown variable '%s'" % expression.name,
                    expression.start, expression.end)
        if isinstance(expression, ast.Integer):
            # this mixes ast nodes and things defined here, but it
            # doesn't really matter because the ast nodes are used for
            # internal checking only
            return expression
        else:
            raise NotImplementedError(expression)

    def execute(self, statement):
        """Pseudo-run a statement."""
        #print(self.kind, "scope: executing", statement)
        if isinstance(statement, ast.Declaration):
            self._error_if_defined(statement.name, statement)
            assert self.kind == 'inner', "global vars aren't supported yet"

            vartype = self.evaluate(statement.type)
            self.variables[statement.name] = Variable(
                vartype, False, statement.start, statement.end)

        elif isinstance(statement, ast.Assignment):
            assert isinstance(statement.target, ast.Name)  # TODO

            # TODO: suggest "Int a = 123;" instead of "a = 123;"
            self._error_if_undefined(statement.target.name, statement)

            # TODO: support some kind of subclassing?
            variable = self.variables[statement.target.name]
            if typeof(statement.value) != variable.type:
                # TODO: better error message
                raise CompileError(
                    "wrong type", statement.start, statement.end)

            self.variables[statement.target.name].initialized = True

        elif isinstance(statement, ast.If):
            subscope = Scope(self)
            for substatement in statement.body:
                subscope.execute(substatement)
            subscope._check_unused_vars()

        elif isinstance(statement, ast.FunctionDef):
            self._error_if_defined(statement.name, statement)

            assert self.kind != 'builtin'
            if self.kind != 'file':
                raise CompileError(
                    "cannot define a function inside a function",
                    statement.start, statement.end)

            # TODO: handle these
            assert statement.returntype is None
            assert not statement.args

            # this must be done before pseudo-running the body because
            # otherwise this passes silently:
            #   function lel() { Int lel = 123; }
            functype = Function(statement.name, [], None)
            self.variables[statement.name] = Variable(
                functype, False, statement.start, statement.end)

            subscope = Scope(self)
            for substatement in statement.body:
                subscope.execute(substatement)
            subscope._check_unused_vars()

        else:
            raise NotImplementedError(statement)


_BUILTIN_SCOPE = Scope(None)
_BUILTIN_SCOPE.variables.update({
    'Int': INT_TYPE,
    'String': STRING_TYPE,
})


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
    def __init__(self, message, start, end):
        # (line, column) tuples compare nicely
        if start > end:
            raise ValueError("the error ends before it starts")

        self.message = message
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
            self.end = None


def check(ast_nodes):
    global_scope = Scope(_BUILTIN_SCOPE)
    for statement in ast_nodes:
        global_scope.execute(statement)
    #global_scope._check_unused_vars()


if __name__ == '__main__':
    from weirdc import tokenizer
    code = '''
    function lel() {
        Int lulz;
        Int a = 1;
        if a {
            a = 2;
        }
        lel = 2;     //ERRROR
    }
    '''
    ast_tree = list(ast.parse(tokenizer.tokenize(code)))
    try:
        check(ast_tree)
    except CompileError as error:
        # minimal error reporting :)
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
