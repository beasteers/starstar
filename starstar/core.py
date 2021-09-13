import inspect
from inspect import signature, Signature
from functools import wraps as builtin_wraps

POS_ONLY = inspect.Parameter.POSITIONAL_ONLY
KW_ONLY = inspect.Parameter.KEYWORD_ONLY
POS_KW = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POS = inspect.Parameter.VAR_POSITIONAL
VAR_KW = inspect.Parameter.VAR_KEYWORD
NOT_KW = {POS_ONLY, VAR_POS, VAR_KW}


def divide(kw, *funcs, overflow='strict', overflow_first=False):
    '''Divide kwargs between multiple functions based on their signatures.
    
    Arguments:
        overflow (str): How to handle extra keyword arguments.
             - 'separate': Add them as an extra dictionary at the end.
             - 'all': add extra keywords to all dicts that take var keywords.
             - 'first': add extra keywords to the first function with var keywords.
        strict (bool): throw a TypeError if there are unclaimed keywords.

    Returns:
        A dict for each function provided, plus one more for unused kwargs.
    '''
    pss = [_nested_cached_sig_params(f) for f in funcs]
    kws = [{} for _ in pss]
    kwunused = dict(kw)
    for ps, kwi in zip(pss, kws):
        for name in ps:
            if ps[name].kind in NOT_KW or name not in kw:
                continue
            kwi[name] = kw[name]
            kwunused.pop(name, None)

    if kwunused:
        found_varkw = False
        for ps, kwi in zip(pss, kws):
            if any(p.kind == VAR_KW for p in ps.values()):
                kwi.update(kwunused)
                found_varkw = True
                if overflow_first:
                    break
        if found_varkw:
            kwunused.clear()

    if overflow == 'separate':
        kws.append(kwunused)
    elif kwunused and overflow == 'strict':
        raise TypeError('Got unexpected arguments: {}'.format(tuple(kwunused)))

    return kws


def _nested_cached_sig_params(f):
    if isinstance(f, (list, tuple)):
        return {k: v for fi in f for k, v in _nested_cached_sig_params(fi).items()}
    return _cached_sig_params(f)
    
def _cached_sig_params(f):
    if isinstance(f, Signature):
        return f
    try:
        return getattr(f, '__divide_kw_stashed_params')
    except AttributeError:
        pass
    f.__divide_kw_stashed_params = p = signature(f).parameters
    return p


def traceto(*funcs, varkw=None, filter_hidden=True):
    '''Tell a function where its **kwargs are going!

    Arguments:
        *funcs (callable[]): The functions where the keyword arguments go.
        varkw (bool): Whether we should keep the varkw arg in the signature.
            If not set, this will be True if any of the passed arguments take 
            variable kwargs.
        filter_hidden (bool): Whether we should filter arguments starting with 
            an underscore. Default True.
    '''
    # names = [f.__name__ for f in funcs]

    # get parameters from source functions
    sigs = [_nested_cached_sig_params(f) for f in funcs]
    ps_all = [p for ps in sigs for p in ps.values()]
    if filter_hidden:
        ps_all = [p for p in ps_all if not p.name.startswith('_')]
    ps = {p.name: p for p in ps_all if p.kind not in NOT_KW}
    other_ps = [p.replace(kind=KW_ONLY) for p in ps.values()]
    # check if the function should still accept var kw
    if varkw is None:
        varkw = any(p.kind == VAR_KW for p in ps_all)

    def decorator(f):
        sig = signature(f)
        params = tuple(sig.parameters.values())
        p_poskw = [p for p in params if p.kind in (POS_ONLY, VAR_POS, KW_ONLY, POS_KW)]
        p_varkw = [p for p in params if p.kind == VAR_KW]

        params = (p_poskw + other_ps + (p_varkw if varkw else []))
        f.__signature__ = sig.replace(parameters=params)
        f.__starstar_source_funcs__ = funcs
        return f
    return decorator



def wraps(func):
    wrap = builtin_wraps(func)
    def decorator(wrapper):
        sig = _merge_signature(wrapper, func)
        f = wrap(wrapper)
        f.__signature__ = sig
        return f
    return decorator

def _merge_signature(wrapper, wrapped):
    sig_wrap = signature(wrapper)
    sig = signature(wrapped)
    psposkw, psvarpos, pskw, psvarkw = _param_groups(sig)
    pswposkw, _, pswkw, _ = _param_groups(sig_wrap)
    return sig.replace(parameters=(
        pswposkw + psposkw + psvarpos + pswkw + pskw + psvarkw))

def _param_groups(sig):
    params = tuple(sig.parameters.values())
    return (
        [p for p in params if p.kind in (POS_ONLY, POS_KW)],
        [p for p in params if p.kind == VAR_POS],
        [p for p in params if p.kind == KW_ONLY],
        [p for p in params if p.kind == VAR_KW])