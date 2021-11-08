import inspect
import copy
from inspect import signature as _builtin_signature, Signature as _Signature
from functools import wraps as _builtin_wraps, update_wrapper as _update_wrapper
import docstring_parser as dcp


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



# Needed for issue: https://github.com/rr-/docstring_parser/issues/61
def _build_meta(self, text, title):
    section = self.sections[title]

    if (
        section.type == dcp.google.SectionType.SINGULAR_OR_MULTIPLE
        and not dcp.google.MULTIPLE_PATTERN.match(text)
    ) or section.type == dcp.google.SectionType.SINGULAR:
        return self._build_single_meta(section, text)

    if ":" not in text:
        raise dcp.ParseError("Expected a colon in {}.".format(repr(text)))

    # Split spec and description
    before, desc = text.split(":", 1)
    if desc:
        desc = desc[1:] if desc[0] == " " else desc
        if "\n" in desc:
            lines = desc.splitlines(keepends=True)
            first_line, lines = lines[0], lines[1:]
            i = next((i for i, l in enumerate(lines) if l.strip()), 0)
            spaces = ''.join(lines[:i])
            rest = ''.join(lines[i:])
            desc = first_line + spaces + inspect.cleandoc(rest)
        desc = desc.strip("\n")

    return self._build_multi_meta(section, before, desc)
dcp.google.GoogleParser._build_meta = _build_meta



def divide(kw, *funcs, mode='strict', varkw=True):
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
        A dict for each function provided, plus one more for unused kwargs if ``overflow == 'separate'``.

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


def _nested_cached_sig_params(f):
    '''Get and merge signature parameters for potentially multiple functions.'''
    return {
        k: p for fi in _nested(f)
        for k, p in signature(fi).parameters.items()}
    # if isinstance(f, (list, tuple)):
    #     return {k: v for fi in f for k, v in _nested_cached_sig_params(fi).items()}
    # return signature(f).parameters

def _nested(xs):
    if isinstance(xs, (set, list, tuple)):
        for x in xs:
            yield from _nested(x)
        return
    yield xs


def signature(f):
    '''Get a function signature.
    
    Faster than inspect.signature (after the first call) because it 
    is cached using the standard ``f.__signature__`` attribute.
    '''
    if isinstance(f, _Signature):
        return f
    try:
        return f.__signature__
    except AttributeError:
        s = f.__signature__ = _builtin_signature(f)
        return s


def traceto(*funcs, keep_varkw=None, filter_hidden=True, doc=True):  # , kw_only=True
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
        doc (bool): Whether to merge the docstrings.

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



def wraps(func, skip_args=(), skip_n=0):
    '''``functools.wraps``, except that it merges the signature.'''
    wrap = _builtin_wraps(func)
    def decorator(wrapper):
        sig = _merge_signature(wrapper, func, skip_args, skip_n)
        f = wrap(wrapper)
        f.__signature__ = sig
        return f
    return decorator
wraps.__doc__ += '\n\n\n' + _builtin_wraps.__doc__


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


# def partial(__func, *a_def, **kw_def):
#     '''``functools.partial``, except that it updates the signature and wrapper.'''
#     @wraps(__func, skip_n=len(a_def))
#     def inner(*a, **kw):
#         return __func(*a_def, *a, **{**kw_def, **kw})
#     return inner


class _Defaults:
    def __init__(self, func, varkw=True, strict=False, frozen=None):
        self.function = func
        self.kw_defaults = {}

        _update_wrapper(self, func)
        sig = signature(func)
        ps = sig.parameters
        self.posargs = [k for k in ps if ps[k].kind in (POS_ONLY, POS_KW)]
        self.varkw = varkw and any(p.kind == VAR_KW for p in ps.values())
        self.strict = strict

        if func.__kwdefaults__ is None:
            func.__kwdefaults__ = {}
        self._backup = frozen or self._freeze()        

    def __str__(self):
        return '{}({}){}'.format(self.__class__.__name__, self.__name__, self.function.__signature__)

    def __call__(self, *a, **kw):
        pos = set(self.posargs[:len(a)])
        return self.function(*a, **{
            k: v for k, v in ({**self.kw_defaults, **kw}).items()
            if k not in pos
        })

    def update(self, **update):
        '''Update the function's defaults.'''
        update = update_defaults(self.function, **update)
        if update:
            if not self.varkw:
                raise TypeError('Unexpected arguments: {}'.format(set(update)))
            self.kw_defaults.update(update)
        return self

    def clear(self):
        '''Reset the function's defaults.'''
        self._restore(self._backup)
        return self

    def get(self):
        '''Get the function's defaults.'''
        return get_defaults(self.function)

    def _freeze(self):
        '''Get the current defaults/signature in case we want to restore back to this point.'''
        f = self.function
        return (signature(f), f.__defaults__, dict(f.__kwdefaults__), dict(self.kw_defaults))

    def _restore(self, frozen):
        '''Use the output of self._freeze() to restore to a previous set of defaults.'''
        f = self.function
        f.__signature__, f.__defaults__, f.__kwdefaults__, self.kw_defaults = frozen
        return self


def defaults(func, *a, **kw):
    '''Allow functions to have easily overrideable default arguments.
    Works with mixed positional and keyword arguments.

    This is a wrapper around ``update_defaults``, that also supports 
    default values for unnamed arguments (``**kwargs``).

    ``defaults(func).update`` will raise a ``TypeError`` if an extra 
    argument is passed, whereas ``update_defaults`` will return 
    the extra arguments.

    NOTE: This interface is not stable yet.

    .. code-block:: python 

        @starstar.defaults
        def abc(a=5, b=6):
            return a + b    

        assert abc() == 11
        abc.update(a=10)
        assert abc() == 16
        assert abc(2) == 8
    '''
    inner = lambda func: _Defaults(func, *a, **kw)
    return inner(func) if callable(func) else inner


def update_defaults(func, **update):
    '''Update a function's default arguments. Because functions don't 
    have a mechanism for defining default ``**kwargs``, this will return 
    any parameters not explicitly named in the signature. 

    TODO: should this be strict?

    .. code-block:: python 

        def abc(a=5, b=6):
            return a + b

        assert starstar.get_defaults(abc) == {'a': 5, 'b': 6}

        starstar.update_defaults(abc, b=7)

        assert starstar.get_defaults(abc) == {'a': 5, 'b': 7}
    '''
    sig = signature(func)
    ps = sig.parameters

    # update signature (do this before we pop)
    if set(ps) & set(update):
        func.__signature__ = sig.replace(parameters=[
            p.replace(default=update[k]) if k in update else p
            for k, p in ps.items()
        ])

    # update pos/poskw
    posargs = [k for k in ps if ps[k].kind in (POS_ONLY, POS_KW)]
    if func.__defaults__ and set(posargs) & set(update):
        func.__defaults__ = tuple(
            update.pop(name, current)
            for name, current in zip(posargs[::-1], func.__defaults__[::-1])
        )[::-1]

    # update kwonly/varkw
    kw_defaults = func.__kwdefaults__
    if kw_defaults and update:
        kw_defaults.update(
            (k, update.pop(k)) for k in set(update) if k in kw_defaults)

    # if not any(p.kind == VAR_KW for p in ps):  # 
    #     update.clear()
    return update


def get_defaults(func):
    '''Get the non-empty default arguments to a function (as a dict).
    
    .. code-block:: python 

        def abc(a=5, b=6):
            return a + b

        assert starstar.get_defaults(abc) == {'a': 5, 'b': 6}
    '''
    ps = ((k, p.default) for k, p in signature(func).parameters.items() if p.kind not in VAR)
    return {k: d for k, d in ps if d is not inspect._empty}


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
    return [p for k, p in signature(func).parameters.items() if p.kind in match]
#     return list(iargs_matching(func, match, ignore))
# def iargs_matching(func, match=(), ignore=()):
#     '''Get argument parameters matching a specific type (as a generator).'''
#     match = (set(asitems(match)) or ALL) - set(asitems(ignore))
#     return (p for k, p in signature(func).parameters.items() if p.kind in match)
# def group_args_matching(func, *matches, ignore=()):
#     '''Get argument parameters matching specific types.
    
#     This is equivalent to ``args_matching`` except it will 
#     pull out multiple groups of arguments.

#     .. code-block:: python

#         assert signature.args
#     '''
#     ignore = set(asitems(ignore))
#     matches = [set(asitems(m)) - ignore for m in matches or (ALL,)]
#     ps = signature(func).parameters.values()
#     return [[p for k, p in ps if p.kind in m] for m in matches]


def filter_kw(func, kw, include_varkw=True):
    '''Filter ``**kwargs`` down to only those that appear in the function signature.
    
    Arguments:
        func (callable): The function to filter using.
        **kw: keyword arguments that you'd like to filter.

    Returns:
        (dict): the filtered ``kwargs``

    .. code-block:: python

        def func_a(a, b, c): 
            pass

        args = {'b': 2, 'c': 3, 'x': 1, 'y': 2}
        assert starstar.filter_kw(func_a, args) == {'b': 2, 'c': 3}
    '''
    ps = signature(func).parameters
    if include_varkw and next((True for p in ps.values() if p.kind == VAR_KW), False):
        return kw
    ps = {k for k, p in ps.items() if p.kind in KW}
    return {k: v for k, v in kw.items() if k in ps}


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


def unmatched_kw(func, *keys, include_varkw=True, reversed=False):
    '''Returns keys that do not appear in the function signature.
    
    Arguments:
        func (callable): The function to filter using.
        *keys: keys that you'd like to check.
        include_varkw (bool): If True and the function accepts ``**kwargs``, it will assume 
            the function takes any kwargs. Default True.
        reversed (bool): If True, it will return the parameters from the function that
            do not appear in the provided keys. Default False.

    .. code-block:: python

        def func_a(a, b, c): 
            pass

        assert starstar.unmatched_kw(func_a, 'a', 'b', 'z') == {'z'}
        assert starstar.unmatched_kw(func_a, 'a', 'b', 'z', reversed=True) == {'c'}

        def func_b(a, b, c, **kw): 
            pass

        assert starstar.unmatched_kw(func_b, 'a', 'b', 'z') == set()
        assert starstar.unmatched_kw(func_b, 'a', 'b', 'z', reversed=True) == {'c'}
    '''
    ps = signature(func).parameters
    if include_varkw and not reversed and next((True for p in ps.values() if p.kind == VAR_KW), False):
        return set()
    ps = {k for k, p in ps.items() if p.kind in KW}
    ks = set(keys)
    return ps - ks if reversed else ks - ps


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


# # keep a record of your kwargs on disk (reproducability)
# def _save_kw(func, kw, keys=()):
#     import time, json
#     with open(f'{func.__name__}_{kw2id(kw, *keys) or "kw"}_{time.time()}.json', 'w') as f:
#         json.dump(kw, f)

# def _load_kw(func, kw, fname):
#     import json
#     with open(fname, 'r') as f:
#         return json.load(f)


# def save_kw(save=_save_kw, load=_load_kw):
#     '''Record the arguments passed to a function, including the function's defaults.
    
#     Also allows restoring arguments from a previous run using ``kw_restore='path/to/outputted.json'``
#     '''
#     def outer(func):
#         @wraps(func)
#         def inner(*a, kw_restore=False, **kw):  # 
#             pos = get_args(func, POS)
#             if kw_restore:
#                 kw.update(_load_kw(kw_restore))
#             d = get_defaults(func)
#             d.update(((p.name, x) for p, x in zip(pos, a)), **kw)
#             save(func, d)
#             return func(*a, **kw)
#         return inner
#     return outer


def asitems(x):
    '''Convert a value into a list/tuple/set. Useful for arguments that can be ``None, str, list, tuple``.

    .. code-block:: python

        assert starstar.asitems(None) == []
        assert starstar.asitems('asdf') == ['asdf']
        assert starstar.asitems([1, 2, 3]) == [1, 2, 3]
    '''
    return x if isinstance(x, (list, tuple, set)) else (x,) if x is not None else ()


# class Docstring:
#     def __init__(self, doc, merge=True):
#         self.doc = doc or ''
#         self.merge = merge
#         self._parsed = None

#     def compile(self):
#         return self.doc

#     def __str__(self):
#         if not self.merge:
#             return self.doc or ''
#         if self._parsed is None:
#             self._parsed = self.compile()
#         return str(self._parsed or '')

# class MergedDocstring(Docstring):
#     def __init__(self, doc, funcs, ps=None, **kw):
#         super().__init__(doc, **kw)
#         self.funcs = funcs or []
#         self.ps = ps
        
#     def compile(self):
#         return mergedoc(self.doc, self.funcs, self.ps)

# class NestedDocstring(Docstring):
#     def __init__(self, doc, funcs, **kw):
#         super().__init__(doc, **kw)
#         self.funcs = funcs or {}

#     def compile(self):
#         return nestdoc(self.doc, self.funcs)


def _mergedoc(doc, funcs, ps=None, style=None):
    import docstring_parser as dcp
    funcs = list(_nested(funcs))  # unravel nested functions

    if ps is None:
        ps = [p for f in funcs for p in signature(f)]

    parsed = dcp.parse(doc)
    docstrs = [dcp.parse(f.__doc__ or '') for f in funcs]
    docps = [{p.arg_name: p for p in d.params} for d in docstrs]

    # find the style from the first function that isn't just a description
    style = style or next(
        (d.style for d in [parsed]+docstrs if d.meta), 
        parsed.style)

    # hack to add a new line between description and parameters
    # if the main function doesn't have params of its own.
    if not parsed.meta:
        parsed.blank_after_long_description = True

    # add params to main docstring
    params = []
    existing = {p.arg_name for p in parsed.params}
    for p in ps:
        if p.name in existing:
            continue
        for d in docps:
            if p.name in d:
                existing.add(p.name)
                params.append(d[p.name])
                break

    # find the right place to splice in the params
    meta = parsed.meta
    i = next((
        i+1 for i, m in list(enumerate(meta))[::-1] 
        if isinstance(m, dcp.DocstringParam)), 0)
    parsed.meta = meta[:i] + params + meta[i:]
    return dcp.compose(parsed, style=style)


def _nestdoc(doc, funcs, style=None):
    
    def _indented_doc_args(func):
        dd = dcp.parse(func.__doc__)
        dd.long_description = ''
        dd.short_description = ''
        dd.blank_after_long_description = False
        dd.blank_after_short_description = False
        dd.meta = [m for m in dd.meta if m.args[0] == 'param']
        for m in dd.meta:
            m.arg_name = f' - {m.arg_name}'
        return '\n'.join(dcp.compose(dd).lstrip().splitlines()[1:])

    parsed = dcp.parse(doc)
    docstrs = {k: dcp.parse(f.__doc__ or '') for k, f in funcs.items()}

    # find the style from the first function that isn't just a description
    style = style or next(
        (d.style for d in [parsed]+list(docstrs.values()) if d.meta), 
        parsed.style)

    # hack to add a new line between description and parameters
    # if the main function doesn't have params of its own.
    if not parsed.meta:
        parsed.blank_after_long_description = True

    # add params to main docstring
    params = []
    current_params = parsed.params
    existing = {p.arg_name for p in current_params}

    # add arguments
    for key, func in funcs.items():
        if key in existing:
            for p in current_params:
                if p.name == key:
                    desc = p.description or f'Keyword arguments for :func:`{func.__name__}`.'
                    p.description = f'{desc}\n\n{_indented_doc_args(func)}'
                    p.type_name = p.type_name or 'dict'
                    break
        else:
            params.append(dcp.DocstringParam(
                ['param', f'{key} (dict)'], 
                f'Keyword arguments for :func:`{func.__name__}`.\n\n{_indented_doc_args(func)}',
                arg_name=key, type_name='dict', 
                is_optional=True, default=None))

    # find the right place to splice in the params
    meta = parsed.meta
    i = next((
        i+1 for i, m in list(enumerate(meta))[::-1] 
        if isinstance(m, dcp.DocstringParam)), 0)
    parsed.meta = meta[:i] + params + meta[i:]
    return dcp.compose(parsed, style=style)


def nestdoc(*funcs, template='{}_kw', **named):
    '''Nest a function's docstring parameters as a dict in another
    function's parameters.
    
    Arguments:
        *funcs: functions to nest. The argument name is gotten using ``template``.
        template (str): The keyword argument template for ``*funcs``. 
            Defaults to ``'{}_kw'`` where {} is replaced with ``f.__name__``.
        **named: functions to nest. The key is used as the argument name
            in the parent function.

    .. code-block:: python

        def funcA(a, b):
            """Another function
            
            Arguments:
                a (int): a from funcA
                b (int): b from funcA
            """

        def funcB(b, c):
            """Anotherrrr function
            
            Arguments:
                b (int): b from funcB
                c (int): c from funcB
            """


        def funcC(**kw):
            """Hello"""
        funcD = nested_doc(funcA, funcB)(funcC)

        print(funcD.__doc__)
        """
        Hello

        Args:
            funcA_kw (dict?): Keyword arguments for ``funcA``.
                
                    - a (int): a from funcA
                    - b (int): b from funcA
            funcB_kw (dict?): Keyword arguments for ``funcB``.
                
                    - b (int): b from funcB
                    - c (int): c from funcB
        """

    '''
    allfuncs = {}
    for f in funcs:
        allfuncs[template.format(f.__name__)] = f
    allfuncs.update(named)
    if not all(callable(f) for f in named.values()):
        raise TypeError("all functions must be callable")

    def inner(func):
        @_builtin_wraps(func)
        def func2(*a, **kw):  # copies func
            return func(*a, **kw)
        func2.__doc__ = _nestdoc(func.__doc__, allfuncs) #str(NestedDocstring(func.__doc__, named))
        return func2
    return inner



# def funcA(a, b):
#     '''Another function
    
#     Arguments:
#         a (int): blah
#         b (int): blallhak
#     '''

# def funcB(b, c):
#     '''Anotherrrr function
    
#     Arguments:
#         b (int): blah
#         c (int): blallhak
#     '''


# def funcC(**kw):
#     '''Hello
    
#     Arguments:
#         x: asdfasdf
            
            
#             asdfasdf
#             asdf
#     '''
# funcD = nestdoc(funcA, funcB)(funcC)
