import pytest

from weirdc import Location, tokenizer, ast, checker


def check_code(code, expected_warnings=()):
    # list() just to make sure that any tokenizing or parsing errors are
    # raised here right away
    ast_nodes = list(ast.parse(tokenizer.tokenize(code)))

    warnings = []
    try:
        # this mutates ast_nodes in-place
        checker.check(ast_nodes, warnings.append)
    finally:
        warning_infos = [(err.message,) + err.location for err in warnings]
        assert warning_infos == list(expected_warnings)
    return ast_nodes


# currently there needs to be a main() function that is magically
# executed and there are no global vars, later i'll probably make it run
# everything in the global scope so there's no need for a main()
def test_invalid_mains(error_at):
    with error_at(None, msg="there's no main() function"):
        check_code('function lel() { }')


def test_unused_vars(error_at):
    # all of these functions should be empty after checking because the
    # bad variable stuff is removed
    empty_main = ast.FunctionDef(Location(4, None), 'main', [], None, [])

    assert check_code('''\
    function main() {
        Bool lol
    }
    ''',
    [("this variable isn't used anywhere", 8, 16, 2)]) == [empty_main]

    assert check_code('''\
    function main() {
        Bool lol = TRUE
    }
    ''',
    [("this variable isn't used anywhere", 8, 16, 2)]) == [empty_main]

    assert check_code('''\
    function main() {
        Bool lol
        lol = TRUE
    }
    ''', [("this variable isn't used anywhere", 8, 16, 2)]) == [empty_main]


def test_nothing_returned(error_at):
    check_code('''\
    function returnsNothing() { }
    function main() {
        returnsNothing()
    }
    ''')
    with error_at(24, 40, 3, msg="this returns nothing"):
        check_code('''\
        function returnsNothing() { }
        function main() {
            Int thing = returnsNothing()
        }
        ''')


def test_not_function(error_at):
    with error_at(12, 19, 2, msg="this is not a function"):
        check_code('''\
        function main() {
            "hello"()
        }
        ''')

    with error_at(12, 15, 2, msg="this is not a function"):
        check_code('''\
        function main() {
            123()
        }
        ''')


def test_wrong_args(error_at):
    with error_at(12, 19, 3, msg="should be thing(Int), not thing()"):
        check_code('''\
        function thing(Int i) { }
        function main() {
            thing()
        }
        ''')

    with error_at(12, 22, 3, msg="should be thing(String), not thing(Int)"):
        check_code('''\
        function thing(String s) { }
        function main() {
            thing(123)
        }
        ''')


def test_already_defined(error_at):
    with error_at(12, 20, 3, msg="there's already a function named 'lol'"):
        check_code('''\
        function lol() { }
        function main() {
            Bool lol = TRUE
        }
        ''')

    with error_at(12, 20, 3, msg="there's already a variable named 'lol'"):
        check_code('''\
        function main() {
            Bool lol = TRUE
            Bool lol = FALSE
        }
        ''')


# undefined, undeclared and uninitialized variable tests are all here
def test_bad_variable(error_at):
    with error_at(12, 15, 2, msg="no variable named 'lol'"):
        check_code('''\
        function main() {
            lol
        }
        ''',
        [('this does nothing', 12, 15, 2)])

    assert check_code('''\
    function main() {
        Int lol = 123
        lol
    }
    ''', [
        ("this does nothing", 8, 11, 3),
        ("this variable isn't used anywhere", 8, 15, 2),
    ]) == [
        # the whole function body should be removed at this point
        ast.FunctionDef(Location(4, None), 'main', [], None, [])
    ]

    with error_at(12, 24, 2, msg=("you need to declare 'thing' first, "
                                  "e.g. 'Bool thing'")):
        check_code('''\
        function main() {
            thing = TRUE
        }
        ''')


def test_wrong_type(error_at):
    with error_at(17, 26, 2, msg="'wut' needs to be a Bool, not an Int"):
        check_code('''\
        function main() {
            Bool wut = 123
        }
        ''')


def test_function_assign(error_at):
    # TODO: this error message kind of sucks
    with error_at(12, 15, 3, msg="functions can't be changed like this"):
        check_code('''\
        function lel() { }
        function main() {
            lel = anything_really
        }
        ''')


def test_no_globals(error_at):
    with error_at(8, 15, 1, msg="only function definitions can be here"):
        check_code('''\
        Int lel
        function main() { }
        ''')


def test_nested_funcs(error_at):
    with error_at(12, 32, 2, msg="cannot define a function inside a function"):
        check_code('''\
        function main() {
            function inner() { }
        }
        ''')


def test_repeated_arguments(error_at):
    with error_at(8, None, msg="there are 2 arguments named 'lel'"):
        check_code('''\
        function thing(Int lel, Int lel) {
            whatever
        }
        function main() { }
        ''')

    with error_at(8, 77, msg="there are 5 arguments named 'lel'"):
        check_code('''\
        function thing(Int lel, String lel, Int lel, Int lel, String lel) { }
        function main() { }
        ''')


def test_not_a_type(error_at):
    with error_at(12, 15, 3, msg=("variable types need to be classes, "
                                  "not String instances")):
        check_code('''\
        function main() {
            String lel = "hello"
            lel lulz = 123
        }
        ''')

    # currently 'function lel("123" i) { }' is invalid syntax, there are
    # no user-defined global variables and all built-in variables are
    # types, so no need to validate argument types and return types


# TODO: a plain 'return' to get out of a function that returns nothing
# TODO: warn about statements after a return
# TODO: make sure that at least one return statement runs if the
#       function is supposed to return something
def test_returns(error_at):
    with error_at(12, 26, 2, msg=("this function should return an Int, "
                                  "not a String")):
        check_code('''\
        function thing() returns Int {
            return "hello"
        }
        function main() {
            thing()
        }
        ''')
