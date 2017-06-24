#!/usr/bin/env python3
import collections
import random

from . import ast


def creates_scope(node, *, classes=(ast.FunctionDef, ast.If)):
    return isinstance(node, classes)


def is_literal(node, *, classes=(ast.String, ast.Integer)):
    return isinstance(node, classes)


def scope_ast(nodes, scopes=None, return_types=None):
    if scopes is None:
        # We start off with a global scope.
        scopes = collections.ChainMap()

    if return_types is None:
        return_types = {}

    scoped_nodes = []
    returned_names = {}

    def _create_variable(value, var_type):
        rand = "".join(filter(str.isdigit, str(random.random())))
        variable = "literal" + rand

        assert variable not in scopes
        scopes[variable] = var_type

        scoped_nodes.append(
            ast.Declaration(None, None, var_type, variable, value)
        )

        return ast.Name(None, None, variable)

    def _store_literals(value):
        if isinstance(value, ast.ExpressionStatement):
            # TODO: Save the whole expression's result to a temporary var.
            value.expression = _store_literals(value.expression)
            return value
        elif isinstance(value, ast.FunctionCall):
            for j, arg in enumerate(value.arguments):
                value.arguments[j] = _store_literals(arg)

            if value.function.name in return_types:
                return _create_variable(
                    value, return_types[value.function.name])
            # XXX: This return statement is only executed when the function is
            # a builtin, ergo it's not in return_types. Maybe we could
            # circumvent this by providing return_types with the builtins'
            # types?
            return value
        elif isinstance(value, ast.Return):
            value.value = _store_literals(value.value)
            returned_names[value.value.name] = len(scoped_nodes)
            return value
        elif not is_literal(value):
            return value

        name = _create_variable(
            value, ast.Name(None, None, value.__class__.__name__)
        )

        return name

    for node in nodes:
        if isinstance(node, ast.Declaration):
            variable = node.variable
            if variable in scopes:
                raise RuntimeError("Variable already declared!")
            else:
                scopes[variable] = node.type
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            # We have to account for the fact that the return statement is
            # added to scoped_nodes later.
            returned_names[node.value.name] = len(scoped_nodes) + 1
        elif isinstance(node, ast.FunctionDef):
            return_types[node.name] = node.returntype

        node = _store_literals(node)
        if creates_scope(node):
            node.body[:] = scope_ast(node.body, scopes.new_child())
        scoped_nodes.append(node)

    decrefs = [ast.DecRef(name)
               for name in scopes.maps[0]
               if name not in returned_names]

    # XXX: Figure out why this works.
    if returned_names:
        for j in set(returned_names.values()) | {len(scoped_nodes) - 1}:
            scoped_nodes[j:j] = decrefs
    else:
        scoped_nodes.extend(decrefs)

    return scoped_nodes


if __name__ == "__main__":
    from . import tokenizer

    SAMPLE_CODE = '''\
    int a = 1;

    main() -> Int {
        int b = 3;
        return b;
    }

    if TRUE {
        int b = 2;
    }
    if TRUE {
        int b = 3;      // ok
    }
    int b = 4;     // error
    '''

    tree = ast.parse(tokenizer.tokenize(SAMPLE_CODE))
    tree = scope_ast(tree)

    print(*tree, sep="\n")
