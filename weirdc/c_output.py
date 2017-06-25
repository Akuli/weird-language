"""Produce C code from an AST tree.

This is a very minimal version and will probably change a lot later.
"""

import collections
import glob
import itertools
import os
import random

from weirdc import ast


# TODO: Do not utilize __INCLUDES__, instead use `str.format` or something like
# that.
# TODO: Investigate the warnings about `do_the_print` in Valgrind.
_PRELOAD = r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

__INCLUDES__

static void do_the_print(struct WeirdObject *message)
{
    char *s = weirdstring_to_cstring(message);
    printf("%s", s);
    free(s);
}


#define MAXLEN 1000

static struct WeirdObject *do_the_input()
{
    char c, result[MAXLEN+1];    /* 1 is the 0 at the end */
    int i;

    for (i = 0; i < MAXLEN; i++) {
        c = getchar();
        if (c == EOF || c == '\n')
            break;
        result[i] = c;
    }

    /* at the end of the loop, i is equal to the length of the string. */
    /* this is automagically free-ed since it's a WeirdObject */
    return weirdstring_new(result, i);
}
#undef MAXLEN

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
random_name = ('name%d' % i for i in itertools.count(1)).__next__


def _unparse(node):
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
        # XXX: String literals that aren't assigned to a variable are never
        # freed.
        return OBJECTS["String"](node.value)
    if isinstance(node, ast.ExpressionStatement):
        return _unparse(node.expression) + ';'
    if isinstance(node, ast.Return):
        return 'return %s;' % _unparse(node.value)

    if isinstance(node, ast.Declaration):
        declared_names[node.variable] = node.variable
        if node.value is None:
            return '%s %s;' % (_unparse(node.type), node.variable)
        elif node.type in OBJECTS:
            value = OBJECTS[node.type](node.value)
            return '%s %s = %s;' % (
                _unparse(node.type), node.variable, value)
        return '%s %s = %s;' % (
            _unparse(node.type), node.variable, _unparse(node.value))

    if isinstance(node, ast.FunctionCall):
        return '%s(%s)' % (
            _unparse(node.function),
            ','.join(map(_unparse, node.arguments)),
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
            return "int main(void) { %s }" % (''.join(map(_unparse, node.body)))
        else:
            return '%s %s(void) { %s }' % (
                _unparse(node.returntype),
                declared_names[node.name],
                ''.join(map(_unparse, node.body))
            )

    if isinstance(node, ast.DecRef):
        return f"weirdobject_decref({node.name});"

    raise TypeError(f"don't know how to unparse {node!r}")


def make_c_code(nodes):
    return _PRELOAD + '\n\n'.join(map(_unparse, nodes)) + '\n'
