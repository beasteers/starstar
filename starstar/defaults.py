from __future__ import annotations
import inspect
from functools import update_wrapper as _update_wrapper
from .core import signature, POS_ONLY, POS_KW, VAR_KW, VAR


class _Defaults:
    def __init__(self, func, varkw=True, strict=False, frozen=None):
        self.function = func
        self.kw_defaults = {}
        self.__name__ = getattr(func, '__name__', None)

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
