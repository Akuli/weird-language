import pytest

from weirdc import CompileError, Location
from weirdc.tokenizer import Token, tokenize as _iter_tokenize


def tokenize(code):
    return list(_iter_tokenize(code))


def test_integers():
    assert tokenize('1234') == [Token('INTEGER', '1234', Location(1, 0, 4))]


def test_ops():
    for op in '= ( ) { } [ ] ; , .'.split():
        assert tokenize(op) == [Token('OP', op, Location(1, 0, len(op)))]


def test_names():
    assert tokenize('hello') == [Token('NAME', 'hello', Location(1, 0, 5))]
    assert tokenize('lol123') == [Token('NAME', 'lol123', Location(1, 0, 6))]

    # i'm not sure if the tokenizer should raise an error about this,
    # but this behaviour is ok for now
    assert tokenize('123wolo') == [
        Token('INTEGER', '123', Location(1, 0, 3)),
        Token('NAME', 'wolo', Location(1, 3, 7)),
    ]


def test_strings():
    assert tokenize('"hello world"') == [
        Token('STRING', '"hello world"', Location(1, 0, 13))
    ]
    with pytest.raises(CompileError):
        tokenize('"hello \n world"')


def test_whitespace():
    assert tokenize(' \n \t \r  ') == []
    assert tokenize(' \n \t 123 \r ') == [
        Token('INTEGER', r'123', Location(2, 3, 6)),
    ]


def test_comments():
    assert tokenize('// hello\n123') == [
        Token('INTEGER', '123', Location(2, 0, 3)),
    ]
    assert tokenize('/* hello\nhello\nhello */') == []


def test_errors():
    # unfortunately none of this stuff is supported yet... :(
    with pytest.raises(CompileError):
        tokenize('+')
    with pytest.raises(CompileError):
        tokenize('¤')


_HELLO_WORLD = '''\
/* i'm not sure about the details yet, but i'm thinking of a hello world
   that looks roughly like this... */
import stdout from "io.weird";

function main() {
\tstdout.print("Hello World!");
}
'''

def test_hello_world():
    assert tokenize(_HELLO_WORLD) == [
        Token('NAME', 'import', Location(3, 0, 6)),
        Token('NAME', 'stdout', Location(3, 7, 13)),
        Token('NAME', 'from', Location(3, 14, 18)),
        Token('STRING', '"io.weird"', Location(3, 19, 29)),
        Token('OP', ';', Location(3, 29, 30)),
        Token('NAME', 'function', Location(5, 0, 8)),
        Token('NAME', 'main', Location(5, 9, 13)),
        Token('OP', '(', Location(5, 13, 14)),
        Token('OP', ')', Location(5, 14, 15)),
        Token('OP', '{', Location(5, 16, 17)),
        Token('NAME', 'stdout', Location(6, 1, 7)),
        Token('OP', '.', Location(6, 7, 8)),
        Token('NAME', 'print', Location(6, 8, 13)),
        Token('OP', '(', Location(6, 13, 14)),
        Token('STRING', '"Hello World!"', Location(6, 14, 28)),
        Token('OP', ')', Location(6, 28, 29)),
        Token('OP', ';', Location(6, 29, 30)),
        Token('OP', '}', Location(7, 0, 1)),
    ]
