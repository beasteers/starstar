import sys
import io
import pytest
import starstar.cli as sscli

def func(*a, **kw):
    return a, kw

def test_cli():
    # positional arguments
    assert sscli.main(func, args=[]) == ((), {})
    assert sscli.main(func, args=['1', '2', '3']) == ((1, 2, 3), {})

    # boolean
    assert sscli.main(func, args=['1', '2', '3', '--asdf']) == ((1, 2, 3), {'asdf': True})
    assert sscli.main(func, args=['1', '2', '3', '--no-asdf']) == ((1, 2, 3), {'asdf': False})

    # both space and equal sign assignment
    assert sscli.main(func, args=['1', '2', '3', '--asdf', 'hi']) == ((1, 2, 3), {'asdf': 'hi'})
    assert sscli.main(func, args=['1', '2', '3', '--asdf=hi']) == ((1, 2, 3), {'asdf': 'hi'})

    # as list
    assert sscli.main(func, args=['1', '2', '3', '--asdf', 'hi', 'hello']) == ((1, 2, 3), {'asdf': ['hi', 'hello']})
    assert sscli.main(func, args=['1', '2', '3', '--asdf=hi', 'hello']) == ((1, 2, 3), {'asdf': ['hi', 'hello']})


def test_multi_cli():
    def funcA(*a, **kw): return 'a', a, kw
    def funcB(*a, **kw): return 'b', a, kw

    # test help message
    with pytest.raises(SystemExit):
        sscli.main([funcA, funcB], args=[])

    # test case insensitive
    assert sscli.main([funcA, funcB], args=['funcA', '2']) == ('a', (2,), {})
    assert sscli.main([funcA, funcB], args=['funcB', '2']) == ('b', (2,), {})
    assert sscli.main([funcA, funcB], args=['funca', '2']) == ('a', (2,), {})
    assert sscli.main([funcA, funcB], args=['funcb', '2']) == ('b', (2,), {})
    assert sscli.main([funcA, funcB], args=['FUNCA', '2']) == ('a', (2,), {})
    assert sscli.main([funcA, funcB], args=['FUNCB', '2']) == ('b', (2,), {})

    # test help message after partial command spec
    with pytest.raises(SystemExit):
        sscli.main({'hey': [funcA, funcB]}, args=['hey'])

    # test nested
    assert sscli.main({'hey': [funcA, funcB]}, args=['hey', 'funcA']) == ('a', (), {})
    assert sscli.main({'hey': [funcA, funcB]}, args=['hey', 'funcB']) == ('b', (), {})



def module(name, doc=None, *a, **kw):
    m = type(sys)(name, doc)
    for f in a + tuple(kw.values()):
        f.__module__ = m.__name__

    m.__dict__.update(
        ((f.__name__.lower(), f) for f in a), 
        **{k.lower(): v for k,v in kw.items()})
    return m
        

# def test_as_funcs():
#     def funcA(*a, **kw): pass
#     def funcB(*a, **kw): pass
    
#     assert sscli._as_funcs(funcA) is funcA
#     assert sscli._as_funcs([funcA, funcB]) == {'funca': funcA, 'funcb': funcB}
#     assert sscli._as_funcs({'funcA': funcA, 'funcB': funcB}) == {'funca': funcA, 'funcb': funcB}

#     class A:
#         def funcA(self): pass
#         def funcB(self): pass

#     a = A()
#     assert sscli._as_funcs(a) == {'funca': a.funcA, 'funcb': a.funcB}

#     m = module('hello!', 'hiiii', funcA, funcB)
#     assert sscli._as_funcs(m) == {'funca': funcA, 'funcb': funcB}

#     assert 'test_as_funcs' in sscli._as_funcs(None, default_module_name=__file__.split('/')[-1].rsplit('.', 1)[0])



def test_parse():
    # basic types
    assert sscli.parse('1') == 1
    assert sscli.parse('"1"') == '1'
    assert sscli.parse('hi') == 'hi'

    # lists
    assert sscli.parse('[hi]') == ['hi']
    assert sscli.parse('[hi,hello]') == ['hi', 'hello']
    assert sscli.parse('[hi,[hello,2]]') == ['hi', ['hello', 2]]

    # dictionaries
    assert sscli.parse('{a:5}') == {'a': 5}
    assert sscli.parse('{a: 5}') == {'a': 5}
    assert sscli.parse('{"a": 5}') == {'a': 5}
    assert sscli.parse('{x:y,y:x}') == {'x': 'y', 'y': 'x'}

    # basic
    assert sscli.parse('None') == None
    assert sscli.parse('True') == True
    assert sscli.parse('False') == False


def test_shortkws():
    def func(aaaa, bbbb, hello):
        pass
    assert sscli.shortkws(func) == {'a': 'aaaa', 'b': 'bbbb', 'h': 'hello'}
    assert sscli.shortkws(func, n=2) == {'a': 'aaaa', 'b': 'bbbb', 'h': 'hello', 'aa': 'aaaa', 'bb': 'bbbb', 'he': 'hello'}
    assert sscli.shortkws(func, reserved=['h']) == {'a': 'aaaa', 'b': 'bbbb'}
    assert sscli.shortkws(func, ignore=['bbbb']) == {'a': 'aaaa', 'h': 'hello'}

    # doesn't work
    assert sscli.shortkws(func, reserved=['hello']) == {'a': 'aaaa', 'b': 'bbbb', 'h': 'hello'}
    assert sscli.shortkws(func, ignore=['b']) == {'a': 'aaaa', 'b': 'bbbb', 'h': 'hello'}

def test_accept_shortkws():
    @sscli.accept_shortkws
    def func(aaaa=1, bbbb=2, hello=3):
        return aaaa, bbbb, hello

    assert func(a=2, b=10, h=15) == (2, 10, 15)

    # test duplicate
    with pytest.raises(TypeError):
        func(a=2, aaaa=1)



def catch_output(*a, **kw):
    out, sys.stdout = sys.stdout, io.StringIO()
    try:
        sscli.main(*a, **kw)
        out = sys.stdout.getvalue()
        print(out)
        return out
    finally:
        sys.stdout = out


def test_format():
    def func(x): return x
    assert catch_output(func, args=["asdfasdfaf"]).strip() == 'asdfasdfaf'
    assert catch_output(func, args=["[1,asdf,{aaa:5}]"]).strip() == '''
1
asdf
{'aaa': 5}
    '''.strip()

    assert catch_output(func, args=['{aa:5,bb:6,c:10,d:{x:5,y:6}}']).strip() == '''
aa: 5
bb: 6
c: 10
d: {'x': 5, 'y': 6}
    '''.strip()

    def formatter(x, angry=False):
        if isinstance(x, dict):
            x = 'really, a dict?'
            if angry:
                x = x.upper() + '!!??!!'
        return x

    assert catch_output(func, format=formatter, args=['asdfadsfasdf']).strip() == 'asdfadsfasdf'
    assert catch_output(func, format=formatter, args=['{aa:5}']).strip() == 'really, a dict?'
    # assert catch_output(func, format=formatter, args=['{aa:5}', '--angry']).strip() == 'REALLY, A DICT?!!??!!'



def catch_help(*a, **kw):
    olderr, sys.stderr = sys.stderr, io.StringIO()
    try:
        with pytest.raises(SystemExit):
            sscli.main(*a, **kw)
        helpmsg = sys.stderr.getvalue()
        print(helpmsg)
        return helpmsg
    finally:
        sys.stderr = olderr

def test_help():
    def funcA(*a, **kw): 
        '''Hi Im funcA
        This is my docstring'''
    def funcB(*a, **kw):
        '''Hi Im funcB
        This is my docstring'''
    def funcC(*a, **kw): pass

    assert catch_help([funcA, funcB, funcC], args=[]).strip() == '''
Available:

    funcA: Hi Im funcA This is my docstring
     ட (*a, **kw)
    
    funcB: Hi Im funcB This is my docstring
     ட (*a, **kw)
    
    funcC: 
     ட (*a, **kw)
    '''.strip()

    assert catch_help({'hey': [funcA, funcB, funcC]}, args=[]).strip() == '''
Available:

    hey: 
    
        funcA: Hi Im funcA This is my docstring
         ட (*a, **kw)
        
        funcB: Hi Im funcB This is my docstring
         ட (*a, **kw)
        
        funcC: 
         ட (*a, **kw)
    '''.strip()

    assert catch_help({'hey': [funcA, funcB, funcC]}, args=['hey']).strip() == '''
Available:

    funcA: Hi Im funcA This is my docstring
     ட (*a, **kw)
    
    funcB: Hi Im funcB This is my docstring
     ட (*a, **kw)
    
    funcC: 
     ட (*a, **kw)
    '''.strip()

    assert catch_help({'hey': [funcA, funcB, funcC], '__doc__': 'hi Im a doc'}, args=[]).strip() == '''
hi Im a doc

Available:

    hey: 
    
        funcA: Hi Im funcA This is my docstring
         ட (*a, **kw)
        
        funcB: Hi Im funcB This is my docstring
         ட (*a, **kw)
        
        funcC: 
         ட (*a, **kw)
    '''.strip()


    class A:
        '''This is my class.'''
        def funcA(self):
            '''This is funcA'''
        def funcB(self):
            '''This is funcB'''
        def funcC(self): pass

    a = A()
    assert catch_help(a, args=[]).strip() == '''
This is my class.

Available:

    funcA: This is funcA
     ட ()
    
    funcB: This is funcB
     ட ()
    
    funcC: 
     ட ()
    '''.strip()