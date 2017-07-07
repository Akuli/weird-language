"""Check an AST tree for errors.

This takes AST nodes and outputs nothing.
"""

from collections import ChainMap, Counter
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

# a FunctionType object represents argument types and return values
# note that FunctionType objects with same argument and return types
# compare unequal
FunctionType = _small_class(
    'FunctionType', ['argtypes', 'returntype'], inherit=Type)

INT_TYPE = Type('Int')
STRING_TYPE = Type('String')     # TODO: rename to just Str or maybe Text?
BOOL_TYPE = Type('Bool')

TRUE = Instance(BOOL_TYPE)
FALSE = Instance(BOOL_TYPE)

# used_by is a list of statement nodes that do something with this variable
# the [] is copied when a new Variable object is created, see utils.py
Variable = _small_class(
    'Variable', ['value', 'defined_location'],
    default_attrs={'initialized': False, 'used_by': []})


# TODO: support some kind of inheritance? currently == is used for
# comparing types everywhere
class Scope:

    # returntype can't be optional because then it's default value
    # couldn't be None since None means a function that doesn't return
    # a value
    def __init__(self, parent, returntype, *, warn_callback=None):
        self.parent = parent
        self.output = []

        # self._variables is {name: Variable}
        if parent is None:
            # this is the built-in scope
            self._variables = {}
            self._warn_callback = warn_callback
            self.returntype = returntype
            self.kind = 'builtin'
        else:
            # defining a variable here must not go to the parent scope's
            # variables, that's why {} here
            self._variables = ChainMap({}, parent._variables)
            self._warn_callback = parent._warn_callback or warn_callback
            self.returntype = returntype or parent.returntype

            if parent.kind == 'builtin':
                self.kind = 'file'
            else:
                assert parent.kind in {'file', 'inner'}
                self.kind = 'inner'

    def warn(self, *args, **kwargs):
        self._warn_callback(CompileError(*args, **kwargs))

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

    def _get_var(self, name, location, *, require_initialized=True):
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
            raise CompileError(
                "variable '%s' might not have a value yet" % name, location)

        return var

    def check_unused_vars(self):
        # these vars were defined in this scope, not in one of the
        # parent scopes
        defined_vars = self._variables.maps[0]

        for name, var in defined_vars.items():
            if not all(isinstance(node, (ast.Declaration, ast.Assignment))
                       for node in var.used_by):
                continue

            definition = var.used_by[0]
            assert isinstance(definition, ast.Declaration)
            self.warn("this variable isn't used anywhere",
                      var.used_by[0].location)

            # now we need to delete this variable everywhere...
            for statement in var.used_by:
                if (isinstance(statement, ast.Assignment)
                        and isinstance(statement.value, ast.FunctionCall)):
                    # unused_var = lel();   // replace with just lel();
                    replacement = ExpressionStatement(None, statement.value)
                    self.output[self.output.index(statement)] = replacement
                else:
                    # String s;              // goodbye, we don't need you
                    # String s = "literal";  // just "literal"; would be no-op
                    self.output.remove(statement)

    def evaluate(self, expression, source_statement, *, allow_no_value=False):
        """Pseudo-run an expression.

        The source_statement should be the statement node that the
        expression node comes from. It will be added to a variable's
        used_by list if a variable needs to be evaluated. Set it to None
        if you don't want to add the statement to used_by lists.
        """
        if isinstance(expression, ast.Name):
            var = self._get_var(expression.name, expression.location)
            if source_statement is not None:
                var.used_by.append(source_statement)
            return var.value

        if isinstance(expression, ast.Integer):
            return Instance(INT_TYPE)

        if isinstance(expression, ast.String):
            return Instance(STRING_TYPE)

        if isinstance(expression, ast.FunctionCall):
            func = self.evaluate(expression.function, source_statement)
            if not isinstance(func.type, FunctionType):
                raise CompileError(
                    "this is not a function", expression.function.location)

            args = [self.evaluate(arg, source_statement)
                    for arg in expression.args]
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

        raise NotImplementedError(expression)   # pragma: no cover

    def execute(self, statement):
        """Pseudo-run a statement."""
        if isinstance(statement, ast.Declaration):
            self._error_if_defined(statement.name, statement)
            assert self.kind == 'inner', "global vars aren't supported yet"

            vartype = self.evaluate(statement.type, statement)
            assert vartype is not None
            if vartype.type is not None:
                raise CompileError(
                    "variable types need to be classes, not %s instances"
                    % vartype.type.name, statement.type.location)

            var = Variable(Instance(vartype), statement.location,
                           used_by=[statement])
            self._variables[statement.name] = var
            self.output.append(statement)

        elif isinstance(statement, ast.Assignment):
            assert isinstance(statement.target, ast.Name)  # TODO

            try:
                variable = self._get_var(
                    statement.target.name, statement.target.location,
                    require_initialized=False)
            except CompileError:
                value = self.evaluate(statement.value, statement)
                raise CompileError(
                    "you need to declare '{varname}' first, "
                    'e.g. "{typename} {varname};"'
                    .format(typename=value.type.name,
                            varname=statement.target.name),
                    statement.location)

            variable.used_by.append(statement)

            if self._find_scope(statement.target.name).kind != 'inner':
                assert isinstance(variable.value.type, FunctionType)
                raise CompileError("functions can't be changed like this",
                                   statement.target.location)

            new_value = self.evaluate(statement.value, statement)
            if new_value.type != variable.value.type:
                correct_typename = utils.add_article(
                    "function" if isinstance(variable.value.type, FunctionType)
                    else variable.value.type.name)
                wrong_typename = utils.add_article(
                    "function" if isinstance(new_value.type, FunctionType)
                    else new_value.type.name)

                # FIXME: it's possible to end up with something like
                # "myvar needs to be a function, not a function"
                raise CompileError(
                    "'%s' needs to be %s, not %s" % (
                        statement.target.name, correct_typename,
                        wrong_typename),
                    statement.location)

            self._variables[statement.target.name].initialized = True
            self.output.append(statement)

        elif isinstance(statement, ast.If):
            subscope = Scope(self, self.returntype)
            for substatement in statement.body:
                substatement.execute(statement)
            subscope.check_unused_vars()
            statement.body = subscope.output
            self.output.append(statement)

        elif isinstance(statement, ast.FunctionDef):
            assert self.kind != 'builtin'
            raise CompileError(
                "cannot define a function inside a function",
                statement.location)

        elif isinstance(statement, ast.ExpressionStatement):
            if isinstance(statement.expression, ast.FunctionCall):
                self.evaluate(statement.expression, statement,
                              allow_no_value=True)
                self.output.append(statement)
            else:
                # the evaluate() raises errors if something's wrong
                self.warn("this does nothing", statement.location)
                self.evaluate(statement.expression, None)
                # don't append it to self.output

        elif isinstance(statement, ast.Return):
            value = self.evaluate(statement.value, statement)
            if value.type != self.returntype:
                raise CompileError(
                    "this function should return %s, not %s"
                    % (utils.add_article(self.returntype.name),
                       utils.add_article(value.type.name)),
                    statement.location)
            self.output.append(statement)

        else:     # pragma: no cover
            raise NotImplementedError(statement)

    # TODO: allow defining functions after using them
    #   function thingy() { stuff(); }
    #   function stuff() { ... }
    def declare_function(self, function):
        self._error_if_defined(function.name, function)
        if function.name == 'main':
            # TODO: create equivalents of sys.exit() and sys.argv, then
            # recommend them here
            if function.returntype != None:
                raise CompileError("main() must not return anything",
                                   function.location)
            if function.args:
                raise CompileError("main() must not take arguments")

        if function.returntype is None:
            returntype = None
        else:
            returntype = self.evaluate(function.returntype, function)
            if returntype.type is not None:
                raise CompileError(
                    "return types need to be classes, not %s instances"
                    % returntype.type.name, function.returntype.location)

        argnames = [namenode.name for argtype, namenode in function.args]
        for arg in argnames:
            if argnames.count(arg) > 1:
                raise CompileError(
                    "there are %d arguments named '%s'"
                    % (argnames.count(arg), arg), function.location)

        argtypes = [self.evaluate(argtype, None)
                    for argtype, name in function.args]
        functype = FunctionType(function.name, argtypes, returntype)
        self._variables[function.name] = Variable(
            Instance(functype), function.location, initialized=True)

    def execute_function_def(self, function):
        returntype = self._variables[function.name].value.type.returntype
        scope = Scope(self, returntype)
        for statement in function.body:
            scope.execute(statement)

        scope.check_unused_vars()
        function.body = scope.output
        self.output.append(function)


_builtin_vars = {
    'Int': INT_TYPE,
    'String': STRING_TYPE,
    'Bool': BOOL_TYPE,
    'TRUE': TRUE,
    'FALSE': FALSE,
}

_BUILTIN_SCOPE = Scope(None, None)
_BUILTIN_SCOPE._variables.update({
    name: Variable(value, None, initialized=True)
    for name, value in _builtin_vars.items()})


def check(ast_nodes, warn_callback):
    # must not be an iterator because this loops over it several times
    assert ast_nodes is not iter(ast_nodes)

    for node in ast_nodes:
        if not isinstance(node, ast.FunctionDef):
            # TODO: allow global vars and get rid of main functions
            raise CompileError("only function definitions can be here",
                               node.location)
    if 'main' not in (func.name for func in ast_nodes):
        raise CompileError("there's no main() function", None)

    global_scope = Scope(_BUILTIN_SCOPE, None, warn_callback=warn_callback)

    # all functions need to be declared before using them, so we'll just
    # forward-declare everything
    for func in ast_nodes:
        global_scope.declare_function(func)
    for func in ast_nodes:
        global_scope.execute_function_def(func)

    # ast nodes are mutated too, so i think it makes sense to mutate
    # everything instead of making new objects
    ast_nodes[:] = global_scope.output
