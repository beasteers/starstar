import sys
import ast
import inspect
import fnmatch
from types import GeneratorType

import starstar
from . import core
from .core import *



def main(func=None, doc=None, format=None, args=None, print_result=True, 
         return_remaining=False, verbose=False):
    '''Create a Command Line Interface, magically from a function (or collection of functions).

    This is inspired by google's Fire library, but it strips it down and removes
    some of the argument parsing quirks you get when you expose OOP via the CLI.
    Don't get me wrong! Fire is absolutely fire. But sometimes I need something that 
    is a bit simpler and a bit more flexible. This also provides customization for 
    output formatting. 

    .. code-block:: python

        def something(a, b=5, negative=False):
            """This is my docstring. I worked so hard on this !!

            Arguments:
                a (int): my first number
                b (int): my second number
                negative (bool): True if the number should be negative.

            Returns:
                (int): The bestest number.
            """
            return (a + b) * (-1 if negative else 1)

        if __name__ == '__main__':
            import starstar.cli as sscli
            sscli.main(test)

    The idea being that you can write a well documented python function, and have 
    that be enough. You shouldn't have to duplicate all that work with argparse too.

    .. code-block:: bash

        # CLI's are mostly just this anyways:
        python myscript.py attr1 method1 *positional_arguments --keyword arguments

        # so we should just be able to do:
        python script.py 8 16 --negative
        # and have it give you: -24

    Arguments:
        func (callable, dict, list, module, object, None): The function or group of functions to create
            a CLI from.
        format (callable): The result formatter to use.
        args (list?): cli argument list. Defaults to ``sys.argv[1:]``.
        verbose (bool): Print out information about the function selection.

    How it works:

     - If we receive a group of functions (dict, list, object), pop arguments from ``sys.argv[1:]`` and use those as
       keys / attributes to recursively select from the group until we reach a function/something callable.
     - Parse the remaining arguments using a relaxed version of python's ``ast`` parser.
     - if there are remaining arguments (more positional arguments than the function takes, or you use a -- separator),
       then the first two will be repeated until the arguments are used up.
     - If you provide a formatter, set aside any arguments that belong to the formatter
     - Pass the parsed arguments to the provided function and retrieve the result.
     - Pass the result to the chain of formatters to print the CLI output, then return the result.
     - super simple! :D

    .. code-block:: python

        def test(a, b=5, offset=6, multiply=1):
            """This is my docstring. This will be shown on the help screen.
            """
            return {'a': a, 'b': b*multiply + offset}

        if __name__ == '__main__':
            import starstar.cli as sscli
            sscli.main(test)

    .. code-block:: bash

        python mycli.py --help  # or -h
        # outputs:
        # Help for test(a, b=5, offset=6, multiply=1):
        # 
        # This is my docstring. This will be shown on the help screen.

        # say I want to call ``test(2)``
        python mycli.py 2
        # outputs:
        # a: 2
        # b: 11

        # specify more arguments
        python mycli.py 2 3 --offset 10
        python mycli.py 2 3 -o 10  # can use short arguments too
        # outputs:
        # a: 2
        # b: 13

        # you can also use equal separators if you prefer that
        python mycli.py 2 3 --offset=10

    You can also pass more complex types like lists and dicts. The main thing to remember is that
    if there is a space in a value, be sure to quote it!! Otherwise they will
    be read as separate arguments.

    .. code-block:: bash

        # you can pass lists
        python mycli.py [1,2]  # may give you an error on shells like zsh btw.
        python mycli.py "[1, 2]"
        # outputs:
        # a: [1, 2]
        # b: 11

        # and dicts
        python mycli.py {a:10}
        python mycli.py "{'a': 10}"
        # outputs:
        # a: {"a": 10}
        # b: 11

        # just watch where you put spaces
        python mycli.py {a:10}  # read as 1 arg: {"a": 10}
        python mycli.py {a: 10}  # read as 2 args: ['{a:', '10}']
        python mycli.py '{a: 10}'  # read as 1 arg: {"a": 10}
        # because if it can't be parsed as a python type, it'll be a string.

        python mycli.py '{my key with spaces: 10}'  
        # read as a string: "{my key with spaces: 10}"
        python mycli.py '{"my key with spaces": 10}'  
        # read as a dict: '{"my key with spaces": 10}'

    You can also pass objects and modules. If you don't provide anything, it will look for functions in
    the ``__main__`` module.

    .. code-block:: python

        # create a cli from an object

        class MyCli:
            def my_func(self): pass
            def other_func(self): pass

        if __name__ == '__main__':
            import numpy as np  # idk lol
            import starstar.cli as sscli
            sscli.main(MyCli())

        # create a cli from your favorite library
        if __name__ == '__main__':
            import numpy as np  # idk lol
            import starstar.cli as sscli
            sscli.main(np)

        # get all functions that belong to this file
        if __name__ == '__main__':
            import starstar.cli as sscli
            sscli.main()

    It's also possible to do something like argparse's ``nargs='+'``.

    .. code-block:: bash

        # this will assume that all of those arguments should be bound 
        # to the ``my_arg`` key, so your function will be passed ``my_arg=[1, 2, 3, 4]``.
        python mycli.py --my-arg 1 2 3 4

        # in fact any argument can do this. The rules are:
        python mycli.py --my-arg                     # (bool) True
        python mycli.py --no-my-arg                  # (bool) False
        python mycli.py --my-arg=False               # (bool) False
        python mycli.py --my-arg 10                  # (int) 10
        python mycli.py --my-arg something           # (str) something
        python mycli.py --my-arg something other 10  # (list[str|int]) ['something', 'other', 10]
        python mycli.py --my-arg None                # (None) None

        # If you want a value to always be a list, you can use this inside your function:
        assert starstar.asitems(['hi', 'hello']) == ['hi', 'hello']
        assert starstar.asitems(['hi']) == ['hi']
        assert starstar.asitems('hi') == ['hi']
        assert starstar.asitems(None) == []
        # I use this all the time to provide really flexible worry-free list inputs.

    Customizing output formatting:

    .. code-block:: python

        def myformat():
            pass
    
    '''
    args = sys.argv[1:] if args is None else args

    # wrap top level container as a CLI command group
    if isinstance(func, CONTAINER_TYPES + NAMED_CONTAINER_TYPES):
        func = Select(func)
    # override top docstring message
    if doc:
        func = _members(func, doc)

    trace = []
    _main_ = _main(
        trace, format=format, print_result=print_result, 
        return_remaining=return_remaining, verbose=verbose)
    while True:
        func, args = _select_function(func, args, trace=trace, verbose=verbose) 
        a, kw, args = process_args_for_func(
            func, args, terminal='--', short={'h': 'help'}, 
            short_ignore=['print', 'cliformat'], booleans=['print'])
        
        # call the function!
        func = result = _main_(*a, __clifunc__=func, __cliargs__=args, **kw)

        if args is None or return_remaining:
            return (result, args) if return_remaining else result


VALUE_TYPES = (bool, str, int, float, complex, type(Ellipsis), type(None), type(NotImplemented), set)
NAMED_CONTAINER_TYPES = (dict,)
CONTAINER_TYPES = (list, tuple)


def _main(trace, format=None, print_result=True, return_remaining=False, verbose=False):
    '''this is the command line function and can intercept arguments from the 
    command line. e.g. --help.
    '''
    def inner(*a, __clifunc__, __cliargs__, help=False, cliformat=None, print=False, **kw):
        func = __clifunc__
        if help:
            _members(func).help(trace)
        
        r = func
        if callable(func):
            if verbose:
                _printerr(f'** Calling function: {func.__name__}{signature(func)}\n')
            try:
                r = func(*a, **kw)
            except Exception:
                _printerr(f'Error occurred in: ({" > ".join(trace)})\n---\n')
                raise
        elif a or kw:
            raise TypeError(f"Object {r} received arguments ({kw}), even though it's not callable.")

        if __cliargs__ is None or return_remaining or print:
            if print_result or print:
                _print_result(r, formatter=cliformat or format)
        return r
    return inner


def _isvalue(x, depth=2):
    '''Check if an argument can be considered a '''
    if not depth:
        return isinstance(x, VALUE_TYPES)
    return (
        all(_isvalue(v, depth=depth-1) for v in x) if isinstance(x, CONTAINER_TYPES) else 
        all(_isvalue(x[k], depth=depth-1) for k in x) if isinstance(x, NAMED_CONTAINER_TYPES) else 
        isinstance(x, VALUE_TYPES))


class _members:
    '''This wraps around an object and creates a uniform interface for 
    type checks and member access from the object.'''
    def __init__(self, obj, doc=None):
        if isinstance(obj, _members):
            self.__dict__ = obj.__dict__
            self.doc = doc or self.doc
            return
        self.obj = obj
        self.doc = doc or getattr(obj, '__doc__', '') or ''

        self.iscls = iscls = inspect.isclass(obj)
        self.isfunc = inspect.isroutine(obj)
        self.iscontainer = isinstance(obj, CONTAINER_TYPES)
        self.isnamedcontainer = isinstance(obj, NAMED_CONTAINER_TYPES)
        self.isvalue = isval = _isvalue(obj)
        self.hasstr = not iscls and not isval and next(
            c for c in obj.__class__.__mro__ if '__str__' in c.__dict__
        ) is not object
        self.getitem = hasattr(obj, '__getitem__')
        self.callable = callable(obj)

    def __str__(self):
        return '({}{})'.format(self.obj, ''.join(f'\n  {k}: {self[k]}' for k in self))

    def __iter__(self):
        '''Get all keys for the object.'''
        if self.getitem:
            if self.isnamedcontainer:
                yield from self.obj
                return
            try:
                yield from range(len(self.obj))
            except TypeError:
                pass
            return

        yield from (k for k in dir(self.obj) if not k.startswith('_'))

    def __contains__(self, key):
        '''Check if the object contains a key'''
        return key in iter(self)

    def __getitem__(self, key):
        '''Get a member by name'''
        if self.getitem:
            return self.obj[parse(str(key))]
        return getattr(self.obj, key)

    def _help(self, trace=None):
        trace = f'| {" > ".join(trace)} ...\n' if trace else ''
        obj = self.obj
        doc = inspect.cleandoc(self.doc)
        if self.isfunc:
            return (
                f'{trace}Help for {obj.__name__}{signature(obj)}:\n\n'
                f'{doc or "-- No docstring available. --"}')
        if self.isvalue:
            return f'({type(obj).__name__})'

        cmds = '\n\n'.join(_members(self[k])._mini_help(k, depth=1) for k in self)

        if self.iscls:
            return (
                f'{trace}Help for {obj.__name__}{signature(obj.__init__)}:\n\n'
                f'{doc or "-- No docstring available. --"}\n' + 
                (f'\nAvailable:\n\n{_indent(cmds)}' if cmds else ''))

        return (
            trace + (f"{doc}\n" if doc else '') + 
            (f'\nAvailable:\n\n{_indent(cmds)}' if cmds else ''))

    def _mini_help(self, name=None, depth=0):
        f = self.obj
        if self.isvalue:
            return f'{name} ({type(f).__name__})'

        # function docstring
        doc = self.doc.split("\n")
        i = next((i for i, x in enumerate(doc) if not x.strip()), None)
        doc = ' '.join(x.strip() for x in doc[:i])

        # function signature
        s = signature(f.__init__ if self.iscls else f, required=False) if self.isfunc or self.iscls else None
        s = f'\n ட {s}' if s else ''
        ann = ' (cls)' if self.iscls else ''

        # nested commands
        cmds = '\n\n'.join(
            _members(self[k])._mini_help(k, depth=depth-1) 
            for k in self) if depth else ''
        cmds = '\n\n' + _indent(cmds) if cmds else ''

        return f'{name or f.__name__}{ann}: {doc}{s}{cmds}'
        

    def help(self, trace=None):
        print(self._help(trace), file=sys.stderr)
        sys.exit(0)


def _select_function(func, args, trace=None, verbose=False):
    '''This will select functions using the positional arguments until it reaches something that we can call.'''
    # handle multi-functions
    while True:
        mems = _members(func)
        if mems.callable:
            break
        # no arguments, show all available functions
        if not args:
            if mems.isvalue or mems.hasstr:
                break
            mems.help()

        key = args[0]
        try:
            # lookup the key using a case insensitive lookup
            insensitive_lookup = {k.lower().replace('-', '_'): k for k in mems}
            key2 = insensitive_lookup[key.lower().replace('-', '_')]
            # okay we matched something lets keep going
            if verbose:
                print(f'** Selecting: {key}', file=sys.stderr)
            func, args = mems[key2], args[1:]
            if trace is not None:
                trace.append(key2)
        except (KeyError, AttributeError, IndexError):
            if not key.startswith('-'):  # ignore keyword argument
                print("\nNot found:", key, '\n', file=sys.stderr)
            mems.help()
    return func, args



class Select:
    def __init__(self, __value__=None, __name__=None, __doc__=None, **kw):
        if isinstance(__value__, NAMED_CONTAINER_TYPES):
            d = dict(__name__=__name__, __doc__=__doc__)
            d.update(__value__)
            d.update(kw)
            self.__init__(None, **d)
            return

        if isinstance(__value__, CONTAINER_TYPES):
            a, kw = __value__, kw
        else:
            a = [__value__] if __value__ is not None else []

        kw = dict(((str(getattr(x, '__name__', None) or i), x) for i, x in enumerate(a)), **kw)

        for k, x in kw.items():
            if isinstance(x, CONTAINER_TYPES + NAMED_CONTAINER_TYPES):
                x = Select(x)
            self.__dict__[k] = x

        self.__name__ = __name__
        self.__doc__ = __doc__


# class _trace:
#     class traceitem:
#         def __init__(self, x, *a, **kw):
#             self.member = _members(x)
#             self.a, self.kw = a, kw
#         def __str__(self):
#             return self.format.format(self.member.obj, *self.a, **self.kw)

#     class attr(traceitem): format = '{}.{}'
#     class item(traceitem): format = '{}[{}]'
#     class call(traceitem): 
#         def __str__(self):
#             return '{}({})'.format(
#                 self.member.obj.__name__, ', '.join(
#                     [str(x) for x in self.a] + 
#                     ['{}={!r}'.format(k, v) for k, v in self.kw.items()]))



#######################
# Argument Grouping
#######################

# there are certain keys that you can't use in a python function - so
# we're going to just put a underscore after them

# This is not enabled by default currently
BAD_SYNTAX_KEYS = [
    'and', 'as', 'assert', 'async', 'await', 
    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 
    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 
    'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 
    'yield'
]
BAD_SYNTAX_KEY_MAP = {}
BAD_SYNTAX_FIX = '{}_'


def process_args_for_func(func, args=None, short=None, short_ignore=None, skip_n=0, **kw):
    isfunc = callable(func)
    # this lets us detect if we've filled up all of the positional arguments of a function
    n_pos = (
        0 if not isfunc else None 
        if starstar.get_args(func, starstar.VAR_POS) else 
        len(starstar.get_args(func, starstar.POS)) - skip_n)
    short = dict((shortkws(func, ignore=short_ignore or ()) if isfunc else {}), **(short or {}))
    # convert cli arguments into function arguments
    return process_args(args, short=short, n_pos=n_pos, **kw)

def process_args(
        args=None, initial_key='*', short=None, n_pos=None, booleans=None, 
        false_prefix='no-', convert_bad_syntax=False, terminal=None):
    '''Given CLI arguments, convert them to positional and keyword arguments for a function.'''
    args = sys.argv[1:] if args is None else args
    short = short or {}
    key = initial_key
    kw = {key: []}

    # pool the arguments
    i = -1  # default i for arg remainder
    terminated = False
    for i, x in enumerate(args):
        # allow using some terminal value e.g. --
        if x == terminal:
            terminated = True
            break
        # handle key
        if x.startswith('-'):
            # handle short arguments
            if not x.startswith('--'):
                if short and x[1:] in short:
                    x = f'--{short[x[1:]]}'
                else:
                    x = f'-{x}'
            key, v = x[2:], None
            # detect k=v as two parts
            if '=' in key:
                key, v = key.split('=', 1)
            # see if we have a flipped argument
            if v is None and key.startswith(false_prefix):
                key = key[len(false_prefix):]
                v = 'False'
            key = key.replace('-', '_')

            # allow people to use python reserved syntax keywords
            if convert_bad_syntax:
                if key in BAD_SYNTAX_KEY_MAP:
                    key = BAD_SYNTAX_KEY_MAP[key]
                elif key in BAD_SYNTAX_KEYS:
                    key = BAD_SYNTAX_FIX.format(key)

            if key not in kw:
                kw[key] = []
            if v is not None:
                kw[key].append(parse(v))
            continue
        elif booleans and key in booleans:
            i -= 1
            break
        if n_pos is not None and key == '*' and len(kw['*']) >= n_pos:
            i -= 1
            break
        # handle value
        kw[key].append(parse(x))
    
    # parse their format
    for k in set(kw) - {'*'}:
        v = kw[k]
        kw[k] = v[0] if len(v) == 1 else True if not v else v
    return kw.pop('*'), kw, (args[i+1:] or ([] if terminated else None))





#######################
# Short Arg Translation
#######################


def shortkws(func, n=1, ignore=(), reserved=()):
    '''Get short names for keyword arguments. This is just like what many CLIs do.
    
    Arguments:
        func (callable): The function to look at.
        n (int): The max number of characters to use. e.g. if you set ``n=2``,
            then ``ignore`` can map to either ``i`` or ``ig``. Defaults to 1.
        ignore (list, tuple): Full keys you want to ignore.
        reserved (list, tuple): Short keys you want to ignore.

    Returns:
        (dict): The mapping between short name and full name.

    .. code-block:: python

        def func(blah, argh, ughh):
            return blah, argh, ughh

        # get the short kw mapping
        assert starstar.shortkws(func) == {'b': 'blah', 'a': 'argh', 'u': 'ughh'}

        # get the short kw mapping for the first two characters
        assert starstar.shortkws(func, n=2) == {
            'b': 'blah', 'bl': 'blah', 'a': 'argh', 'ar': 'argh', ...}

    '''
    short = {}
    for p in get_args(func, KW):
        k = p.name
        if k in ignore:
            continue
        for i in range(min(n, len(k))):
            ki = k[:i+1]
            if ki in reserved:
                continue
            if ki not in short:
                short[ki] = k
    return short


def convert_shortkws(kw, short):
    for k in short:
        if k in kw:
            klong = short[k]
            if klong in kw:
                raise TypeError(f'keyword argument repeated: {k} & {klong}')
            kw[klong] = kw.pop(k)
    return kw


@traceto(shortkws)
def accept_shortkws(func=None, short=None, **kw):
    '''A decorator that automatically converts short keywords to full ones 
    in a function call.

    Arguments:
        short (dict?): Precomputed short kw mapping. If provided, :func:`shortkws` won't be called.

    Examples:

    .. code-block:: python

        @starstar.accept_shortkws
        def func(blah, argh, ughh):
            return blah, argh, ughh

        assert func(b=1, a=2, u=3) == 1, 2, 3
    '''
    def outer(func, short=short):
        func.shortkw = short = short or shortkws(func, **kw)
        @core._builtin_wraps(func)
        def inner(*a, **kw):
            return func(*a, **convert_shortkws(kw, short))
        return inner
    return outer(func) if callable(func) else outer





###################
# CLI Value Parsing
###################


def parse(value):
    """Parse a python literal from a string, allowing for some flexibilities in syntax.

    
    .. code-block:: python
    
        assert sscli.parse('5') == 5
        assert sscli.parse('asdf') == 'asdf'
        assert sscli.parse('True') == True
        assert sscli.parse('None') == None
        assert sscli.parse('[1,2,3]') == [1, 2, 3]
        assert sscli.parse('[1,2,asdf]') == [1, 2, 'asdf']
        assert sscli.parse('{a:5}') == {'a': 5}
        assert sscli.parse('{a:[1,2,3]}') == {'a': [1, 2, 3]}
    """
    try:
        return _literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def _literal_eval(value):
    root = ast.parse(value, mode='eval')
    if isinstance(root.body, ast.BinOp):  # pytype: disable=attribute-error
        raise ValueError(value)

    for node in ast.walk(root):
        for field, child in ast.iter_fields(node):
            if isinstance(child, list):
                for index, subchild in enumerate(child):
                    if isinstance(subchild, ast.Name):
                        child[index] = _replacement(subchild)
            elif isinstance(child, ast.Name):
                node.__setattr__(field, _replacement(child))

    # supports: strings, bytes, numbers, tuples, lists, dicts, sets, booleans, and None
    return ast.literal_eval(root)


_BUILTIN = ('True', 'False', 'None')  # TODO: '...'
def _replacement(node):
  """Returns a node to use in place of the supplied node in the AST."""
  value = node.id
  return node if value in _BUILTIN else ast.Str(value)





###################
# Result Formatting
###################


class Csv:
    def __call__(self, data):
        import csv
        w = csv.DictWriter(sys.stdout, fieldnames=list(data[0]) if data else [])
        w.writeheader()
        for d in data:
            w.writerow(d)

class Json:
    def __init__(self, indent=4):
        self.indent = indent

    def __call__(self, data):
        import json
        return json.dumps(data, indent=self.indent)

class Yaml:
    def __call__(self, data):
        import yaml
        return yaml.dump(data)

class Table:
    def __init__(self, columns=None, drop=None, drop_types=(dict, list), **kw):
        self.columns = columns
        self.drop = drop
        self.drop_types = drop_types
        self.cell_kw = kw

    def cell(self, x, bool_icon=None):
        '''Format a cell's value based on its data type.'''
        if isinstance(x, bool):
            BOOL = BOOLS[bool_icon or DEFAULT_BOOL]
            return BOOL[0] if x else BOOL[1]
        if isinstance(x, float):
            return f'{x:,.3f}'
        if isinstance(x, list):
            return f'list[{len(x)}, {type(x[0]).__name__ if x else None}]'
        if isinstance(x, dict):
            return f'dict{{{len(x)}}}'
        if x is None:
            return '--'
        return str(x)

    COL_SEPS = ',/|'
    JOIN_SEPS = '\n|'

    def __call__(self, data):
        '''Format a list of dictionaries as a table.'''
        # short-circuit for non-lists
        if not isinstance(data, (list, tuple)):
            return data
        elif not data:
            return '-- no data --'

        import tabulate

        # get data
        cols, colnames = self._parse_columns(data)
        return tabulate.tabulate([
            _joinnested(_nested_apply(
                cols, lambda c: _nested_key(d, c, None)), self.JOIN_SEPS) 
            for d in data
        ], headers=colnames)

    def _parse_columns(self, data):
        # get all columns across the data
        all_cols = {
            c for d in data for c in d 
            if not c.startswith('_')} - set(self.drop or ())
        if self.drop_types:
            all_cols = {
                c for c in all_cols 
                if not any(isinstance(d.get(c), self.drop_types) for d in data)}

        seps = self.COL_SEPS
        # default auto columns
        # break out columns into a uniform list
        cols = list(_splitnested(self.columns or sorted(all_cols), seps, all_cols))

        # handle leftover columns
        remaining_cols = [_deepnest(c, len(seps)-1) for c in sorted(all_cols - set(_flatten(cols)))]
        remaining_flag = _deepnest('...', len(seps)-1)
        # given_cols = {c for ci in cols for cj in ci for c in cj}
        cols = [
            ci for ci_ in cols 
            for ci in (remaining_cols if ci_ == remaining_flag else (ci_,))]

        # convert back to column names
        # colnames = ['/'.join('|'.join(cj) for cj in ci) for ci in cols]
        colnames = [_joinnested(c, seps[1:]) for c in cols]
        return cols, colnames


def _maybesplit(x, ch, strip=True, filter=True):
    '''Coerce a string to a list by splitting by a certain character,
    or skip if already a list.'''
    return [
        x.strip() if strip and isinstance(x, str) else x
        for x in (x.split(ch) if isinstance(x, str) else x)
        if not filter or x]


def _splitnested(cols, seps=',/|', avail=None):
    '''Splits a shorthand column layout into a nested column list.
    e.g.
        'time,max_laeq|avg_laeq/l90|min_laeq,emb_*,...'
        [
            [['time]],
            [
                ['max_laeq', 'avg_laeq'],
                ['l90', 'min_laeq']
            ],
            [['emb_min']], [['emb_max'], ...],
            [['time']], ...  # leftover columns
        ]

    '''
    if not seps:
        yield cols
        return
    sep, nextsep = seps[0], seps[1] if len(seps) > 1 else None
    for x in _maybesplit(cols, sep):
        xs = [x]
        if isinstance(x, str) and not any(s in x for s in seps) and avail and '*' in x:
            xs = sorted(c for c in avail if fnmatch.fnmatch(c, x))

        for xi in xs:  # inner loop handles unpacked glob
            yield list(_splitnested(xi, seps[1:], avail)) if nextsep else xi


def _nested_apply(xs, func, *a, _types=(list, tuple, set), **kw):
    if isinstance(xs, _types):
        return type(xs)(_nested_apply(x, func, *a, **kw) for x in xs)
    return func(xs, *a, **kw)


def _joinnested(cols, seps=',/|', apply=None, **kw):
    return seps[0].join(_joinnested(cols, seps[1:])) if seps else (apply(cols, **kw) if apply else cols)

def _deepnest(x, n):
    for _ in range(n):
        x = [x]
    return x


def _flatten(xs, *types):
    if isinstance(xs, types or (list, tuple, set)):
        yield from (xi for x in xs for xi in _flatten(x))
        return
    yield xs


def _nested_key(d, k, default=...):
    '''Get a nested key (a.b.c) from a nested dictionary.'''
    for ki in k.split('.'):
        try:
            d = d[ki]
        except (TypeError, KeyError):
            if default is ...:
                raise
            return default
    return d

# boolean display

BOOLS = {
    'moon': ['🌖', '🌒'],
    'full-moon': ['🌕', '🌑'],
    'rose': ['🌹', '🥀'],
    'rainbow': ['🌈', '☔️'],
    'octopus': ['🐙', '🐍'],
    'virus': ['🔬', '🦠'],
    'party-horn': ['🎉', '💥'],
    'party-ball': ['🎊', '🧨'],

    'relieved': ['😅', '🥺'],
    'laughing': ['😂', '😰'],
    'elated': ['🥰', '🤬'],
    'fleek': ['💅', '👺'],
    'thumb': ['👍', '👎'],
    'green-heart': ['💚', '💔'],
    'circle': ['🟢', '🔴'],
    'green-check': ['✅', '❗️'],
    'TF': ['T', 'F'],
    'tf': ['t', 'f'],
    'YN': ['Y', 'N'],
    'yn': ['y', 'n'],
    'check': ['✓', ''],
    'checkx': ['✓', 'x'],
}

DEFAULT_BOOL = 'rose'






def _default_format(result):
    '''The default output formatter.'''
    if isinstance(result, dict):
        return '\n'.join(f'{k}: {v}' for k, v in result.items())
    if isinstance(result, list):
        return '\n'.join(map(str, result))
    if isinstance(result, GeneratorType):
        for x in result:
            print(x)
        return
    return result


FORMATTERS = {'json': Json, 'csv': Csv, 'table': Table, 'yaml': Yaml}


def _print_result(result, formatter=None, available_formats=None, **kw):
    '''Prepare the result for output. The result will either be casted to a string, 
    or if the result is None, no output will be shown.'''
    if formatter is not False:
        formatters = list(starstar.asitems([] if formatter is True else formatter))
        # allow users to specify cliformat as a string via a cli argument - but we need to translate
        if available_formats is not False:
            available_formats = available_formats or FORMATTERS
            for i, f in enumerate(formatters):
                if not callable(f):
                    f = available_formats[f]
                    formatters[i] = f() if isinstance(f, type) else f
        formatters.append(_default_format)

        for func in formatters:
            result = func(result, **starstar.filter_kw(func, kw, skip_n=1))

    if result is not None:
        print(result)


def _indent(text, n=1, width=4):
    '''Indent text a certain indent.'''
    return '\n'.join(' '*n*width + l for l in str(text or '').splitlines())



def _printerr(*a, v=True, **kw):
    # print to stderr
    if v:
        print(*a, file=sys.stderr, **kw)



if __name__ == '__main__':
    def func(*a, **kw):
        '''This is a function that shows you 
        what you passed it!'''
        return a, kw

    def func_named(name):
        def func(*a, **kw):
            '''This is a function that shows you 
            what you passed it!
            yep!
            
            can't see me! cuz the blank line.
            '''
            return name, a, kw
        func.__name__ = name
        return func

    class Something:
        '''Hello hi im something'''
        def __init__(self, name):
            self.name = name

        def __str__(self):
            return 'my special {}({})'.format(self.__class__.__name__, self.name)

        def say_hi(self):
            '''Saying hi'''
            print('Hiii', self.name)

        def breakit(self):
            1/0

        def table(self):
            return [{'a': 5, 'b': 6}, {'a': 15, 'b': 16}]

    main({
        'a': func_named('a'),
        'b': func_named('b'),
        'c': {
            'd': func_named('d'),
            'e': func_named('e'),
        },
        'Something': Something,
        'x': {'a': 5, 'b': [5, 6, 7], 'c': 7}
    }, '''Hello I'm a doc
    
    this is my cute lil doc
    ''')