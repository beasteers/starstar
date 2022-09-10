import functools
import starstar as ss


def _show_sig(func):
    return f'{func.__name__}{ss.signature(func)}'


def wraps():
    def ft_wrapper(func):
        @functools.wraps(func)
        def inner(*a, something=True, **kw):
            return func(*a, **kw)
        return inner

    @ft_wrapper
    def functools_wraps(a, b, k=5): pass

    def ss_wrapper(func):
        @ss.wraps(func)
        def inner(*a, something=True, **kw):
            return func(*a, **kw)
        return inner

    @ss_wrapper
    def starstar_wraps(a, b, k=5): pass

    print('what the function takes:', '(a, b, k=5, something=True)')
    print('with functools:', _show_sig(functools_wraps))
    print('with starstar:', _show_sig(starstar_wraps))

    starstar_wraps(1, 2, something=False)


def partial():
    def func(a, b, c=5, k=10):pass
    print('functools.partial(func, 1, 2, k=10)')
    print('with functools:', functools.partial(func, 1, 2, k=10))
    print()
    print('ss.partial(func, 1, 2, k=10)')
    print('with starstar:', _show_sig(ss.partial(func, 1, 2, k=10)))

def pickled():
    pass


if __name__ == '__main__':
    import fire
    fire.Fire()