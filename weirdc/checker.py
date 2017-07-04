"""Check an AST tree for errors.

This takes AST nodes and outputs nothing.
"""

import collections
import functools
import itertools
import string as string_module

from weirdc import CompileError, ast, utils


_small_class = functools.partial(utils.miniclass, __name__)

# if the type attribute is None, it means that the object is a class
Type = _small_class('Type', ['name'])
Type.type = None

# "Int a = 1;" doesn't actually track the value of a, it just makes a an
# Instance(INT_TYPE)
Instance = _small_class('Instance', ['type'])

# "hello", 123
Literal = _small_class('Literal', ['constructor_args'], inherit=Instance)

# a FunctionType object represents argument types and return values
# note that FunctionType objects with same argument and return types
# compare unequal
FunctionType = _small_class(
    'FunctionType', ['argtypes', 'returntype'], inherit=Type)

INT_TYPE = Type('Int')
STRING_TYPE = Type('String')     # TODO: rename to just Str?

Variable = _small_class(
    'Variable', ['id', 'value', 'defined_location'],
    default_attrs={'initialized': False, 'used_somewhere': False})


Declaration = _small_class('Declaration', ['id', 'type'])
Assignment = _small_class('Assignment', ['id', 'value'])


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
        raise CompileError("there's already a %s named '%s'" % (what, name),
                           node.location)

    def _get_var(self, name, location, *,
                 require_initialized=True, mark_used=True):
        """Get the value of a variable.

        If mark_used is true, the variable won't look like it's
        undefined. An error is raised if require_initialized is true and
        the value doesn't necessarily have a value yet.
        """
        try:
            var = self._variables[name]
        except KeyError:
            raise CompileError("no variable named '%s'" % name, location)
        if require_initialized and not var.initialized:
            # TODO: better error message
            raise CompileError("variable '%s' is not initialized" % name,
                               location)

        if mark_used:
            var.used_somewhere = True
        return var

    def check_unused_vars(self):
        defined_vars = self._variables.maps[0]
        for name, var in defined_vars.items():
            if not var.used_somewhere:
                # TODO: get rid of the definition of this var
                print(var.defined_location)
                error = CompileError(
                    "this variable isn't used anywhere", var.defined_location)
                print(error.show('the code will appear here later', 'warning'))

    def evaluate(self, expression, *, allow_no_value=False):
        """Pseudo-run an expression."""
        if isinstance(expression, ast.Name):
            var = self._get_var(expression.name, expression.location)
            return var.value

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
                    "this is not a function", expression.function.location)

            args = list(map(self.evaluate, expression.args))
            if [arg.type for arg in args] != func.type.argtypes:
                good = ', '.join(type_.name for type_ in func.type.argtypes)
                bad = ', '.join(arg.type.name for arg in args)
                raise CompileError(
                    "should be {name}({}), not {name}({})"
                    .format(good, bad, name=func.type.name),
                    expression.location)

            if func.type.returntype is None:
                if not allow_no_value:
                    raise CompileError(
                        "this returns nothing", expression.location)
                return None
            else:
                return Instance(func.type.returntype)

        raise NotImplementedError(expression)

    def execute(self, statement):
        """Pseudo-run a statement."""
        if isinstance(statement, ast.Declaration):
            self._error_if_defined(statement.name, statement)
            assert self.kind == 'inner', "global vars aren't supported yet"

            vartype = self.evaluate(statement.type)
            assert vartype is not None
            self._variables[statement.name] = Variable(
                next(self.counter), Instance(vartype), statement.location)

        elif isinstance(statement, ast.Assignment):
            assert isinstance(statement.target, ast.Name)  # TODO

            # TODO: suggest "Int a = 123;" instead of "a = 123;" in the
            # error message
            variable = self._get_var(
                statement.target.name, statement.target.location,
                mark_used=False, require_initialized=False)

            new_value = self.evaluate(statement.value)
            if new_value is None:
                # TODO: better error message
                raise CompileError("this returns nothing",
                                   statement.value.location)

            if new_value.type != variable.value.type:
                # when implementing this, remember to do something
                # (disallow?) assigning to defined functions
                correct_typename = _add_article(
                    "function" if isinstance(variable.type, FunctionType)
                    else variable.type.name)
                wrong_typename = _add_article(
                    "function" if isinstance(new_value.type, FunctionType)
                    else new_type.name)

                raise CompileError(
                    "%s needs to be %s, not %s" % (
                        statement.target.name, correct_typename,
                        wrong_typename),
                    statement.location)

            if self._find_scope(statement.target.name).kind != 'inner':
                raise CompileError(
                    "sorry, global variables aren't supported yet :(",
                    statement.location)

            self._variables[statement.target.name].initialized = True

        elif isinstance(statement, ast.If):
            subscope = Scope(self)
            for substatement in statement.body:
                subscope.execute(substatement)
            subscope.check_unused_vars()

        elif isinstance(statement, ast.FunctionDef):
            assert self.kind != 'builtin'
            raise CompileError(
                "cannot define a function inside a function",
                statement.location)

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
            next(self.counter), Instance(functype), function.location,
            initialized=True)

    def execute_function_def(self, function):
        scope = Scope(self)
        for statement in function.body:
            scope.execute(statement)
        scope.check_unused_vars()


_BUILTIN_SCOPE = Scope(None)
_BUILTIN_SCOPE._variables['Int'] = Variable(
    next(_BUILTIN_SCOPE.counter), INT_TYPE, None, initialized=True)
_BUILTIN_SCOPE._variables['String'] = Variable(
    next(_BUILTIN_SCOPE.counter), STRING_TYPE, None, initialized=True)


def check(ast_nodes):
    global_scope = Scope(_BUILTIN_SCOPE)

    # all functions need to be declared before using them, so we'll just
    # forward-declare everything
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
            ast_tree = list(ast.parse(tokens))
            check(ast_tree)
        except CompileError as error:
            line = code.splitlines()[error.lineno-1]
            print(error.show(line))
        except Exception:
            traceback.print_exc()
        else:
            print("ok")
