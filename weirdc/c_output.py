"""Produce C code from an AST tree.

This is a very minimal version and will probably change a lot later.
"""

import collections
import glob
import os
import random

from weirdc import ast


# TODO: Do not utilize __INCLUDES__, instead use `str.format` or something like
# that.
PRELOAD = r"""
#include <stdio.h>
#include <string.h>

__INCLUDES__

static void do_the_print(struct WeirdObject *message)
{
    printf("%s", weirdstring_to_cstring(message));
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
""".replace("__INCLUDES__", 
            "\n".join(f'#include "{os.path.basename(header)}"'
                      for header in glob.glob("objects/*.h")), 
            1)


# Maps objects to functions that return the C code for their construction.
OBJECTS = {
    "Int": lambda n: f"weirdint_new({abs(n)}, {1 if n >= 0 else -1})",
    "String": lambda s: f'weirdstring_new("{s}", {len(s)})',
}

BUILTIN_NAMES = {
    'print': 'do_the_print',
    'input': 'do_the_input',
    'main': 'main'
}

declared_names = collections.ChainMap({}, BUILTIN_NAMES)


def random_name():
    return 'name' + ''.join(filter(str.isdigit, str(random.random())))


def unparse(node):
    # this is used just for parsing function definitions
    if node is None:
        return 'void'

    if isinstance(node, ast.Name):
        if node.name in OBJECTS:
            return "struct WeirdObject*"
        return declared_names[node.name]
    if isinstance(node, ast.Integer):
        return str(node.value)
    if isinstance(node, ast.String):
        # TODO: escaping and other stuff
        return OBJECTS["String"](node.value)
    if isinstance(node, ast.ExpressionStatement):
        return unparse(node.expression) + ';'
    if isinstance(node, ast.Return):
        return 'return %s;' % unparse(node.value)

    if isinstance(node, ast.Declaration):
        declared_names[node.variable] = node.variable
        if node.value is None:
            return '%s %s;' % (unparse(node.type), node.variable)
        elif node.type in OBJECTS:
            value = OBJECTS[node.type](node.value)
            return '%s %s = %s;' % (
                unparse(node.type), node.variable, value)
        return '%s %s = %s;' % (
            unparse(node.type), node.variable, unparse(node.value))

    if isinstance(node, ast.FunctionCall):
        return '%s(%s)' % (
            unparse(node.function),
            ','.join(map(unparse, node.arguments)),
        )

    if isinstance(node, ast.FunctionDef):
        # TODO: Add support for function arguments.
        assert not node.arguments   # lol
        if node.name not in declared_names:
            declared_names[node.name] = random_name()
        if node.name == "main":
            # Since we must return an int primitive from main, we treat it
            # specially.
            # TODO: Handle returns, so WeirdInt objects are converted to C int
            # primitives.
            assert node.returntype == "Int", "main return type must be int."
            return "int main(void) { %s }" % (''.join(map(unparse, node.body)))
        else:
            return '%s %s(void) { %s }' % (
                unparse(node.returntype),
                declared_names[node.name],
                ''.join(map(unparse, node.body))
            )

    raise TypeError(f"don't know how to unparse {node!r}")
