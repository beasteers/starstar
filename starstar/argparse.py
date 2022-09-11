'''Create an argparse ArgumentParser from a function signature.

.. note::

    This isn't a fully featured CLI alternative. This is meant for cases
    where you need to interface with another CLI that uses argparse 
    (e.g. pytorch_lightning).

I find writing out argparse arguments extremely annoying. 
Why do I have to? The information is already there!
Usually I use ``fire``, but that's not always an option so 
hopefully this can help reduce the amount of code you need
to write.


.. code-block:: python

    import starstar.argparse

    def myfunc(batch_size=64, dataset='urbansas', n_mels=128, win_size=10):
        ...

    parser = starstar.argparse.from_func(myfunc)
    args = parser.parse_args()

    # this.py --batch-size 32 --win-size 15



'''
from __future__ import annotations
import copy
import functools
from typing import Any, Callable, Union, get_type_hints
try:
    from typing import Literal, get_origin, get_args
except ImportError:
    from typing_extensions import Literal, get_origin, get_args
import argparse
import inspect
import starstar
from starstar import docstr, POS_ONLY, VAR_POS, VAR_KW, POS_KW
from starstar.parse import parse

TYPE = type

# improved argparser with vararg parsing

class ArgumentParser(argparse.ArgumentParser):
    accept_var_kw = False
    def parse_args(self, *a):
        if getattr(self, 'accept_var_kw', False):
            return self.parse_varkw_args(*a)
        return super().parse_args(*a)

    def parse_varkw_args(self, *a):
        '''Parse arguments and accept var kwargs if provided.'''
        # support variable kwargs
        parsed, unknown = self.parse_known_args(*a)
        key = None
        values = []
        for arg in unknown + [None]:  # type: ignore
            if arg is None or arg.startswith(("-", "--")):
                if key is not None:
                    self.add_argument(key, required=False, type=parse, default=argparse.SUPPRESS)
                key = arg
                values.clear()
                continue
            values.append(arg)
        return super().parse_args(*a)


def from_func(
        func: Callable, 
        *, 
        parser: argparse.ArgumentParser|None=None, 
        docstyle: str|None=None, 
        prog: str|bool|None=None, 
        actions: dict[str, str]|None=None, 
        choices: dict[str, list]|None=None, 
        defaults: dict[str, Any]|None=None,
        consts: dict[str, Any]|None=None, 
        nargs: dict[str, int|str]|None=None, 
        types: dict[str, Callable]|None=None, 
        dests: dict[str, str]|None=None, 
        short: dict[str, str]|None=None,
        **kw
):
    '''
    
    Arguments:
        func (callable):
        parser (argparse.ArgumentParser): You can pass in your own parser to use.
        docstyle (str): The name of the docstring style. Can be google or numpy.

    '''
    actions = actions or {}
    choices = choices or {}
    defaults = defaults or {}
    consts = consts or {}
    nargs = nargs or {}
    dests = dests or {}
    types = types or {}

    # 
    if 'parents' in kw:
        kw.setdefault('add_help', False)

    # handle class init
    if isinstance(func, type):
        cls = func
        func_name = func.__name__
        docs = func.__init__.__doc__ or func.__doc__
        func = func.__init__
    else:
        func_name = func.__name__
        docs = func.__doc__


    # parse docstring
    docs = docstr.parse(docs, style=docstyle) or None
    docargs = list(docs.children('args')) if docs else None
    description = docs.first('desc') if docs else None

    # create parser if not provided
    if not parser:
        if 'formatter_class' not in kw:
            kw['formatter_class'] = argparse.RawDescriptionHelpFormatter
        if description and 'description' not in kw:
            kw['description'] = str(description)
        kw['prog'] = func_name if prog is True else prog
        parser = ArgumentParser(**kw)
    
    # get signature
    s = starstar.signature(func)
    short = _get_shortkw(s.parameters, reserved=['h'], short=short)

    # fix union syntax and get type hints
    s = copy.copy(s)
    anns = dict(func.__annotations__)
    for n, tstr in list(anns.items()):
        anns[n] = _repl_union(tstr)
    type_hints = get_type_hints(TYPE(func_name, (object,), {'__annotations__': anns}))

    # make any arguments before varargs positional only
    override_pos_only = any(p.kind == VAR_POS for p in s.parameters.values())

    # create each parameter
    for name, p in s.parameters.items():
        pkw = {}

        flag_name = name
        short_name = short.get(name)

        # check if the argument is positional
        var_pos = p.kind == VAR_POS
        pos_only = p.kind == POS_ONLY
        pos_kw = p.kind == POS_KW
        positional = var_pos or pos_only or (override_pos_only and pos_kw)

        # var arg specifics: *a, **kw
        if var_pos:
            # allow 0 or more
            pkw['nargs'] =  '*'
            # indicate that it gobbles up positional args
            pkw['metavar'] = f'*{name}'
            override_pos_only = False
        elif p.kind == VAR_KW:
            # can't handle varkw in here (see parse_args)
            parser.accept_var_kw = True
            continue

        # manual nargs
        if name in nargs:
            pkw['nargs'] = nargs[name]
        # manual action
        if name in actions:
            pkw['action'] = actions[name]
        # custom type
        if name in types:
            pkw['type'] = types[name]
        # rename destination
        if name in dests:
            pkw['dest'] = dests[name]
        
        # set defaults
        default = defaults.get(name, p.default)
        if default == inspect._empty:
            if not positional:
                pkw['required'] = True
        else:
            if positional and 'nargs' not in pkw:
                pkw['nargs'] = '?'
            pkw['default'] = default

        # set action & type

        # use type annotation
        dtype = type_hints.get(name)
        if dtype:
            if _lenient_subclass(dtype, bool):
                if 'action' not in pkw:
                    if default is True:
                        pkw['action'] = 'store_false'
                        flag_name = f'no-{flag_name}'
                        if short_name:
                            short_name = f'no{short_name}'
                    else:
                        pkw['action'] = 'store_true'
            if _lenient_subclass(dtype, (list, tuple)):
                if 'action' not in pkw:
                    pkw['action'] = 'extend'
                if 'nargs' not in pkw:
                    pkw['nargs'] = '+'
            elif 'type' not in pkw:
                pkw['type'] = _type_checker(dtype)
        if 'type' not in pkw:
            pkw['type'] = parse

        # manage constants
        if name in consts:
            if pkw.get('action') in {'append', 'extend'}:
                pkw['action'] = 'append_const'
            elif 'action' not in pkw:
                pkw['action'] = 'store_const'
            pkw['const'] = consts[name]

        # set choices
        if name in choices:
            pkw['choices'] = choices[name]
        elif type and get_origin(type) == Literal:
            pkw['choices'] = get_args(type)

        # create flags
        flag_name = flag_name.replace('_', '-')
        if positional:
            argnames = [flag_name]
        else:
            argnames = [f'--{flag_name}']
            if name in short:
                argnames.append(f'-{short_name}')

        # find the help message
        for darg in docargs or []:
            for dp in darg.body:
                if dp.name == name:
                    helpmsg = dp.get('desc')
                    if helpmsg:
                        pkw['help'] = str(helpmsg)
                        break
        
        # print(argnames, pkw)
        parser.add_argument(*argnames, **pkw)
    return parser


# short arguments

def _get_shortkw(parameters, ignore=(), reserved=(), short=None):
    '''Given a set of arguments, find the natural short arguments e.g. ``--wow -> -w``'''
    short = short or {}
    for k in parameters:
        if parameters[k].kind == POS_ONLY:
            continue
        if k not in ignore and k[0] not in reserved and k[0] not in short:
            short[k] = k[0]
    return short



# type checkers

def _lenient_subclass(obj, cls, union_cond=all):
    '''Check isinstance/subclass including unions.'''
    if get_origin(obj) == Union:
        return union_cond(t is None or t is type(None) or _lenient_subclass(t, cls) for t in get_args(obj))
    return isinstance(obj, cls) or isinstance(obj, type) and issubclass(obj, cls)

def _type_check(type, x):
    '''Cast union type'''
    if get_origin(type) == Union:
        for t in get_args(type):
            try:
                return _type_check(t, x)
            except Exception:
                pass
        raise TypeError(f"{x} could not be cast to {type}")
    return type(x)

def _type_checker(type):
    '''A decorator for type checking.'''
    @functools.wraps(type)
    def __type(x):  return _type_check(type, x)
    if __type.__name__ == '__type':
        __type.__name__ = __type.__qualname__ = _type_check_name(type)
    return __type

def _type_check_name(type):
    '''Get the name of a type check (including unions)'''
    if get_origin(type) == Union:
        return '|'.join([_type_check_name(t) for t in get_args(type)])
    return type.__name__



# Fix old union annotations

# Constants
OPEN_BRACKET = '['
CLOSE_BRACKET = ']'
COMMA = ','
OR = '|'


def _repl_union(s: str):
    """ Replace PEP 604-style annotations (i.e. like `X | Y`) with `Union[X, Y]`."""
    # If there is no '|' character in the annotation part, we just return it.
    if OR not in s:
        return s
    s = s.replace(' ', '')

    # Checking for brackets like `List[int | str]`.
    if OPEN_BRACKET in s:
        # Get any indices of COMMA or OR outside a braced expression.
        outer_commas, outer_pipes = _outer_comma_and_pipe_indices(s)
        # commas outside bracket? e.g. dict[str | int, str]***,*** value[test]
        if outer_commas:
            return COMMA.join([_repl_union(i) for i in _sub_strings(s, outer_commas)])
        # pipes outside bracket? e.g.: value | dict[str | int, list[int | str]]
        if outer_pipes:
            return f'Union{OPEN_BRACKET}{COMMA.join([_repl_union(i) for i in _sub_strings(s, outer_pipes)])}{CLOSE_BRACKET}'

        # no outer commas/pipes, and `SomeType[str][bool]` is  invalid
        # Replace inside brackets, e.g.: dict[str | int, str]
        first_start_bracket = s.index(OPEN_BRACKET)
        last_end_bracket = s.rindex(CLOSE_BRACKET)
        return (
            f'{s[:first_start_bracket]}{OPEN_BRACKET}'
            f'{_repl_union(s[first_start_bracket + 1:last_end_bracket])}'
            f'{CLOSE_BRACKET}{s[last_end_bracket + 1:]}')

    elif COMMA in s:  #  e.g. `int | str, float | None`
        return COMMA.join([_repl_union(i) for i in s.split(COMMA)])

    return f'Union{OPEN_BRACKET}{s.replace(OR, COMMA)}{CLOSE_BRACKET}'  # e.g. `int | str`


def _sub_strings(s: str, split_indices):
    """Split a string on the specified indices, and return the split parts."""
    prev = -1
    for idx in split_indices:
        yield s[prev+1:idx]
        prev = idx
    yield s[prev+1:]


def _outer_comma_and_pipe_indices(s: str):
    """Return any indices of ',' and '|' that are outside of braces."""
    indices = {OR: [], COMMA: []}
    brace_dict = {OPEN_BRACKET: 1, CLOSE_BRACKET: -1}
    brace_count = 0

    for i, char in enumerate(s):
        if char in brace_dict:
            brace_count += brace_dict[char]
        elif not brace_count and char in indices:
            indices[char].append(i)
    return indices[COMMA], indices[OR]


# Demo



def myfunction(aaa, bbb=5, *a, wow: int|list, quoi='aaa', **kw):
        '''Look at my function

        I love it so much

        Arguments:
            aaa: first
            bbbb: second thing
            wow (int): ok cool
            quoi (str): wow alright
        '''
        print(aaa,  bbb, a, wow, quoi, kw)

if __name__ == '__main__':
    # parser = from_func(myfunction, docstyle='google')
    # args = parser.parse_args()
    # print(args)

    parent = argparse.ArgumentParser()
    parent.add_argument('--extra',  default=5)
    parser = from_func(myfunction, parents=[parent], docstyle='google')
    args = parser.parse_args()
    print(args)
