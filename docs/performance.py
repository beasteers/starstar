import inspect
import starstar
from starstar import unpack

N = 1000000

def time_signature(n=100000):
    heading('signature()')

    def funcA(a=1, b=1, c=1): pass

    def baseline():
        inspect.signature(funcA)

    def starstar_signature(**kw):
        starstar.signature(funcA)

    dtbase = timed(baseline, n=n)
    dt = timed(starstar_signature, n=n, compare=dtbase)


def time_divide(n=N):
    heading('divide()')

    def funcA(a=1, b=1, c=1): pass
    def funcB(x=1, y=1, z=1): pass

    def baseline(a=1, b=1, c=1, x=1, y=1, z=1):
        funcA(a, b, c)
        funcB(x, y, z)

    def divide(**kw):
        kwa, kwb = starstar.divide(kw, funcA, funcB)
        funcA(**kwa)
        funcB(**kwb)

    @starstar.traceto(funcA, funcB)
    def traced_divide(**kw):
        kwa, kwb = starstar.divide(kw, funcA, funcB)
        funcA(**kwa)
        funcB(**kwb)

    dtbase = timed(baseline, n=n)
    dt = timed(divide, compare=dtbase, n=n)
    dt = timed(traced_divide, compare=dtbase, n=n)


def time_unpack(n=N):
    heading('unpack()')

    data = {'a': 5, 'b': 6, 'x': 0, 'y': 1, 'z': 2}

    def baseline():
        a, b, c = (
            data.get('a'), data.get('b'), 
            {k: data[k] for k in set(data) - {'b','a'}})

    def unpack_test():
        a, b, *(c,) = unpack(data, b=0, c=10)

    dt = timed(baseline, n=n)
    dt = timed(unpack_test, compare=dt, n=n)
    


def heading(txt):
    print('*'*20)
    print()
    print(txt)
    print()
    print('*'*20)


def timed(__func, compare=None, n=N, source=None, **kw):
    import time

    # calculate the overhead of using this for loop
    t0 = time.time()
    for _ in range(N): pass
    overhead = (time.time() - t0)/N

    # get the 
    t0 = time.time()
    for _ in range(N):
        __func(**kw)
    dt = (time.time() - t0 - overhead)/N

    print('---')
    print(f'time for {__func.__name__} ({n} iters):')
    print(source or inspect.getsource(__func))
    print('===')
    print(f'{dt:.3g}s / iter', (f'({dt/compare:.3g}x slower)' if dt > compare else f'({compare/dt:.3g}x faster)') if compare else '')
    print('---')
    print()
    return dt



import pyinstrument

with pyinstrument.Profiler() as p:
    time_signature()
p.print()

with pyinstrument.Profiler() as p:
    time_divide()
p.print()

with pyinstrument.Profiler() as p:
    time_unpack()
p.print()