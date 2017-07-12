import contextlib

import pytest

from weirdc import Location, CompileError, tokenizer, bracechecker


def check(code):
    # list() makes sure that errors are raised before passing to
    # bracechecker.check
    tokens = list(tokenizer.tokenize(code))
    bracechecker.check(tokens)


def test_the_brace_checker_like_everything_about_it(error_at):
    with error_at(0, 1, msg="missing '}'"):
        check('{ {')

    with error_at(4, 5, msg="missing '{'"):
        check('{ } }')

    with error_at(2, 3, msg="should be '}'"):
        check('{ )')
