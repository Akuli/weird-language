"""The abstract syntax tree."""

import collections
import functools

from weirdc import CompileError, Location, utils


class _HandyDandyTokenIterator:

    def __init__(self, iterable):
        self._iterator = iter(iterable)
        self._coming_up_stack = collections.deque()

    def pop(self):
        try:
            return self._coming_up_stack.pop()
        except IndexError:
            return next(self._iterator)

    def coming_up(self, n=1):
        while len(self._coming_up_stack) < n:
            try:
                self._coming_up_stack.appendleft(next(self._iterator))
            except StopIteration as e:
                raise EOFError from e
        return self._coming_up_stack[-n]

    def something_coming_up(self):
        if not self._coming_up_stack:
            try:
                self._coming_up_stack.appendleft(next(self._iterator))
            except StopIteration:
                return False
        return True

    # this must be "check and pop", not "pop and check"
    # that way this can be used in try/except
    def check_and_pop(self, kind, value=None):
        if value is not None and self.coming_up().value != value:
            # TODO: currently forgetting a semicolon like this...
            #     function something() { lel() }
            # ...results in an error message which says that the '}'
            # should be ';'
            raise CompileError("this should be '%s'" % value,
                               self.coming_up().location)

        if self.coming_up().kind != kind:
            raise CompileError(
                "this should be %s" % weirdc.utils.add_article(kind.lower()),
                self.coming_up().location)

        return self.pop()


def _node(name, fields):
    return utils.miniclass(__name__, name, ['location'] + fields)

Name = _node('Name', ['name'])
Integer = _node('Integer', ['value'])
String = _node('String', ['value'])
FunctionCall = _node('FunctionCall', ['function', 'args'])
ExpressionStatement = _node('ExpressionStatement', ['expression'])
Declaration = _node('Declaration', ['type', 'name'])
Assignment = _node('Assignment', ['target', 'value'])
If = _node('If', ['condition', 'body'])
FunctionDef = _node('FunctionDef', ['name', 'args', 'returntype', 'body'])
Return = _node('Return', ['value'])

_KEYWORDS = {'return', 'if'}


# FIXME: this should produce similar (overlapping) nodes for "Int a = 1;"
# and "Int a; a = 1;" because it's simpler and checker.py relies on it
class _Parser:

    def __init__(self, tokens):
        self.tokens = _HandyDandyTokenIterator(tokens)

    def parse_name(self, check_for_keywords=True):
        # thing
        token = self.tokens.check_and_pop('NAME')
        if check_for_keywords and token.value in _KEYWORDS:
            raise CompileError(
                "%s is not a valid variable name because it has a "
                "special meaning" % token.value,
                token.location)
        return Name(token.location, token.value)

    def parse_integer(self):
        # 3735928559
        token = self.tokens.check_and_pop('INTEGER')
        return Integer(token.location, token.value)

    def parse_string(self):
        # "hello world"
        # TODO: "hello \"world\" ${some code}"
        token = self.tokens.check_and_pop('STRING')
        return String(token.location, token.value[1:-1])

    def _parse_comma_list(self, stop=')', parsemethod=None):
        # )
        # element )
        # element , )
        # element , element )
        # element , element , )
        # ...
        if parsemethod is None:
            parsemethod = self.parse_expression

        elements = []
        if self.tokens.coming_up().startswith(['OP', stop]):
            # empty list
            last_token = self.tokens.pop()
        else:
            while True:
                if self.tokens.coming_up().startswith(['OP', ',']):
                    raise CompileError("don't put a ',' here",
                                       self.tokens.coming_up().location)
                elements.append(parsemethod())
                if self.tokens.coming_up().startswith(['OP', stop]):
                    last_token = self.tokens.pop()
                    break

                comma = self.tokens.check_and_pop('OP', ',')
                if self.tokens.coming_up().startswith(['OP', ',']):
                    raise CompileError(
                        "two ',' characters",
                        Location.between(comma, self.tokens.coming_up()))

                if self.tokens.coming_up().startswith(['OP', stop]):
                    last_token = self.tokens.pop()
                    break

        return (elements, last_token)

    def parse_expression(self):
        coming_up = self.tokens.coming_up()
        if coming_up.kind == 'NAME':
            # hello
            result = self.parse_name()
        elif coming_up.kind == 'STRING':
            # "hello"
            result = self.parse_string()
        elif coming_up.kind == 'INTEGER':
            # 123
            result = self.parse_integer()
        else:
            raise CompileError("this should be a name, string or integer",
                               coming_up.location)

        # check for function calls, this is a while loop to allow
        # function calls like thing()()()
        while self.tokens.coming_up().startswith(['OP', '(']):
            self.tokens.check_and_pop('OP', '(')
            args, last_token = self._parse_comma_list()
            result = FunctionCall(Location.between(result, last_token),
                                  result, args)

        return result

    # rest of these methods are for parsing statements

    def parse_expression_statement(self):
        # expression;
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return ExpressionStatement(Location.between(value, semicolon), value)

    def assignment(self):
        # thing = value
        # TODO: thing's stuff = value
        target = self.parse_name()
        self.tokens.check_and_pop('OP', '=')
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return Assignment(Location.between(target, semicolon), target, value)

    # TODO: add parentheses around the condition
    #   old:    if stuff { thing; }
    #   new:    if (stuff) { thing; }
    #
    # this way it's easier to get started with another programming
    # language after learning this language
    #
    # parsing parentheses in general needs to be implemented, currently
    # '(thing());' is not valid syntax
    def parse_if(self):
        the_if = self.tokens.check_and_pop('NAME', 'if')
        condition = self.parse_expression()
        self.tokens.check_and_pop('OP', '{')

        body = []
        while not self.tokens.coming_up().startswith(['OP', '}']):
            body.extend(self.parse_statement())

        closing_brace = self.tokens.check_and_pop('OP', '}')
        return If(Location.between(the_if, closing_brace), condition, body)

    def _type_and_name(self):
        # Int a;
        # this returns (typenode, name_string)
        typenode = self.parse_name()   # TODO: module's Thing
        name = self.parse_name()
        return (typenode, name)

    def parse_declaration(self) -> list:
        # Int thing;
        # Int thing = expr;
        # TODO: module.Thingy thing;
        #
        # "Int thing = expr;" produces overlapping Declaration and
        # Assignment nodes, that's why this returns a list of nodes
        datatype = self.parse_name()   # TODO: module's Thing
        variable = self.parse_name()

        third_thing = self.tokens.check_and_pop('OP')
        if third_thing.value == ';':
            return [Declaration(Location.between(datatype, third_thing),
                                datatype, variable.name)]

        assert third_thing.value == '='
        initial_value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return [Declaration(Location.between(datatype, variable),
                            datatype, variable.name),
                Assignment(Location.between(variable, semicolon),
                           variable, initial_value)]

    def parse_return(self):
        the_return = self.tokens.check_and_pop('NAME', 'return')
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return Return(Location.between(the_return, semicolon), value)

    def parse_statement(self) -> list:
        # coming_up(1) and coming_up(2) work because there's always a
        # semicolon and at least something before it
        if self.tokens.coming_up(1).kind == 'NAME':
            if self.tokens.coming_up(1).value == 'return':
                return [self.parse_return()]
            if self.tokens.coming_up(1).value == 'if':
                return [self.parse_if()]
            if self.tokens.coming_up(1).value == 'function':
                return [self.parse_function_def()]

            after_name = self.tokens.coming_up(2)
            if after_name.startswith(['OP', '=']):
                return [self.assignment()]
            if after_name.kind == 'NAME':
                return self.parse_declaration()

        return [self.parse_expression_statement()]

    def parse_function_def(self):
        # function main() { ... }
        # function thing() returns Int { ... }
        function_keyword = self.tokens.check_and_pop('NAME', 'function')
        name = self.parse_name()
        self.tokens.check_and_pop('OP', '(')
        args, junk = self._parse_comma_list(parsemethod=self._type_and_name)

        if self.tokens.coming_up().startswith(['NAME', 'returns']):
            self.tokens.pop()
            returntype = self.parse_name()
        else:
            returntype = None

        self.tokens.check_and_pop('OP')
        body = []
        while not self.tokens.coming_up().startswith(['OP', '}']):
            body.extend(self.parse_statement())
        closing_brace = self.tokens.check_and_pop('OP', '}')

        return FunctionDef(Location.between(function_keyword, closing_brace),
                           name.name, args, returntype, body)

    def parse_file(self):
        while True:
            try:
                self.tokens.coming_up(1)
            except EOFError:
                break

            yield from self.parse_statement()


def parse(tokens):
    """Convert an iterable of tokens to AST nodes.

    This returns an iterator.
    """
    parser = _Parser(tokens)
    return parser.parse_file()
