from __future__ import annotations
import inspect
from types import MappingProxyType
from typing import Callable, Iterable, cast as tcast
from inspect import signature as _builtin_signature, Signature as _Signature
from functools import wraps as _builtin_wraps, update_wrapper as _update_wrapper


POS_ONLY = inspect.Parameter.POSITIONAL_ONLY
KW_ONLY = inspect.Parameter.KEYWORD_ONLY
POS_KW = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POS = inspect.Parameter.VAR_POSITIONAL
VAR_KW = inspect.Parameter.VAR_KEYWORD

ALL = {POS_ONLY, KW_ONLY, POS_KW, VAR_POS, VAR_KW}
POS = {POS_ONLY, POS_KW}
KW = {POS_KW, KW_ONLY}
VAR = {VAR_POS, VAR_KW}

NAMED = ALL - VAR
NOT_KW = ALL - KW



def divide(kw: dict, *funcs: Callable|Iterable[Callable], mode='strict', varkw: bool=True):
    '''Divide ``**kwargs`` between multiple functions based on their signatures.
    
    Arguments:
        *funcs (callable): The functions you want to divide arguments amongst.
        mode (str): How to handle extra keyword arguments.

             - ``'separate'``: Add them as an extra dictionary at the end.
             - | ``'strict'``: If there are extra keyword arguments, raise a ``TypeError``. 
                This will only raise if no function with a variable keyword is found or ``varkw == False``.
        varkw (bool | 'first'): Do we want to pass extra arguments as ``**kwargs`` to any function 
            that accepts them? By default (True), they will go to all functions with variable keyword 
            arguments. If ``'first'`` they will only go to the first matching function. If ``False``, 
            no function will get variable keyword args.

    Returns:
        A dict for each function provided, plus one more for unused kwargs if ``mode == 'separate'``.

    Raises:
        TypeError: if ``mode='strict'`` (default) and it receives arguments that don't appear in any function's signature. Does not apply if any function takes ``**kw``.

    Pass arguments to multiple functions!

    .. code-block:: python 

        def func_a(a=None, b=None, c=None):
            return a, b, c

        def func_b(d=None, e=None, f=None):
            return d, e, f

        def main(**kw):
            kw_a, kw_b = starstar.divide(kw, func_a, func_b)
            func_a(**kw_a)
            func_b(**kw_b)

        # and it even works for nested functions !

        def func_c(**kw):
            kw_a, kw_b = starstar.divide(kw, func_a, func_b)
            func_a(**kw_a)
            func_b(**kw_b)

        def func_d(g=None, h=None, i=None):
            return g, h, i

        def main(**kw):
            kw_c, kw_d = starstar.divide(kw, (func_a, func_b), func_d)
            func_c(**kw_c)
            func_d(**kw_d)

    Decide how you want to handle extra keyword args.

    .. code-block:: python

        main(a=1, x=2)  # extra argument "x"
        # divide raises TypeError

        def main(**kw):
            kw_a, kw_b, kw_extra = starstar.divide(kw, func_a, func_b, mode='separate')

        main(a=1, x=2)  # extra argument "x"
        # gets put in ``kw_extra``
    '''
    pss = [_nested_cached_sig_params(f) for f in funcs]
    kws = [{} for _ in pss]

    # get all keys that match explicitly defined parameters
    kwunused = dict(kw)
    for ps, kwi in zip(pss, kws):
        for name in ps:
            if ps[name].kind in NOT_KW or name not in kw:
                continue
            kwi[name] = kw[name]
            kwunused.pop(name, None)

    # check functions for varkw
    if kwunused and varkw:
        found_varkw = False
        for ps, kwi in zip(pss, kws):
            if any(p.kind == VAR_KW for p in ps.values()):
                kwi.update(kwunused)
                found_varkw = True
                if varkw == 'first':
                    break
        if found_varkw:
            kwunused.clear()

    # handle extra kwargs
    if mode == 'separate':
        kws.append(kwunused)
    elif mode == 'strict':
        if kwunused:
            raise TypeError('Got unexpected arguments: {}'.format(tuple(kwunused)))

    return kws


def _nested_cached_sig_params(f: Callable|list|tuple) -> dict|MappingProxyType:
    '''Get and merge signature parameters for potentially multiple functions.'''
    # return signature(f).parameters
    # return {k: p for fi in _nested(f) for k, p in signature(fi).parameters.items()}
    if isinstance(f, (list, tuple)):
        return {k: v for fi in f for k, v in signature(fi).parameters.items()}
    return signature(f).parameters

def _nested(xs, types=(tuple, list)):
    if isinstance(xs, types):
        yield from (xi for x in xs for xi in _nested(x))
    else:
        yield xs


def signature(f: Callable, required=True) -> _Signature:  # type: ignore
    '''Get a function signature.
    
    Faster than inspect.signature (after the first call) because it 
    is cached using the standard ``f.__signature__`` attribute.
    '''
    try:
        try:
            return f.__signature__
        except AttributeError:
            s = tcast(_Signature, _builtin_signature(f))
            try:
                f.__signature__ = s
            except AttributeError:
                try:
                    f.__dict__['__signature__'] = s
                except AttributeError:
                    pass
            return s
    except ValueError:
        if required:
            raise

def traceto(*funcs: Callable, keep_varkw=None, filter_hidden=True, doc=False) -> Callable:  # , kw_only=True
    '''Tell a function where its ``**kwargs`` are going!

    This is similar to ``functools.wraps``, except that it merges the signatures of multiple functions
    and only deals with arguments that can be passed as keyword arguments.

    Arguments:
        *funcs (callable): The functions where the keyword arguments go.
        keep_varkw (bool): Whether we should keep ``**kw`` in the signature.
            If not set, this will be True if any of the passed arguments take 
            variable kwargs.
        filter_hidden (bool): Whether we should filter out arguments starting with 
            an underscore. Default True. This is often used for private arguments
            for example in the case of recursive functions that pass objects internally.
        doc (bool): Whether to merge the docstrings. Defaults to False.

    By having ``func_c`` trace its ``**kwargs`` signature, ``main`` can say that it's passing
    its arguments to ``func_c`` and it will be able to see the parameters of ``func_a`` & ``func_b``.

    .. code-block:: python

        @starstar.traceto(func_a, func_b)
        def func_c(**kw):
            kw_a, kw_b = starstar.divide(kw, func_a, func_b)
            func_a(**kw_a)
            func_b(**kw_b)

        @starstar.traceto(func_c, func_d)
        def main(**kw):
            kw_c, kw_d = starstar.divide(kw, func_c, func_d)
            func_c(**kw_c)
            func_d(**kw_d)

    ..
        .. note::
            I hope to have a way of tracing positional arguments to a single function as well. But it adds 
            more complexity to keyword dividing and I don't think it's worth it until we can flesh out 
            nice, organized, clearly defined, and intuitive behavior.

            e.g. what to do with this?

            .. code-block:: python

                def func_a(a, b, c): pass
                def func_b(b, c, d): pass
                def func_c(*a, **kw):
                    starstar.divide(a, kw, func_a, func_b)
                func_c(1, 2)  # should func_b get b=2 ???
                # if not, how can I pass b=2 to func_b ?
    '''
    # get parameters from source functions
    f_params = [_nested_cached_sig_params(f) for f in funcs]
    ps_all = [p for ps in f_params for p in ps.values()]
    if keep_varkw is None:  # check if any have varkw
        keep_varkw = any(p.kind == VAR_KW for p in ps_all)

    # remove private parameters (start with '_')
    if filter_hidden:
        ps_all = [p for p in ps_all if not p.name.startswith('_')]
    # remove duplicates
    ps = {p.name: p for p in ps_all if p.kind not in NOT_KW}
    # make the parameters kwonly
    other_ps = [p.replace(kind=KW_ONLY) for p in ps.values()]# if kw_only else list(ps.values())

    def decorator(func):
        # copy func
        @_builtin_wraps(func)
        def f(*a, **kw):
            return func(*a, **kw)

        # get signature from the decorated function
        sig = signature(f)
        params = tuple(sig.parameters.values())
        p_poskw = [p for p in params if p.kind in (POS_ONLY, POS_KW, VAR_POS, KW_ONLY)]
        p_varkw = [p for p in params if p.kind == VAR_KW]
        p_names = {p.name for p in params if p.kind not in VAR}
        other_ps_ = [p for p in other_ps if p.name not in p_names]

        if doc:
            f.__doc__ = _mergedoc(f.__doc__, funcs, other_ps_) #MergedDocstring(f.__doc__, funcs, other_ps_)

        # merge parameters and replace the signature
        f.__signature__ = sig.replace(parameters=(
            p_poskw + other_ps_ + (p_varkw if keep_varkw else [])))
        f.__starstar_traceto__ = funcs
        return f
    return decorator



def wraps(func: Callable, skip_args=(), skip_n=0) -> Callable:
    '''``functools.wraps``, except that it merges the signature.

    .. note::

        ``functools.wraps`` doesn't do any function introspection. This means
        that if the wrapper function adds any arguments to the function 
        signature, these arguments won't be documented.
    
    If you're not familiar with ``functools.wraps``, it is a decorator
    that renames a wrapper function and its signature to look like the 
    function that it's wrapping.

    .. code-block:: python

        # without wrapping

        def print_output(func):
            def inner(*a, print_output=True, **kw):
                output = func(*a, **kw)
                if print_output:
                    print(output)
                return output
            return inner

        @print_output
        def something(a, b):
            return a+b

        assert something.__name__ == 'inner'

        # with wrapping

        def print_output(func):
            @starstar.wraps(func)
            def inner(*a, print_output=True, **kw):
                output = func(*a, **kw)
                if print_output:
                    print(output)
                return output
            return inner

        @print_output
        def something(a, b):
            return a+b

        assert something.__name__ == 'something'
    '''
    wrap = _builtin_wraps(func)
    def decorator(wrapper):
        sig = _merge_signature(wrapper, func, skip_args, skip_n)
        f = wrap(wrapper)
        f.__signature__ = sig
        return f
    return decorator
# wraps.__doc__ += '\n\n\n' + _builtin_wraps.__doc__


def _merge_signature(wrapper, wrapped, skip_args=(), skip_n=0):
    '''Merge the signatures of a wrapper and its wrapped function.'''
    sig = signature(wrapped)
    sig_wrap = signature(wrapper)
    psposkw, psvarpos, pskw, psvarkw = _param_groups(sig, skip_args)
    pswposkw, _, pswkw, _ = _param_groups(sig_wrap)
    return sig.replace(parameters=(
        pswposkw + psposkw[skip_n or 0:] + psvarpos + pswkw + pskw + psvarkw))

def _param_groups(sig, skip_args=()):
    '''Return the parameters by their kind. Useful for interleaving.'''
    params = tuple(sig.parameters.values())
    if skip_args:
        skip_args = asitems(skip_args)
        params = [p for p in params if p.name not in skip_args]
    return (
        [p for p in params if p.kind in (POS_ONLY, POS_KW)],
        [p for p in params if p.kind == VAR_POS],
        [p for p in params if p.kind == KW_ONLY],
        [p for p in params if p.kind == VAR_KW])


def partial(__func, *a_def, **kw_def):
    '''``functools.partial``, except that it updates the signature and wrapper.
    
    known bug: kw defaults dont update in signature.
    '''
    @wraps(__func, skip_n=len(a_def))
    def inner(*a, **kw):
        return __func(*a_def, *a, **{**kw_def, **kw})
    return inner

# given signature and dict, produce *a, **kw

def as_args_kwargs(func, kw):
    '''Separate out positional and keyword arguments using a function's signature.

    Sometimes functions have position only arguments, but you still want to be able 
    to configure them in a single dictionary. In order to pass them to a function
    you need to separate them out first. This will separate out all arguments that 
    can be passed as positional arguments.
    
    Arguments:
        func (callable): The function that the arguments will be passed to.
        values (dict): The parameter values you want to pass to the function.
            NOTE: This value is not modified.

    Returns: 
        (tuple): A tuple containing
         - a (list): The positional arguments we could pull out.
         - kw (dict): The keyword args that are left over.

    .. code-block:: python

        def func_a(a, b, c, *, d=0):
            return a, b, c, d

        # split out the args and kwargs
        a, kw = starstar.as_args_kwargs(func_a, {'a': 1, 'b': 2, 'c': 3, 'd': 4})
        assert a == [1, 2, 3]
        assert kw == {'d': 4}

        # 
        assert func_a(*a, **kw) == (1, 2, 3, 4)
        
    '''
    sig = signature(func)
    pos = []
    kw = dict(kw)
    for name, arg in sig.parameters.items():
        if arg.kind == VAR_POS:
            pos.extend(kw.pop(arg.name, ()))
            pos.extend(kw.pop('*', ()))
            break
        if arg.kind not in (POS_ONLY, POS_KW) or name not in kw:
            break
        pos.append(kw.pop(name))
    return pos, kw

# get arguments matching a condition

def get_args(func, match=(), ignore=()):
    '''Get argument parameters matching a specific type.

    Arguments:
        func (callable): The function to inspect.
        match (int or set): Argument types to filter for.
        ignore (int or set): Argument types to filter out.

    Returns:
        (list): a list containing the matching parameter objects.
    
    .. code-block:: python

        def func(x, y=3, *a, z=4, **kw):
            pass

        # get all arguments
        args = starstar.get_args(func)
        assert all(isinstance(p, inspect.Parameter) for p in args)
        assert [p.name for p in args] == ['x', 'y', 'a', 'z', 'kw']

        # get positional arguments
        args = starstar.get_args(func, starstar.POS)
        assert [p.name for p in args] == ['x', 'y']

        # get arguments excluding *a, **kw
        args = starstar.get_args(func, ignore=starstar.VAR)
        assert [p.name for p in args] == ['x', 'y', 'z']

        # get keyword arguments
        args = starstar.get_args(func, ignore=starstar.KW)
        assert [p.name for p in args] == ['x', 'y', 'z']

        # get keyword only arguments
        args = starstar.get_args(func, ignore=starstar.KW_ONLY)
        assert [p.name for p in args] == ['z']
    '''
    match = (set(asitems(match)) or ALL) - set(asitems(ignore))
    return [p for p in signature(func).parameters.values() if p.kind in match]

# get required arguments

def required_args(func):
    '''Get the required arguments for a function.'''
    return [
        p for p in signature(func).parameters.values() 
        if p.default is inspect._empty and p.kind not in VAR
    ]

# filter kw dict using function signature

def filter_kw(func, kw, skip_n=0, pop=False, inverse=False, unmatched=False, include_varkw=True):
    '''Filter ``**kwargs`` down to only those that appear in the function signature.
    
    Arguments:
        func (callable): The function to filter using.
        kw: keyword arguments that you'd like to filter.
        pop (bool): Remove matched keys from kw.
        inverse (bool): Return keys not in function signature.
        include_varkw (bool): if a function takes **kw, should it 
            swallow all arguments? default True.

    Returns:
        (dict): the filtered ``kwargs``

    .. code-block:: python

        def func_a(a, b, c): 
            pass

        args = {'b': 2, 'c': 3, 'x': 1, 'y': 2}
        assert starstar.filter_kw(func_a, args) == {'b': 2, 'c': 3}
    '''
    ps = list(signature(func).parameters.values())[skip_n or 0:]
    varkw = include_varkw and next((True for p in ps if p.kind == VAR_KW), False)
    ks = set(kw)
    ps = {p.name for p in ps if p.kind in KW}
    if varkw:
        ps = ps|ks
    if unmatched:
        return ks - ps if inverse else ps - ks
    ks = ks - ps if inverse else ks & ps
    return {k: kw.pop(k) for k in ks} if pop else {k: kw[k] for k in ks}


def filtered(func):
    '''A decorator that filters out any extra kwargs passed to a function.
    See ``starstar.filter`` for more information.

    .. code-block:: python

        @starstar.filtered
        def func_a(a, b, c): pass

        func_a(1, 2, c=3, x=1, y=2)  # just gonna ignore x and y

        # using the decorator is equivalent to
        func_a(*a, **starstar.filter_kw(func_a, kw))
    '''
    @_builtin_wraps(func)
    def inner(*a, **kw):
        return func(*a, **filter_kw(func, kw))
    return inner


def kw2id(kw, *keys, key=True, sep='-', key_sep='_', filter=True, missing='', format=str):
    '''Create an id from keyword arguments.
    
    Arguments:
        kw (dict): The available arguments.
        *keys (str): The keys to use.
        key (bool): Include the key in the id?
        sep (str): The separator between each item.
        key_sep (str): The separator between key and value (if ``key=True``).
        filter (bool): Filter out missing values.
        format (callable): A function that formats the values.

    .. code-block:: python

        kw = {'name': 'asdf', 'count': 10, 'enabled': True}
        assert starstar.kw2id(kw, 'name', 'count', 'enabled', 'xxx') == 'name_asdf-count_10-enabled_True'
        assert starstar.kw2id(kw, 'name', 'xxx', 'count', filter=False) == 'name_asdf-xxx_-count_10'
    '''
    ki = ((k, kw.get(k, missing)) for k in keys if not filter or k in kw)
    return sep.join(f'{k}{key_sep}{format(i)}' if key else f'{i}' for k, i in ki)



def asitems(x, types=(list, tuple, set)):
    '''Convert a value into a list/tuple/set. Useful for arguments that can be ``None, single item, list, tuple``.

    .. code-block:: python

        assert starstar.asitems(None) == []
        assert starstar.asitems('asdf') == ['asdf']
        assert starstar.asitems([1, 2, 3]) == [1, 2, 3]
    '''
    return x if isinstance(x, types) else (x,) if x is not None else ()



from .dcp_nesteddoc import _mergedoc #  circular