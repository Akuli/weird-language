#!/usr/bin/env python3
import collections
import random

from . import ast, c_output


def creates_scope(node, *, classes=(ast.FunctionDef, ast.If)):
    return isinstance(node, classes)


def is_literal(node, *, classes=(ast.String, ast.Integer)):
    return isinstance(node, classes)


def is_weird_object(type_):
    if isinstance(type_, ast.Name):
        type_ = type_.name
    return type_ in c_output.OBJECTS


def modify_body(node, new_body):
    node.body[:] = new_body
    return node


def scope_node(scopes, node):
    simplified_body = scope_ast(node.body, scopes)
    return modify_body(node, simplified_body)


def scope_ast(nodes, scopes=None, return_types={}):
    if scopes is None:
        # We start off with a global scope.
        scopes = collections.ChainMap()

    scoped_nodes = []
    returned_names = {}
    index = 0

    def _store_literals(value, *, from_return=False):
        nonlocal index  # I FINALLY FOUND A USE FOR THIS!

        if isinstance(value, ast.ExpressionStatement):
            value.expression = _store_literals(value.expression)
            return value
        elif isinstance(value, ast.FunctionCall):
            for j, arg in enumerate(value.arguments):
                value.arguments[j] = _store_literals(arg)

            if value.function.name in return_types:
                # TODO: Dry this code.
                rand = "".join(filter(str.isdigit, str(random.random())))
                variable = "literal" + rand
                type_ = return_types[value.function.name]

                assert variable not in scopes
                scopes[variable] = type_

                scoped_nodes.insert(
                    index, ast.Declaration(None, None, type_, variable, value)
                )

                # We must offset all further indexes by one.
                index += 1

                return ast.Name(None, None, variable)
            else:
                # TODO: This is a builtin, and we must someway know their return
                # types.
                return value
        elif isinstance(value, ast.Return):
            value.value = _store_literals(value.value, from_return=True)
            return value
        elif not is_literal(value):
            return value
        # XXX: Is there anything to add?

        rand = "".join(filter(str.isdigit, str(random.random())))
        variable = "literal" + rand
        type_ = ast.Name(None, None, value.__class__.__name__)

        assert variable not in scopes
        scopes[variable] = type_

        scoped_nodes.insert(
            index, ast.Declaration(None, None, type_, variable, value)
        )

        # We must offset all further indexes by one.
        index += 1

        if from_return:
            returned_names[variable] = index

        return ast.Name(None, None, variable)

    for node in nodes:
        if isinstance(node, ast.Declaration):
            variable = node.variable
            if variable in scopes:
                raise RuntimeError("Variable already declared!")
            else:
                scopes[variable] = node.type
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            returned_names[node.value.name] = index
        elif isinstance(node, ast.FunctionDef):
            return_types[node.name] = node.returntype

        node = _store_literals(node)
        if creates_scope(node):
            simplified_node = scope_node(scopes.new_child(), node)
            scoped_nodes.append(simplified_node)
        else:
            scoped_nodes.append(node)

        index += 1

    decrefs = []
    for name, type_ in scopes.maps[0].items():
        if name not in returned_names and is_weird_object(type_):
            decrefs.append(ast.DecRef(name))

    # index is the length of scoped_nodes, offset by all the included nodes at
    # this point, however it is off by one (this is not a bug)
    for j in set(returned_names.values()) | {index - 1}:
        scoped_nodes[j:j] = decrefs

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
