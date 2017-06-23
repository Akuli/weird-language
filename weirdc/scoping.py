#!/usr/bin/env python3
import collections

from . import ast, c_output


def creates_scope(node, *, classes=(ast.FunctionDef, ast.If)):
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


def scope_ast(nodes, scopes=None):
    if scopes is None:
        # We start off with a global scope.
        scopes = collections.ChainMap()

    scoped_nodes = []
    returned_names = {}

    for index, node in enumerate(nodes):
        if creates_scope(node):
            simplified_node = scope_node(scopes.new_child(), node)
            scoped_nodes.append(simplified_node)
        else:
            scoped_nodes.append(node)

        if isinstance(node, ast.Declaration):
            variable = node.variable
            if variable in scopes:
                raise RuntimeError("Variable already declared!")
            else:
                scopes[variable] = node.type
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            returned_names[node.value.name] = index

    decrefs = []
    for name, type_ in scopes.maps[0].items():
        if name not in returned_names and is_weird_object(type_):
            decrefs.append(ast.DecRef(name))

    for index in set(returned_names.values()) | {len(scoped_nodes)}:
        scoped_nodes[index:index] = decrefs

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
