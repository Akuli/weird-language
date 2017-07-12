"""The abstract syntax tree elements and parser."""

import collections
import contextlib
import functools

from weirdc import CompileError, Location, utils


def _node(name, fields):
    return utils.miniclass(__name__, name, ['location'] + fields)

# expressions that can also be statements
# only FunctionCall makes sense as a statement, so other statements
# are removed in checker.py
Name = _node('Name', ['name'])
Integer = _node('Integer', ['value'])
String = _node('String', ['value'])
FunctionCall = _node('FunctionCall', ['function', 'args'])

# these aren't valid expressions
Declaration = _node('Declaration', ['type', 'name'])
Assignment = _node('Assignment', ['target', 'value'])
If = _node('If', ['condition', 'body'])
Return = _node('Return', ['value'])
FunctionDef = _node('FunctionDef', ['name', 'args', 'returntype', 'body'])

# these doesn't have locations, so we can't use _node()
# TODO: add these everywhere in decreffer.py
IncRef = utils.miniclass(__name__, 'IncRef', ['varname'])
DecRef = utils.miniclass(__name__, 'DecRef', ['varname'])


# this kind of abuses EOFError... feels good, i'm evil >:D MUHAHAHAA!!!
class _HandyDandyTokenIterator:

    def __init__(self, iterable):
        self._iterator = iter(iterable)
        self._coming_up_stack = collections.deque()

        # this is only used in _Parser.parse_file()
        self.last_popped = None

    def pop(self):
        try:
            result = self._coming_up_stack.pop()
        except IndexError:
            try:
                result = next(self._iterator)
            except StopIteration:
                raise EOFError

        self.last_popped = result
        return result

    def coming_up(self, n=1):
        while len(self._coming_up_stack) < n:
            try:
                # pop() doesn't work if there's something on _coming_up_stack
                self._coming_up_stack.appendleft(next(self._iterator))
            except StopIteration as e:
                raise EOFError from e
        return self._coming_up_stack[-n]

    # this must be "check and pop", not "pop and check"
    # that way this can be used in try/except
    def check_and_pop(self, kind, value=None):
        if value is not None and self.coming_up().value != value:
            raise CompileError("this should be '%s'" % value,
                               self.coming_up().location)

        if self.coming_up().kind != kind:
            raise CompileError(
                "this should be %s" % utils.add_article(kind.lower()),
                self.coming_up().location)

        return self.pop()

    # this skips everything except the first NEWLINE when there are
    # multiple NEWLINE tokens with nothing in between
    def pop_newline(self):
        try:
            self.check_and_pop('NEWLINE')
            while self.coming_up().kind == 'NEWLINE':
                self.pop()
        except EOFError:
            # no trailing newline at the end of file
            pass


_KEYWORDS = {'return', 'if'}


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

    def parse_parentheses(self):
        # ( expr )
        # parentheses don't have a node type because they just change
        # the evaluation order
        self.tokens.check_and_pop('OP', '(')
        content = self.parse_expression()
        self.tokens.check_and_pop('OP', ')')
        return content

    # return (element_list, stop_token)
    def _parse_comma_list(self, start='(', stop=')', parsemethod=None):
        # ( )
        # ( element )
        # ( element , )
        # ( element , element )
        # ( element , element , )
        # ...
        if parsemethod is None:
            parsemethod = self.parse_expression

        start_token = self.tokens.check_and_pop('OP', start)
        if self.tokens.coming_up().startswith(['OP', stop]):
            # empty list
            return ([], self.tokens.pop())

        elements = []
        while True:
            if self.tokens.coming_up().startswith(['OP', ',']):
                raise CompileError("don't put a ',' here",
                                   self.tokens.coming_up().location)
            elements.append(parsemethod())

            if self.tokens.coming_up().startswith(['OP', stop]):
                return (elements, self.tokens.pop())

            comma = self.tokens.check_and_pop('OP', ',')
            if self.tokens.coming_up().startswith(['OP', ',']):
                raise CompileError(
                    "two ',' characters",
                    Location.between(comma, self.tokens.coming_up()))

            if self.tokens.coming_up().startswith(['OP', stop]):
                return (elements, self.tokens.pop())

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
        elif coming_up.startswith(['OP', '(']):
            result = self.parse_parentheses()
        else:
            raise CompileError(
                "this should be variable name, string, integer or '('",
                coming_up.location)

        # check for function calls, this is a while loop to allow
        # function calls like thing()()()
        while self.tokens.coming_up().startswith(['OP', '(']):
            args, stop_token = self._parse_comma_list('(', ')')
            result = FunctionCall(Location.between(result, stop_token),
                                  result, args)

        return result

    # rest of these methods are for parsing statements

    def parse_expression_statement(self):
        # expression and newline
        value = self.parse_expression()
        self.tokens.pop_newline()
        return value

    def assignment(self):
        # thing = value
        # TODO: thing's stuff = value
        target = self.parse_name()
        self.tokens.check_and_pop('OP', '=')
        value = self.parse_expression()
        self.tokens.pop_newline()
        return Assignment(Location.between(target, value), target, value)

    def parse_if(self):
        # if cond { statements }
        the_if = self.tokens.check_and_pop('NAME', 'if')
        condition = self.parse_expression()

        self.tokens.check_and_pop('OP', '{')
        body = []

        # allow "if thing { }" without a newline
        if not self.tokens.coming_up().startswith(['OP', '}']):
            self.tokens.pop_newline()
            while not self.tokens.coming_up().startswith(['OP', '}']):
                body.extend(self.parse_statement())
        closing_brace = self.tokens.check_and_pop('OP', '}')

        self.tokens.pop_newline()
        return If(Location.between(the_if, closing_brace), condition, body)

    def _type_and_name(self):
        # Int a
        # this returns (typenode, name_string)
        typenode = self.parse_name()   # TODO: module's Thing
        name = self.parse_name()
        return (typenode, name)

    def parse_declaration(self) -> list:
        # Int thing
        # Int thing = expr
        # TODO: module.Thingy thing
        #
        # "Int thing = expr" produces overlapping Declaration and
        # Assignment nodes, that's why this returns a list of nodes
        datatype = self.parse_name()   # TODO: module's Thing
        variable = self.parse_name()

        if self.tokens.coming_up().kind == 'NEWLINE':
            self.tokens.pop_newline()
            return [Declaration(Location.between(datatype, variable),
                                datatype, variable.name)]

        self.tokens.check_and_pop('OP', '=')
        initial_value = self.parse_expression()
        self.tokens.pop_newline()
        return [Declaration(Location.between(datatype, variable),
                            datatype, variable.name),
                Assignment(Location.between(variable, initial_value),
                           variable, initial_value)]

    def parse_return(self):
        the_return = self.tokens.check_and_pop('NAME', 'return')
        value = self.parse_expression()
        self.tokens.pop_newline()
        return Return(Location.between(the_return, value), value)

    def parse_statement(self) -> list:
        # coming_up(1) and coming_up(2) work because there's always a
        # newline and at least something before it
        if self.tokens.coming_up(1).kind == 'NAME':
            if self.tokens.coming_up(1).value == 'return':
                return [self.parse_return()]
            if self.tokens.coming_up(1).value == 'if':
                return [self.parse_if()]
            if self.tokens.coming_up(1).value == 'function':
                return [self.parse_function_def()]

            try:
                after_name = self.tokens.coming_up(2)
            except EOFError:
                return [self.parse_expression_statement()]

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
        args, junk = self._parse_comma_list(
            '(', ')', parsemethod=self._type_and_name)

        if self.tokens.coming_up().startswith(['NAME', 'returns']):
            self.tokens.pop()
            returntype = self.parse_name()
        else:
            returntype = None

        opening_brace = self.tokens.check_and_pop('OP', '{')
        if self.tokens.coming_up().kind == 'NEWLINE':
            self.tokens.pop_newline()
        body = []
        while not self.tokens.coming_up().startswith(['OP', '}']):
            body.extend(self.parse_statement())
        closing_brace = self.tokens.check_and_pop('OP', '}')
        self.tokens.pop_newline()

        return FunctionDef(Location.between(function_keyword, closing_brace),
                           name.name, args, returntype, body)

    def parse_file(self):
        while True:
            try:
                self.tokens.coming_up(1)
            except EOFError:
                break

            try:
                yield from self.parse_statement()
            except EOFError:
                # underline 3 blanks after last token
                last_location = self.tokens.last_popped.location
                mark_here = Location(last_location.end, last_location.end+3,
                                     last_location.lineno)

                # python abbreviates this as EOF and beginners don't
                # understand it, but i guess this one is good enough
                raise CompileError("unexpected end of file", mark_here)


def parse(tokens):
    """Convert an iterable of tokens to AST nodes.

    This returns an iterator.
    """
    parser = _Parser(tokens)
    return parser.parse_file()
