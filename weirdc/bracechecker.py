"""Check for unbalanced { } and ( ).

Originally weirdc.test_ast checked the braces, but this makes it a
bit simpler.
"""

from weirdc import CompileError

_opening2closing = {'{': '}', '(': ')'}
_closing2opening = {close: open_ for open_, close in _opening2closing.items()}


def check(tokens):
    brace_stack = []
    for token in tokens:
        if token.kind != 'OP':
            continue

        if token.value in _opening2closing:
            brace_stack.append(token)
        elif token.value in _closing2opening:
            opening = _closing2opening[token.value]
            if not brace_stack:
                raise CompileError("missing '%s'" % opening, token.location)

            open_token = brace_stack.pop()
            if open_token.value != opening:
                raise CompileError(
                    "should be '%s'" % _opening2closing[open_token.value],
                    token.location)

    if brace_stack:
        # i'm not sure if complaining about the outermost brace is the
        # right thing to do, but pypy does it...
        #
        # $ cat > test.py
        # (        # one
        #     (    # two
        #   )      # three
        # ^D
        # $ bin/pypy3 test.py
        # File "test.py", line 1
        #     (        # one
        #     ^
        # SyntaxError: parenthesis is never closed
        outermost = brace_stack[0]
        raise CompileError(
            "missing '%s'" % _opening2closing[brace_stack[0].value],
            brace_stack[0].location)
