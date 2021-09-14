import inspect
from inspect import signature as builtin_signature, Signature
from functools import wraps as builtin_wraps, update_wrapper

POS_ONLY = inspect.Parameter.POSITIONAL_ONLY
KW_ONLY = inspect.Parameter.KEYWORD_ONLY
POS_KW = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POS = inspect.Parameter.VAR_POSITIONAL
VAR_KW = inspect.Parameter.VAR_KEYWORD
NOT_KW = {POS_ONLY, VAR_POS, VAR_KW}
KW = POS_KW, KW_ONLY


def divide(kw, *funcs, mode='strict', varkw=True):
    '''Divide kwargs between multiple functions based on their signatures.
    
    Arguments:
        overflow (str): How to handle extra keyword arguments.
             - ``'separate'``: Add them as an extra dictionary at the end.
             - ``'strict'``: If there are extra keyword arguments, raise a ``TypeError``. This 
               will only raise if no function with a variable keyword is found or ``varkw == False``.
        varkw (bool | 'first'): Do we want to pass extra arguments as ``**kwargs`` to any function 
            that accepts them? By default (True), they will go to all functions with variable keyword 
            arguments. If ``'first'`` they will only go to the first matching function. 


    Returns:
        A dict for each function provided, plus one more for unused kwargs if ``overflow == 'separate'``.
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
    if isinstance(f, (list, tuple)):
        return {k: v for fi in f for k, v in _nested_cached_sig_params(fi).items()}
    return signature(f).parameters


def signature(f):
    '''Get a function signature and save it for subsequent calls.'''
    if isinstance(f, Signature):
        return f
    try:
        return f.__signature__
    except AttributeError:
        s = f.__signature__ = builtin_signature(f)
        return s


def traceto(*funcs, keep_varkw=None, filter_hidden=True, kw_only=True):
    '''Tell a function where its **kwargs are going!

    Arguments:
        *funcs (callable[]): The functions where the keyword arguments go.
        posargs (callable): 
        keep_varkw (bool): Whether we should keep the varkw arg in the signature.
            If not set, this will be True if any of the passed arguments take 
            variable kwargs.
        filter_hidden (bool): Whether we should filter arguments starting with 
            an underscore. Default True.
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
    other_ps = [p.replace(kind=KW_ONLY) for p in ps.values()] if kw_only else list(ps.values())

    def decorator(f):
        # get signature from the decorated function
        sig = signature(f)
        params = tuple(sig.parameters.values())
        p_poskw = [p for p in params if p.kind in (POS_ONLY, POS_KW, VAR_POS, KW_ONLY)]
        p_varkw = [p for p in params if p.kind == VAR_KW]

        # merge parameters and replace the signature
        f.__signature__ = sig.replace(parameters=(
            p_poskw + other_ps + (p_varkw if keep_varkw else [])))
        f.__starstar_traceto__ = funcs
        return f
    return decorator



def wraps(func, skip_args=(), skip_n=0):
    '''``functools.wraps``, except that it merges the signature'''
    wrap = builtin_wraps(func)
    def decorator(wrapper):
        sig = _merge_signature(wrapper, func, skip_args, skip_n)
        f = wrap(wrapper)
        f.__signature__ = sig
        return f
    return decorator
wraps.__doc__ += '\n\nfunctools.wraps:\n' + builtin_wraps.__doc__


def _merge_signature(wrapper, wrapped, skip_args=(), skip_n=0):
    '''Merge the signatures of a wrapper and its wrapped function.'''
    sig = signature(wrapped)
    sig_wrap = signature(wrapper)
    psposkw, psvarpos, pskw, psvarkw = _param_groups(sig, skip_args)
    pswposkw, _, pswkw, _ = _param_groups(sig_wrap)
    return sig.replace(parameters=(
        pswposkw + psposkw[skip_n or 0:] + psvarpos + pswkw + pskw + psvarkw))

def _param_groups(sig, skip_args):
    '''Return the parameters by their kind. Useful for interleaving.'''
    params = tuple(sig.parameters.values())
    if skip_args:
        params = [p for p in params if p.name not in skip_args]
    return (
        [p for p in params if p.kind in (POS_ONLY, POS_KW)],
        [p for p in params if p.kind == VAR_POS],
        [p for p in params if p.kind == KW_ONLY],
        [p for p in params if p.kind == VAR_KW])



class _Defaults:
    def __init__(self, func, varkw=True, strict=False, frozen=None):
        self.function = func
        self.kw_defaults = {}

        update_wrapper(self, func)
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
        f = self.function
        f.__signature__, f.__defaults__, f.__kwdefaults__, self.kw_defaults = frozen
        return self


def defaults(func, *a, **kw):
    '''Allow functions to have easily overrideable default arguments.
    Works with mixed positional and keyword arguments.

    This is a wrapper around ``update_defaults``, that also supports 
    default values for unnamed arguments (**kwargs).

    NOTE: This interface is not stable yet. 

    >>> @starstar.defaults
    ... def abc(a=5, b=6):
    ...     return a + b

    >>> assert abc() == 11
    >>> abc.update(a=10)
    >>> assert abc() == 16
    >>> assert abc(2) == 8
    '''
    inner = lambda func: _Defaults(func, *a, **kw)
    return inner(func) if callable(func) else inner


def update_defaults(func, **update):
    '''Update a function's default arguments. Because functions don't 
    have a mechanism for defining default **kwargs, this will return 
    any parameters not explicitly named in the signature. 

    TODO: should this be strict?
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
    '''Get the non-empty default arguments to a function (as a dict).'''
    ps = ((k, p.default) for k, p in signature(func).parameters.items())
    return {k: d for k, d in ps if d is not inspect._empty}