# Weird language

This is a weird programming language. Currently it has a weird compiler
written in Python that generates C code and compiles that. Everything
will probably change a lot later.

Here's a Hello World from [examples/hello.weird](examples/hello.weird):

    main() -> Int {
        print("Hello World!");
        return 0;
    }

You can compile and run the example like this:

    $ python3 -m weirdc examples/hello.weird
    ...some output...
    $ ./a.out
    Hello World!
    $
