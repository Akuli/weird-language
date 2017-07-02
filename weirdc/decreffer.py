"""Add DecRef nodes."""

from collections import namedtuple
import itertools

from weirdc import ast


def _nodetype(name, fields):
    # this is equivalent enough to doing this:
    #    class <name>:
    #        # only allow these attributes
    #        __slots__ = <fields> + ['start', 'end']
    #
    #        def __init__(self, <fields>):
    #            for each field:
    #                self.<field> = <field>
    #
    #        # just for debugging
    #        def __repr__(self):
    #            return '<name>(<values of the fields>)'
    def dunder_init(self, *args):
        assert len(fields) == len(args)
        for name, value in zip(fields, args):
            setattr(self, name, value)

    def dunder_repr(self):
        parts = [repr(getattr(self, name)) for name in fields]
        return 'decreffer.' + name + '(' + ', '.join(parts) + ')'

    return type(name, (), {
        '__slots__': fields + ['start', 'end'],
        '__init__': dunder_init,
        '__repr__': dunder_repr,
    })


Declaration = _nodetype('Declaration', ['name', 'value'])
FunctionDef = _nodetype('FunctionDef', ['name', 'args', 'returntype', 'body'])
FunctionCall = _nodetype('FunctionCall', ['function', 'arguments'])
DecRef = _nodetype('DecRef', ['name'])

random_name = map('tempvar{}'.format, itertools.count(1)).__next__


class _Scoper:

    def __init__(self):
        self.output = []

    def _store_function_call(self, node):
        argument_names = []
        for argument in node.arguments:
            if isinstance(argument, ast.Name):
                argument_names.append(argument.name)
            else:
                # is_temporary was here
                print('*** Wolo Wolo', argument)
                name = random_name()
                self.output.append(Declaration(name, argument))
                argument_names.append(name)

        assert isinstance(node.function, ast.Name)   # lel
        func_name = random_name()
        func_call = FunctionCall(node.function.name, argument_names)
        self.output.append(Declaration(func_name, func_call))
        self.output.append(DecRef(func_name))

        for name in argument_names:
            self.output.append(DecRef(name))

    def decref_scope(self, statements):
        defined_variables = []

        for statement in statements:
            if isinstance(statement, ast.Declaration):
                defined_variables.append(statement.name)
            elif isinstance(statement, (ast.FunctionDef, ast.If)):
                scoper = _Scoper()
                scoper.decref_scope(statement.body)
                statement.body = scoper.output
            elif (isinstance(statement, ast.ExpressionStatement)
                  and isinstance(statement.expression, ast.FunctionCall)):
                self._store_function_call(statement.expression)
            else:
                self.output.append(statement)
        self.output.extend(map(DecRef, defined_variables))


def add_decrefs(function):
    scoper = _Scoper()
    scoper.decref_scope(function.body)
    return scoper.output


if __name__ == '__main__':
    from weirdc import tokenizer

    code = '''
    function main() returns Int {
        stuff(thing());
        return 0;
    }
    '''

    [astfunc] = ast.parse(tokenizer.tokenize(code))

    for decreffernode in add_decrefs(astfunc):
        print(decreffernode)
