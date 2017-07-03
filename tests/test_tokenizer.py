import pytest

from weirdc import CompileError, Location
from weirdc.tokenizer import Token, tokenize as _iter_tokenize


def tokenize(code):
    return list(_iter_tokenize(code))


def test_integers():
    assert tokenize('1234') == [Token('INTEGER', '1234', Location(0, 4))]


def test_ops():
    for op in '= ( ) { } [ ] ; , .'.split():
        assert tokenize(op) == [Token('OP', op, Location(0, len(op)))]


def test_names():
    assert tokenize('hello') == [Token('NAME', 'hello', Location(0, 5))]
    assert tokenize('lol123') == [Token('NAME', 'lol123', Location(0, 6))]

    # i'm not sure if the tokenizer should raise an error about this,
    # but this behaviour is ok for now
    assert tokenize('123wolo') == [
        Token('INTEGER', '123', Location(0, 3)),
        Token('NAME', 'wolo', Location(3, 7)),
    ]


def test_strings():
    assert tokenize('"hello world"') == [
        Token('STRING', '"hello world"', Location(0, 13))
    ]
    with pytest.raises(CompileError):
        tokenize('"hello \n world"')


def test_whitespace():
    assert tokenize(' \n \t \r  ') == []
    assert tokenize(' \n \t 123 \r ') == [
        Token('INTEGER', r'123', Location(3, 6, 2)),
    ]


def test_comments():
    assert tokenize('// hello\n123') == [
        Token('INTEGER', '123', Location(0, 3, 2)),
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
        Token('NAME', 'import', Location(0, 6, 3)),
        Token('NAME', 'stdout', Location(7, 13, 3)),
        Token('NAME', 'from', Location(14, 18, 3)),
        Token('STRING', '"io.weird"', Location(19, 29, 3)),
        Token('OP', ';', Location(29, 30, 3)),
        Token('NAME', 'function', Location(0, 8, 5)),
        Token('NAME', 'main', Location(9, 13, 5)),
        Token('OP', '(', Location(13, 14, 5)),
        Token('OP', ')', Location(14, 15, 5)),
        Token('OP', '{', Location(16, 17, 5)),
        Token('NAME', 'stdout', Location(1, 7, 6)),
        Token('OP', '.', Location(7, 8, 6)),
        Token('NAME', 'print', Location(8, 13, 6)),
        Token('OP', '(', Location(13, 14, 6)),
        Token('STRING', '"Hello World!"', Location(14, 28, 6)),
        Token('OP', ')', Location(28, 29, 6)),
        Token('OP', ';', Location(29, 30, 6)),
        Token('OP', '}', Location(0, 1, 7)),
    ]
