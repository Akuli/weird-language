import collections
import string as string_module


def add_article(string):
    # if the string is prefixed with e.g. quotes, handle that
    first_letter = string.lstrip(string_module.punctuation)[0]
    article = 'an' if first_letter in 'AEIOUYaeiouy' else 'a'
    return article + ' ' + string


def miniclass(modulename, name, fields, *, inherit=object, default_attrs=None):
    """Create a small class, a lot like :func:`collections.namedtuple`.

    Unlike namedtuples, instances of the returned classes are mutable
    and not iterable.

    The ``modulename`` should be the name of the module that called
    this for the ``__repr__``. Only the last part of it will be used, so
    ``weirdc.utils`` turns into just ``utils``. 

    If *default_attrs* is specified, it should be a ``{name: value}``
    dictionary of attributes. They can be customized with keyword
    arguments.

    You can also set *inherit* to another class from this function.
    The inherited fields need to be given as initialization arguments
    before the fields specific to the new class.
    """
    modulename = modulename.split('.')[-1]

    # __slots__ can be a list, but mutating it afterwards doesn't change
    # anything so it just confuses stuff
    fields = tuple(fields)
    if default_attrs is None:
        default_attrs = {}

    if inherit is object:
        all_fields = fields
    else:
        all_fields = tuple(inherit.__slots__) + fields

    def dunder_init(self, *args, **kwargs):
        assert len(args) == len(all_fields)
        assert set(kwargs.keys()).issubset(default_attrs.keys())

        for name, value in zip(all_fields, args):
            setattr(self, name, value)
        for name, value in collections.ChainMap(kwargs, default_attrs).items():
            setattr(self, name, value)

    # not really necessary, but makes debugging a lot easier
    def dunder_repr(self):
        values = [repr(getattr(self, name)) for name in all_fields]
        return '%s.%s(%s)' % (modulename, name, ', '.join(values))

    def dunder_eq(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        for name in all_fields:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    return type(name, (inherit,), {
        '__slots__': fields + tuple(default_attrs),
        '__init__': dunder_init,
        '__repr__': dunder_repr,
        '__eq__': dunder_eq,
        # __ne__ works automagically
    })
