"""Produce C code from an AST tree.

This is a very minimal version and will probably change a lot later.
"""

import random

from weirdc import ast


PRELOAD = r"""
#include <stdio.h>
#include <string.h>


static void do_the_print(char *message)
{
    printf("%s", message);
}


#define MAXLEN 1000

static char *do_the_input()
{
    char c, result[MAXLEN+1];    /* 1 is the 0 at the end */
    int i;

    for (i = 0; i < MAXLEN; i++) {
        c = getchar();
        if (c == EOF || c == '\n')
            break;
        result[i] = c;
    }
    result[i] = 0;

    /* this sucks because this isn't freed anywhere :(
       like david beazley says: call it a prototype */
    return strdup(result);
}
"""
names = {'Int': 'int', 'Text': 'char *',
         'print': 'do_the_print', 'input': 'do_the_input', 'main': 'main'}


def random_name():
    return 'name' + ''.join(filter(str.isdigit, str(random.random())))


def unparse(node):
    # this is used just for parsing function definitions
    if node is None:
        return 'void'

    if isinstance(node, ast.Name):
        return names[node.name]
    if isinstance(node, ast.Integer):
        return str(node.value)
    if isinstance(node, ast.String):
        # TODO: escaping and other stuff
        return '"' + node.value + '"'
    if isinstance(node, ast.ExpressionStatement):
        return unparse(node.expression) + ';'
    if isinstance(node, ast.Return):
        return 'return %s;' % unparse(node.value)

    if isinstance(node, ast.Declaration):
        names[node.variable] = node.variable
        if node.value is None:
            return '%s %s;' % (unparse(node.type), node.variable)
        return '%s %s = %s;' % (
            unparse(node.type), node.variable, unparse(node.value))

    if isinstance(node, ast.FunctionCall):
        return '%s(%s)' % (
            unparse(node.function),
            ','.join(map(unparse, node.arguments)),
        )

    if isinstance(node, ast.FunctionDef):
        assert not node.arguments   # lol
        if node.name not in names:
            names[node.name] = random_name()
        return '%s %s(void) { %s }' % (
            unparse(node.returntype),
            names[node.name],
            ''.join(map(unparse, node.body))
        )

    raise TypeError(f"don't know how to unparse {node!r}")
