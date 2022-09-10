import os
import inspect

l_= lambda *x, sep=' ': sep.join(str(x) for x in x if x)
b_ = lambda *x, sep='\n': l_(*x, sep=sep)
fw_ = lambda *x, w=20, right=False: f"{l_(*x):{'>' if right else '<'}{w}}"
bb_ = lambda *x, ch='-', n=20: b_(ch*n, *x, ch*n)

def tbl_(*rows, buffer=2):
    rows = [[str(c) for c in cs] for cs in rows]
    widths = [max((len(c) for c in cs), default=0) for cs in zip(*rows)]
    return b_(*(l_(*(fw_(c, w=w + buffer-1) for c, w in zip(cs, widths))) for cs in rows))

def _filter_stack(stack, match=None, stop=None, offset=0, limit=None):
    if isinstance(stop, str):
        stopstr, stop = stop, lambda f: stopstr == f.function
    elif stop is None:
        stop = lambda f: False
    else:
        stopframe, stop = stop, lambda f: stopframe == f
    if isinstance(match, str):
        includestr, match = match, lambda f: (
            includestr == f.function or
            includestr in f.filename)

    x = []
    for i, f in enumerate(stack[offset+1:][:limit]):
        if match and not match(f): continue
        if stop(f): break
        x.append(f)
    return x

def format_stack(message=None, match=None, stop=None, offset=0, limit=None):
    '''Format the current stack trace.'''
    return bb_(message, tbl_(*(
        (f.function, f.lineno, f.filename, f'>>> {f.code_context[0].strip()}')
        if i else 
        (f.function, f.lineno, f.filename, '')
        for i, f in enumerate(_filter_stack(
            inspect.stack(), match, stop, offset=offset, limit=limit))
    )))

def print_stack(*a, offset=0, **kw):
    '''Print out the current stack trace.'''
    print(format_stack(*a, offset=offset + 1, **kw), flush=True)


def short_stack(match=None, file=False, sep=' << ', format='{}', stop=None, offset=0, n=None):
    '''get a compressed view of the stack.'''
    return sep.join(
        format.format(f'{f.function} ({os.path.basename(f.filename)}:{f.lineno})' if file else f.function)
        for f in _filter_stack(inspect.stack(), match, stop, offset+1, n)
    )

def funcstr(func, *a, **kw):
    return '{}({})'.format(func.__name__, ', '.join(
        ['{!r}'.format(v) for v in a] +
        ['{}={!r}'.format(k, v) for k, v in kw.items()]
    ))

def excline(e):
    return '{}: {}'.format(type(e).__name__, e)






if __name__ == '__main__':
    def aaa(**kw):
        bbb(**kw)
    def bbb(**kw):
        ccc(**kw)
    def ccc(**kw):
        print_stack(**kw)

    def nested(func, *a, N=3, **kw):
        if N>0:
            return nested(func, *a, N=N-1, **kw)
        func(*a, **kw)

    def main():
        aaa()
        aaa(match='debug')
        aaa(stop=inspect.stack()[0])
        nested(lambda: print(short_stack()))
        nested(lambda: print(short_stack(match='debug.py')))
        nested(lambda: print(short_stack(stop='main')))
    import fire
    fire.Fire(main)