"""The abstract syntax tree."""

import collections


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
        assert self.coming_up().kind == kind, self.coming_up()
        if value is not None:
            assert self.coming_up().value == value, self.coming_up()
        return self.pop()


def _nodetype(name, fields):
    return collections.namedtuple(name, ['start', 'end'] + fields)


Name = _nodetype('Name', ['name'])
Integer = _nodetype('Integer', ['value'])
String = _nodetype('String', ['value'])
FunctionCall = _nodetype('FunctionCall', ['function', 'arguments'])
ExpressionStatement = _nodetype('ExpressionStatement', ['expression'])
Declaration = _nodetype('Declaration', ['type', 'variable', 'value'])
Assignment = _nodetype('Assignment', ['variable', 'value'])
If = _nodetype('If', ['condition', 'body'])
FunctionDef = _nodetype('FunctionDef', [
    'name', 'arguments', 'returntype', 'body'])
Return = _nodetype('Return', ['value'])
DecRef = collections.namedtuple("DecRef", ["name"])


KEYWORDS = {'return', 'if'}


class _Parser:

    def __init__(self, tokens):
        self.tokens = _HandyDandyTokenIterator(tokens)

    def parse_name(self, check_for_keywords=True):
        # thing
        token = self.tokens.check_and_pop('NAME')
        if check_for_keywords:
            assert token.value not in KEYWORDS, token.value
        return Name(token.start, token.end, token.value)

    def parse_integer(self):
        # 3735928559
        token = self.tokens.check_and_pop('INTEGER')
        return Integer(token.start, token.end, int(token.value))

    def parse_string(self):
        # "hello world"
        # TODO: "hello \"world\" ${some code}"
        token = self.tokens.check_and_pop('STRING')
        return String(token.start, token.end, token.value[1:-1])

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
        if self.tokens.coming_up().info == ('OP', stop):
            # empty list
            last_token = self.tokens.pop()
        else:
            while True:
                elements.append(parsemethod())
                if self.tokens.coming_up().info == ('OP', stop):
                    last_token = self.tokens.pop()
                    break

                self.tokens.check_and_pop('OP', ',')
                if self.tokens.coming_up().info == ('OP', stop):
                    last_token = self.tokens.pop()
                    break

        return (elements, last_token)

    def parse_expression(self):
        coming_up = self.tokens.coming_up()
        next_kind = coming_up.kind
        if next_kind == 'NAME':
            # hello
            result = self.parse_name()
        elif next_kind == 'STRING':
            # "hello"
            result = self.parse_string()
        elif next_kind == 'INTEGER':
            # 123
            result = self.parse_integer()
        else:
            raise ValueError(f"Invalid token: {coming_up!r}")

        # check for function calls, this is a while loop to allow nested
        # function calls like thing()()()
        while True:
            next_token = self.tokens.coming_up()
            if next_token.kind != 'OP' or next_token.value != '(':
                break

            openparen = self.tokens.check_and_pop('OP', '(')
            arguments, last_token = self._parse_comma_list()
            result = FunctionCall(result.start, last_token.end,
                                  result, arguments)

        return result

    # rest of these methods are for parsing statements

    def parse_expression_statement(self):
        # expression;
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return ExpressionStatement(value.start, semicolon.end, value)

    def assignment(self):
        # thing = value
        # TODO: thing's stuff = value
        variable = self.parse_name()
        self.tokens.check_and_pop('OP', '=')
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return Assignment(variable.start, semicolon.end, variable, value)

    def parse_if(self):
        the_if = self.tokens.check_and_pop('NAME', 'if')
        condition = self.parse_expression()
        self.tokens.check_and_pop('OP', '{')

        body = []
        while self.tokens.coming_up().info != ('OP', '}'):
            body.append(self.parse_statement())

        closing_brace = self.tokens.check_and_pop('OP', '}')
        return If(the_if.start, closing_brace.end, condition, body)

    def _type_and_name(self):
        # Int a
        # return (typenode, name_string)
        typenode = self.parse_name()
        name = self.parse_name()
        return (typenode, name.name)

    def parse_declaration(self):
        # Int thing;
        # Int thing = expression;
        # TODO: module's Thingy thing;
        datatype, variable_name = self._type_and_name()

        third_thing = self.tokens.check_and_pop('OP')
        if third_thing.value == ';':
            semicolon = third_thing
            initial_value = None
        else:
            initial_value = self.parse_expression()
            semicolon = self.tokens.check_and_pop('OP', ';')
        return Declaration(datatype.start, third_thing.end,
                           datatype, variable_name, initial_value)

    def parse_return(self):
        the_return = self.tokens.check_and_pop('NAME', 'return')
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return Return(the_return.start, semicolon.end, value)

    def parse_statement(self):
        # coming_up(1) and coming_up(2) work because there's always a
        # semicolon and at least something before it
        if self.tokens.coming_up(1).kind == 'NAME':
            if self.tokens.coming_up(1).value == 'return':
                return self.parse_return()
            if self.tokens.coming_up(1).value == 'if':
                return self.parse_if()
            if self.tokens.coming_up(1).value == 'function':
                return self.parse_function_def()

            after_name = self.tokens.coming_up(2)
            if after_name.info == ('OP', '='):
                return self.assignment()
            if after_name.kind == 'NAME':
                return self.parse_declaration()

        return self.parse_expression_statement()

    def parse_function_def(self):
        # function main() { ... }
        # function thing() returns Int { ... }
        function_keyword = self.tokens.check_and_pop('NAME', 'function')
        name = self.parse_name()
        self.tokens.check_and_pop('OP', '(')
        arguments, junk = self._parse_comma_list(parsemethod=self._type_and_name)

        if self.tokens.coming_up().info == ('NAME', 'returns'):
            self.tokens.pop()
            returntype = self.parse_name()
        else:
            returntype = None

        before_body = self.tokens.check_and_pop('OP')
        body = []
        while self.tokens.coming_up().info != ('OP', '}'):
            body.append(self.parse_statement())
        closing_brace = self.tokens.check_and_pop('OP', '}')

        return FunctionDef(function_keyword.start, closing_brace.end,
                           name.name, arguments, returntype, body)

    def parse_file(self):
        while True:
            try:
                self.tokens.coming_up(1)
            except EOFError:
                break

            yield self.parse_statement()


def parse(tokens):
    parser = _Parser(tokens)
    return parser.parse_file()


if __name__ == '__main__':
    from weirdc import tokenizer
    code = '''\
    Int GLOBAL;
    GLOBAL = 123;

    function lel() {
        // this does nothing
    }

    function main(String s) returns Int {
        Int a = 1;
        if a {
            print("WOLO WOLO");
        }
        return 123;
    }
    '''
    for node in parse(tokenizer.tokenize(code)):
        print(node)
