
import pytest
import inspect
import starstar


def test_divide():
    def b(a=None, b=None, c=None):
        return 'b', a, b, c

    def c(d=None, e=None, f=None, c=None):
        return 'c', d, e, f, c

    kw = dict(a='a', e='e')
    assert starstar.divide(kw, b, c) == [{'a': 'a'}, {'e': 'e'}]

    kw = dict(a='a', e='e', c='c')
    assert starstar.divide(kw, b, c) == [{'a': 'a', 'c': 'c'}, {'e': 'e', 'c': 'c'}]

    kwx = dict(a='a', e='e', zzz='zzz')
    with pytest.raises(TypeError):
        starstar.divide(kwx, b, c, mode='strict')
    assert starstar.divide(kwx, b, c, mode='separate') == [{'a': 'a'}, {'e': 'e'}, {'zzz': 'zzz'}]
    assert starstar.divide(kwx, b, c, mode=None) == [{'a': 'a'}, {'e': 'e'}]


    def b2(a=None, b=None, c=None, **kw):
        return 'b', a, b, c, kw

    def c2(d=None, e=None, f=None, **kw):
        return 'c', d, e, f, kw

    kwx = dict(a='a', e='e', zzz='zzz')
    assert starstar.divide(kwx, b2, c2, mode='strict') == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
    assert starstar.divide(kwx, b2, c2) == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
    assert starstar.divide(kwx, b2, c2, varkw=True) == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
    assert starstar.divide(kwx, b2, c2, varkw='first') == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e'}]
    assert starstar.divide(kwx, b2, c2, varkw=False, mode='ignore') == [{'a': 'a'}, {'e': 'e'}]
    assert starstar.divide(kwx, b2, c2, mode='separate') == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}, {}]


def test_signature():
    def b(a=None, b=None, c=None):
        return 'b', a, b, c

    insig = inspect.signature(b)
    sssig = starstar.signature(b)
    assert insig is not sssig
    assert insig == sssig
    assert inspect.signature(b) is starstar.signature(b)  # inspect is reading __signature__
    assert starstar.signature(b) is starstar.signature(b)
    # assert starstar.signature(sssig) is sssig


def test_core():
    def b(a=None, b=None, c=None):
        return 'b', a, b, c

    def c(d=None, e=None, f=None):
        return 'c', d, e, f
    
    @starstar.traceto(b, c)
    def a(aaa=None, **kw):
        kw_b, kw_c = starstar.divide(kw, b, c)
        return b(**kw_b), c(**kw_c)

    a_names = {'aaa', 'a', 'b', 'c', 'd', 'e', 'f'}
    assert set(a.__signature__.parameters) == a_names

    a_return = ('b', 'a', 'b', 'c'), ('c', 'd', 'e', 'f')
    assert a(**{x: x for x in a_names}) == a_return


    def x(x=None, y=None, z=None):
        return 'x', x, y, z

    @starstar.traceto(a, x)
    def asdf(**kw):
        kw_a, kw_x = starstar.divide(kw, (a, b, c), x)
        return a(**kw_a), x(**kw_x)

    asdf_names = a_names | {'x', 'y', 'z'}
    assert set(asdf.__signature__.parameters) == asdf_names

    asdf_return = a_return, ('x', 'x', 'y', 'z')
    assert asdf(**{x: x for x in asdf_names}) == asdf_return

    @starstar.traceto(a, x)
    def asdf2(**kw):
        kw_a, kw_x = starstar.divide(kw, a, x)
        return a(**kw_a), x(**kw_x)

    assert set(asdf2.__signature__.parameters) == asdf_names
    assert asdf2(**{x: x for x in asdf_names}) == asdf_return


def test_merge_docs():
    def aaa(x, y):
        '''aaa doc
        
        Arguments:
            x (int): x from aaa
            y (int): y from aaa
        '''

    def bbb(y, z):
        '''bbb doc
        
        Arguments:
            y (int): y from bbb
            z (int): z from bbb
        '''

    def main(**kw):
        '''main doc'''

    doc = str(starstar.traceto(aaa, bbb, doc=True)(main).__doc__)
    print(doc)
    assert doc.strip() == '''
main doc

Args:
    x (int): x from aaa
    y (int): y from aaa
    z (int): z from bbb
    '''.strip()

    def main(**kw):
        '''main doc
        
        Arguments:
            a (int): from main
            b (int): from main
        '''

    doc = str(starstar.traceto(aaa, bbb, doc=True)(main).__doc__)
    print(doc)
    assert doc.strip() == '''
main doc

Args:
    a (int): from main
    b (int): from main
    x (int): x from aaa
    y (int): y from aaa
    z (int): z from bbb
    '''.strip()


    def main(**kw):
        '''main doc
        
        Returns:
            (int): some number
        '''

    doc = str(starstar.traceto(aaa, bbb, doc=False)(main).__doc__)
    print(doc)
    assert cleandoc(doc) == cleandoc('''
main doc

        Returns:
            (int): some number
    '''.strip())

    doc = str(starstar.traceto(aaa, bbb, doc=True)(main).__doc__)
    print(doc)
    assert doc.strip() == '''
main doc

Args:
    x (int): x from aaa
    y (int): y from aaa
    z (int): z from bbb

Returns:
    (int): some number
    '''.strip()



    def funcA(a, b):
        '''Another function
        
        Arguments:
            a (int): blah
            b (int): blallhak
        '''

    def funcB(b, c):
        '''Anotherrrr function
        
        Arguments:
            b (int): blah
            c (int): blallhak
        '''

    def funcC(**kw):
        '''Hellooo'''


    def funcnewlines(**kw):
        '''Hello

        Args:
            x: asdfasdf

                asdfasdf
                asdf
        '''
    funcD = starstar.nestdoc(funcA, b_kw=funcB)(funcC)

    import docstring_parser as dcp
    doc_rec = dcp.compose(dcp.parse(funcnewlines.__doc__))

    # print(cleandoc(funcC.__doc__))
    # print(cleandoc(doc_rec))
    assert cleandoc(funcnewlines.__doc__) == cleandoc(doc_rec)

    print(funcD.__doc__)
    assert funcD.__doc__.strip() == '''
Hellooo

Args:
    funcA_kw (dict?): Keyword arguments for :func:`funcA`.
        
             - a (int): blah
             - b (int): blallhak
    b_kw (dict?): Keyword arguments for :func:`funcB`.
        
             - b (int): blah
             - c (int): blallhak
    '''.strip()

def cleandoc(doc):
    doc = inspect.cleandoc(doc)
    return '\n'.join(l.strip() if not l.strip() else l for l in doc.split('\n'))


def test_wraps():
    def a(x, y, *aaa, z, **kwaaa):
        pass

    @starstar.wraps(a)
    def asdf(q, *a, **kw):
        a(*a, **kw) + q

    assert tuple(inspect.signature(asdf).parameters) == ('q', 'x', 'y', 'aaa', 'z', 'kwaaa')

    @starstar.wraps(a, skip_n=1)
    def asdf(q, *a, **kw):
        a(q, *a, **kw)
    assert tuple(inspect.signature(asdf).parameters) == ('q', 'y', 'aaa', 'z', 'kwaaa')

    @starstar.wraps(a, skip_args='x')
    def asdf(q, *a, **kw):
        a(q, *a, **kw)
    assert tuple(inspect.signature(asdf).parameters) == ('q', 'y', 'aaa', 'z', 'kwaaa')


def test_defaults():
    @starstar.defaults
    def a():
        pass

    @starstar.defaults
    def a(x):
        return x
    with pytest.raises(TypeError):
        a()
    with pytest.raises(TypeError):
        a.update(y=10)
    # a.update(x=1)  # FIXME: TypeError: Unexpected arguments: {'x'}
    # assert a() == 1

    @starstar.defaults
    def a(x, y=6, *args, z=7, **kw):
        return x, y, z, kw

    print(a)

    assert a(5) == (5, 6, 7, {})
    assert a(10, 11, z=12) == (10, 11, 12, {})
    assert a.get() == {'y': 6, 'z': 7}

    assert tuple(inspect.signature(a).parameters) == ('x', 'y', 'args', 'z', 'kw')
    assert tuple(p.default for p in inspect.signature(a).parameters.values()) == (
        inspect._empty, 6, inspect._empty, 7, inspect._empty)

    a.update(x=8, z=13)

    assert a() == (8, 6, 13, {})
    assert a(10, 11, z=12) == (10, 11, 12, {})

    assert tuple(inspect.signature(a).parameters) == ('x', 'y', 'args', 'z', 'kw')
    assert tuple(p.default for p in inspect.signature(a).parameters.values()) == (
        8, 6, inspect._empty, 13, inspect._empty)

    a.clear()

    assert a(5) == (5, 6, 7, {})
    assert a(10, 11, z=12) == (10, 11, 12, {})

    assert tuple(inspect.signature(a).parameters) == ('x', 'y', 'args', 'z', 'kw')
    assert tuple(p.default for p in inspect.signature(a).parameters.values()) == (
        inspect._empty, 6, inspect._empty, 7, inspect._empty)


def test_as_akw():
    def func_a(a, b, c, *x, d=0):
            return a, b, c, d

    a, kw = starstar.as_args_kwargs(func_a, {'a': 1, 'b': 2, 'c': 3, 'd': 4})
    assert a == [1, 2, 3]
    assert kw == {'d': 4}

    a, kw = starstar.as_args_kwargs(func_a, {'a': 1, 'b': 2, 'c': 3, 'x': [6,6,6], '*': [7,7,7], 'd': 4})
    assert a == [1, 2, 3, 6, 6, 6, 7, 7, 7]
    assert kw == {'d': 4}

    def func_a(a, b, c, *, d=0): 
        return a, b, c, d

    a, kw = starstar.as_args_kwargs(func_a, {'a': 1, 'b': 2, 'c': 3, 'd': 4})
    assert a == [1, 2, 3]
    assert kw == {'d': 4}


def test_kw_filtering():
    def func_a(a, b, c): 
        return a+b+c
    
    kw = dict(b=2, c=3, x=1, y=2)
    assert starstar.filter_kw(func_a, kw) == {'b': 2, 'c': 3}

    assert starstar.filter_kw(lambda b, **kw: kw, kw) == kw

    func_a1 = starstar.filtered(func_a)
    func_a1(1, 2, c=3, x=1, y=2)  # just gonna ignore x and y

    assert starstar.unmatched_kw(func_a1, 'a', 'b', 'z') == {'z'}
    assert starstar.unmatched_kw(func_a1, 'a', 'b', 'z', reversed=True) == {'c'}

    def func_b(a, b, c, **kw): 
        return a+b+c, kw
    assert starstar.unmatched_kw(func_b, 'a', 'b', 'z') == set()
    assert starstar.unmatched_kw(func_b, 'a', 'b', 'z', reversed=True) == {'c'}


def test_get_args():
    def func(a, b, *xs, c):
        ...

    assert [p.name for p in starstar.get_args(func)] == ['a', 'b', 'xs', 'c']
    assert [p.name for p in starstar.get_args(func, starstar.POS)] == ['a', 'b']
    assert [p.name for p in starstar.get_args(func, starstar.KW)] == ['a', 'b', 'c']
    assert [p.name for p in starstar.get_args(func, starstar.KW_ONLY)] == ['c']
    assert [p.name for p in starstar.get_args(func, ignore=starstar.VAR)] == ['a', 'b', 'c']


def test_kw2id():
    kw = {'name': 'asdf', 'count': 10, 'enabled': True}
    assert starstar.kw2id(kw, 'name', 'count', 'enabled', 'xxx') == 'name_asdf-count_10-enabled_True'
    assert starstar.kw2id(kw, 'name', 'xxx', 'count', filter=False) == 'name_asdf-xxx_-count_10'