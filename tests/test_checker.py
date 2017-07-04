import pytest

from weirdc import CompileError, tokenizer, ast, checker


def check_code(code):
    # this doesn't dedent the code because that way i can use my
    # editor's column counter without having to do math
    code = code.lstrip('\n')

    # list() just to make sure that any tokenizing or parsing errors are
    # thrown here right away
    ast_nodes = list(ast.parse(tokenizer.tokenize(code)))
    checker.check(ast_nodes)


# currently there needs to be a main() function that is magically
# executed and there are no global vars, later i'll probably make it run
# everything in the global scope so there's no need for a main()
def test_invalid_mains():
    # utils.error_at doesn't have anything for this because these
    # location=None cases are rare
    with pytest.raises(CompileError) as err:
        check_code('function lel() { }')
    assert err.value.location is None
    assert err.value.message == "there's no main() function"


def test_unused_vars(utils):
    with utils.error_at(12, 20, 2, msg="this variable isn't used anywhere"):
        check_code('''
        function main() {
            Int lol;
        }
        ''')

    with utils.error_at(12, 19, 2, msg="this variable isn't used anywhere"):
        check_code('''
        function main() {
            Int lol = 123;
        }
        ''')

    with utils.error_at(12, 20, 2, msg="this variable isn't used anywhere"):
        check_code('''
        function main() {
            Int lol;
            lol = 123;
        }
        ''')


def test_nothing_returned(utils):
    check_code('''
    function returnsNothing() { }
    function main() { returnsNothing(); }
    ''')
    with utils.error_at(38, 54, 2, msg="this returns nothing"):
        check_code('''
        function returnsNothing() { }
        function main() { Int thing = returnsNothing(); }
        ''')


def test_not_function(utils):
    with utils.error_at(26, 33, msg="this is not a function"):
        check_code('''
        function main() { "hello"(); }
        ''')

    with utils.error_at(26, 29, msg="this is not a function"):
        check_code('''
        function main() { 123(); }
        ''')


def test_wrong_args(utils):
    with utils.error_at(26, 33, 2, msg="should be thing(Int), not thing()"):
        check_code('''
        function thing(Int i) { }
        function main() { thing(); }
        ''')

    with utils.error_at(26, 36, 2,
                        msg="should be thing(String), not thing(Int)"):
        check_code('''
        function thing(String s) { }
        function main() { thing(123); }
        ''')


def test_already_defined(utils):
    with utils.error_at(26, 33, 2,
                        msg="there's already a function named 'lol'"):
        check_code('''
        function lol() { }
        function main() { Int lol = 123; }
        ''')

    with utils.error_at(12, 22, 3,
                        msg="there's already a variable named 'lol'"):
        check_code('''
        function main() {
            Int lol = 123;
            String lol = "well lulz";
        }
        ''')


# undefined, undeclared and uninitialized variable tests are all here
def test_bad_variable(utils):
    with utils.error_at(26, 29, msg="no variable named 'lol'"):
        check_code('''
        function main() { lol; }
        ''')

    with utils.error_at(12, 15, 3,
                        msg="variable 'lol' might not have a value yet"):
        check_code('''
        function main() {
            Int lol;
            lol;
        }
        ''')

    with utils.error_at(12, 24, 2, msg=("you need to declare 'thing' first, "
                                        'e.g. "Int thing;"')):
        check_code('''
        function main() {
            thing = 123;
        }
        ''')


def test_wrong_type(utils):
    with utils.error_at(30, 50, msg="'wut' needs to be an Int, not a String"):
        check_code('''
        function main() { Int wut = "this is lol"; }
        ''')


def test_function_assign(utils):
    with utils.error_at(26, 29, 2, msg="functions can't be changed like this"):
        check_code('''
        function lel() { }
        function main() { lel = anything_really; }
        ''')


def test_no_globals(utils):
    with utils.error_at(8, 16, 1, msg="only function definitions can be here"):
        check_code('''
        Int lel;
        function main() { }
        ''')
