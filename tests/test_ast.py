# TODO: handle newlines specially in parentheses
# for example, python does this:
#    stuff = (
#        1, 2,
#        3, 4,
#    )

import contextlib

import pytest

from weirdc import Location, CompileError, tokenizer, ast


def get_ast(code):
    nodes = ast.parse(tokenizer.tokenize(code))
    assert nodes is iter(nodes), "ast.parse() should return an iterator"
    return list(nodes)


# TODO: use a real keyword here instead of this, currently there are
# not enough implemented keywords
@pytest.fixture
def fake_keyword():
    ast._KEYWORDS.add('fake')
    yield
    ast._KEYWORDS.remove('fake')


def test_parse_name(fake_keyword, error_at):
    assert get_ast('hello') == [ast.Name(Location(0, 5), 'hello')]

    with error_at(0, 4, msg=("fake is not a valid variable name "
                             "because it has a special meaning")):
        get_ast('fake')


def test_parse_integer():
    assert get_ast('123') == [ast.Integer(Location(0, 3), '123')]


def test_parse_string():
    assert get_ast('"hello"') == [ast.String(Location(0, 7), 'hello')]

    # TODO: do something to escapes
    assert get_ast(r'"hello \n\t"') == [
        ast.String(Location(0, 12), r'hello \n\t')]


def test_parentheses():
    # FIXME: currently the whole expression starts at column 4 and
    # that's not quite right...
    assert get_ast('(((("hello"))))') == [ast.String(Location(4, 11), 'hello')]


# FIXME: get_ast('lol()') doesn't say that a semicolon is missing
def test_function_calls():
    assert get_ast('lol()\n'
                   'lol(1)\n'
                   'lol(1, 2, 3)\n') == [
        ast.FunctionCall(
            Location(0, 5), ast.Name(Location(0, 3), 'lol'), []),
        ast.FunctionCall(
            Location(0, 6, 2),
            ast.Name(Location(0, 3, 2), 'lol'),
            [ast.Integer(Location(4, 5, 2), '1')]),
        ast.FunctionCall(
            Location(0, 12, 3),
            ast.Name(Location(0, 3, 3), 'lol'),
            [ast.Integer(Location(4, 5, 3), '1'),
             ast.Integer(Location(7, 8, 3), '2'),
             ast.Integer(Location(10, 11, 3), '3')]),
    ]


def test_trailing_commas(error_at):
    assert get_ast('lol(1,)\n'
                   'lol(1, 2, 3,)') == [
        ast.FunctionCall(
            Location(0, 7),
            ast.Name(Location(0, 3), 'lol'),
            [ast.Integer(Location(4, 5), '1')]),
        ast.FunctionCall(
            Location(0, 13, 2),
            ast.Name(Location(0, 3, 2), 'lol'),
            [ast.Integer(Location(4, 5, 2), '1'),
             ast.Integer(Location(7, 8, 2), '2'),
             ast.Integer(Location(10, 11, 2), '3')]),
    ]

    with error_at(4, 5, msg="don't put a ',' here"):
        get_ast('lol(,)')
    with error_at(4, 5, msg="don't put a ',' here"):
        get_ast('lol(,,)')
    with error_at(13, 15, msg="two ',' characters"):
        get_ast('lol(something,,)')

    # this doesn't matter much because it's unlikely that anyone will
    # accidentally put 3 commas next to each other
    with error_at(13, 15, msg="two ',' characters"):
        get_ast('lol(something,,,)')


def test_function_returns_function():
    assert get_ast('lol()()()') == [
        ast.FunctionCall(
            Location(0, 9),
            ast.FunctionCall(
                Location(0, 7),
                ast.FunctionCall(
                    Location(0, 5),
                    ast.Name(Location(0, 3), 'lol'),
                    []),
                []),
            []),
    ]

    assert get_ast('lol(1, 2)(3, 4)') == [
        ast.FunctionCall(
            Location(0, 15),
            ast.FunctionCall(
                Location(0, 9),
                ast.Name(Location(0, 3), 'lol'),
                [ast.Integer(Location(4, 5), '1'),
                 ast.Integer(Location(7, 8), '2')]),
            [ast.Integer(Location(10, 11), '3'),
             ast.Integer(Location(13, 14), '4')]),
    ]


def test_declaration_and_assignment():
    assert get_ast('Int i') == [
        ast.Declaration(
            Location(0, 5),
            ast.Name(Location(0, 3), 'Int'),
            'i'),
    ]

    assert get_ast('Int i = 123') == [
        # these overlap
        ast.Declaration(
            Location(0, 5),     # Int i
            ast.Name(Location(0, 3), 'Int'),
            'i'),
        ast.Assignment(
            Location(4, 11),    # i = 123
            ast.Name(Location(4, 5), 'i'),
            ast.Integer(Location(8, 11), '123')),
    ]

    assert get_ast('i = 123') == [
        ast.Assignment(
            Location(0, 7),
            ast.Name(Location(0, 1), 'i'),
            ast.Integer(Location(4, 7), '123')),
    ]


def test_if():
    assert get_ast('if thing { }') == [
        ast.If(
            Location(0, 12),
            ast.Name(Location(3, 8), 'thing'),
            []),
    ]

    assert get_ast('if thing {\n'
                   '\tstuff\n'
                   '\tmore_stuff\n'
                   '}') == [
        ast.If(
            Location(0, None),    # None because it's not a 1-liner
            ast.Name(Location(3, 8), 'thing'),
            [ast.Name(Location(4, 9, 2), 'stuff'),
             ast.Name(Location(4, 14, 3), 'more_stuff')])
    ]


def test_return():
    assert get_ast('return 123') == [
        ast.Return(
            Location(0, 10),
            ast.Integer(Location(7, 10), '123')),
    ]


def test_function_defs():
    assert get_ast('function thing() {\n'
                   '\tlol()\n'
                   '\tlol()\n'
                   '}') == [
        ast.FunctionDef(
            Location(0, None),
            'thing',    # function name
            [],         # arguments
            None,       # return type
            [           # body
                ast.FunctionCall(
                    Location(4, 9, 2),
                    ast.Name(Location(4, 7, 2), 'lol'),
                    []),
                ast.FunctionCall(
                    Location(4, 9, 3),
                    ast.Name(Location(4, 7, 3), 'lol'),
                    []),
            ]),
    ]

    # 0-statement 1-liner
    assert get_ast('function thing(Int i, String s) returns String { }') == [
        ast.FunctionDef(
            Location(0, 50),
            'thing',
            # arguments are (type, name) tuples
            [(ast.Name(Location(15, 18), 'Int'),
              ast.Name(Location(19, 20), 'i')),
             (ast.Name(Location(22, 28), 'String'),
              ast.Name(Location(29, 30), 's'))],
            ast.Name(Location(40, 46), 'String'),
            []),
    ]

    # 1-statement 1-liner
    # FIXME: uncomment this and fix ast.py
    #assert get_ast('function f(Int i) { f(i) }  // this is stupid') == [
    #]
