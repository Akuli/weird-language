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


# the optional fields will be filled out later
# TODO: add the name of the file that does this to this comment
# (i'm not sure about the name yet)
def _nodetype(name, required_fields, optional_fields=()):
    # this is equivalent enough to doing this:
    #    class <name>:
    #        # only allow these attributes, source is added by
    #        # _Parser.add_source()
    #        __slots__ = required_fields + optional_fields + [
    #            'start', 'end', 'source']
    #
    #        def __init__(self, <args>, start=None, end=None):
    #            for each required field:
    #                self.<field> = <value from args>
    #            for each optional field:
    #                self.<field> = None
    #            self.start = start
    #            self.end = end
    #
    #        # just for debugging
    #        def __repr__(self):
    #            # this doesn't show start, end and other optional things, most
    #            # of the time i don't care about them
    #            return '<name>(<values of the required fields>)'
    def dunder_init(self, *args, start=None, end=None):
        self.start = start
        self.end = end
        assert len(required_fields) == len(args)
        for name, value in zip(required_fields, args):
            setattr(self, name, value)
        for name in optional_fields:
            setattr(self, name, None)

    def dunder_repr(self):
        parts = [repr(getattr(self, name)) for name in required_fields]
        return 'ast.' + name + '(' + ', '.join(parts) + ')'

    # slots is defined separately because pep8 weird indent rules and
    # max line length, that's also why .split()
    return type(name, (), {
        '__init__': dunder_init,
        '__repr__': dunder_repr,
        '__slots__': (
            required_fields + list(optional_fields)
            + ['start', 'end', 'source']),
    })


Name = _nodetype('Name', ['name'])
Integer = _nodetype('Integer', ['value'])
String = _nodetype('String', ['value'])
FunctionCall = _nodetype('FunctionCall', ['function', 'args'], ['returntype'])
ExpressionStatement = _nodetype('ExpressionStatement', ['expression'])
Declaration = _nodetype('Declaration', ['type', 'name'])
Assignment = _nodetype('Assignment', ['target', 'value'])
If = _nodetype('If', ['condition', 'body'])
FunctionDef = _nodetype('FunctionDef', ['name', 'args', 'returntype', 'body'])
Return = _nodetype('Return', ['value'])
DecRef = _nodetype('DecRef', ['name'])


KEYWORDS = {'return', 'if'}


# FIXME: this should produce similar (overlapping) nodes for "Int a = 1;"
# and "Int a; a = 1;" because it's simpler and checker.py relies on it
class _Parser:

    def __init__(self, tokens, sourcelines):
        self.tokens = _HandyDandyTokenIterator(tokens)
        self.sourcelines = [None] + sourcelines     # 1-based indexing

    # calls to this in rest of the code are kind of annoying, but this
    # way making error messages is easier
    def add_source(self, node):
        if node.start is None or node.end is None:
            node.source = None
        else:
            assert node.start < node.end, "the node must start before it ends"

            startline, startcol = node.start
            endline, endcol = node.end
            if startline == endline:
                node.source = self.sourcelines[startline][startcol:endcol]
            else:
                first = self.sourcelines[startline][startcol:]
                rest = self.sourcelines[startline+1:endline]
                last = self.sourcelines[endline][:endcol]
                node.source = '\n'.join([first] + rest + [last])

        return node

    def parse_name(self, check_for_keywords=True):
        # thing
        token = self.tokens.check_and_pop('NAME')
        if check_for_keywords:
            assert token.value not in KEYWORDS, token.value
        return self.add_source(Name(
            token.value, start=token.start, end=token.end))

    def parse_integer(self):
        # 3735928559
        token = self.tokens.check_and_pop('INTEGER')
        return self.add_source(Integer(
            int(token.value), start=token.start, end=token.end))

    def parse_string(self):
        # "hello world"
        # TODO: "hello \"world\" ${some code}"
        token = self.tokens.check_and_pop('STRING')
        return self.add_source(String(
            token.value[1:-1], start=token.start, end=token.end))

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
            args, last_token = self._parse_comma_list()
            result = self.add_source(FunctionCall(
                result, args, start=result.start, end=last_token.end))

        return result

    # rest of these methods are for parsing statements

    def parse_expression_statement(self):
        # expression;
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return self.add_source(ExpressionStatement(
            value, start=value.start, end=semicolon.end))

    def assignment(self):
        # thing = value
        # TODO: thing's stuff = value
        target = self.parse_name()
        self.tokens.check_and_pop('OP', '=')
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return self.add_source(Assignment(
            target, value, start=target.start, end=semicolon.end))

    def parse_if(self):
        the_if = self.tokens.check_and_pop('NAME', 'if')
        condition = self.parse_expression()
        self.tokens.check_and_pop('OP', '{')

        body = []
        while self.tokens.coming_up().info != ('OP', '}'):
            body.extend(self.parse_statement())

        closing_brace = self.tokens.check_and_pop('OP', '}')
        return self.add_source(If(
            condition, body, start=the_if.start, end=closing_brace.end))

    def _type_and_name(self):
        # Int a;
        # this returns (typenode, name_string)
        typenode = self.parse_name()   # TODO: module's Thing
        name = self.parse_name()
        return (typenode, name.name)

    # RETURNS AN ITERABLE
    def parse_declaration(self):
        # Int thing;
        # Int thing = expr;    // equivalent to "Int thing; thing = expr;" [*]
        # TODO: module's Thingy thing;
        #
        # [*] produces overlapping Declaration and Assignment nodes,
        #     that's why this returns a list of nodes
        datatype = self.parse_name()   # TODO: module's Thing
        variable = self.parse_name()

        third_thing = self.tokens.check_and_pop('OP')
        if third_thing.value == ';':
            return [self.add_source(Declaration(
                datatype, variable.name,
                start=datatype.start, end=third_thing.end))]

        assert third_thing.value == '='
        initial_value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return map(self.add_source, [
            Declaration(datatype, variable.name,
                        start=datatype.start, end=variable.end),
            Assignment(variable, initial_value,
                       start=variable.start, end=semicolon.end),
        ])

    def parse_return(self):
        the_return = self.tokens.check_and_pop('NAME', 'return')
        value = self.parse_expression()
        semicolon = self.tokens.check_and_pop('OP', ';')
        return self.add_source(Return(
            value, start=the_return.start, end=semicolon.end))

    # RETURNS AN ITERABLE
    def parse_statement(self):
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
            if after_name.info == ('OP', '='):
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

        if self.tokens.coming_up().info == ('NAME', 'returns'):
            self.tokens.pop()
            returntype = self.parse_name()
        else:
            returntype = None

        before_body = self.tokens.check_and_pop('OP')
        body = []
        while self.tokens.coming_up().info != ('OP', '}'):
            body.extend(self.parse_statement())
        closing_brace = self.tokens.check_and_pop('OP', '}')

        return self.add_source(FunctionDef(
            name.name, args, returntype, body,
            start=function_keyword.start, end=closing_brace.end))

    def parse_file(self):
        while True:
            try:
                self.tokens.coming_up(1)
            except EOFError:
                break

            yield from self.parse_statement()


def parse(tokens, sourcelines):
    r"""Convert an iterable of tokens to AST nodes.

    The sourcelines argument should be a list of the lines of code that
    the tokens come from, without trailing \n's. The .splitlines()
    string method is handy for this.
    """
    parser = _Parser(tokens, sourcelines)
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
    for node in parse(tokenizer.tokenize(code), code.splitlines()):
        print(node)
