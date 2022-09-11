import inspect
import starstar.docstr as ssd


# def clean(x):
#     return ''.join(xi[:-1].rstrip(' ')+xi[-1] for xi in str(x).splitlines(keepends=True))


def test_google():
    doc = '''This is my docstring description.

    Args:
        a (str): this is a
        b (str): this is b
            yes its b
            yes b

    I'm some more docs

    Returns:
        dict: the special thing
        list: other

    alksdfj
    '''

    ds = ssd.Google(doc)

    print(repr(str(ds)))
    assert str(ds) == inspect.cleandoc(doc) + '\n'

    p = ds.Param.new('c', 'int', 'this is\nan int.')
    pret = ds.Param.new('str', None, 'blah')

    ds['args'].append(p)
    ds['returns'].append(pret)

    assert str(ds) == inspect.cleandoc('''This is my docstring description.

    Args:
        a (str): this is a
        b (str): this is b
            yes its b
            yes b
        c (int): this is
            an int.

    I'm some more docs

    Returns:
        dict: the special thing
        list: other
        str: blah

    alksdfj
    ''') + '\n'

    del ds['args']['a']
    del ds['returns']['list']
    del ds['returns']['str']

    assert str(ds) == inspect.cleandoc('''This is my docstring description.

    Args:
        b (str): this is b
            yes its b
            yes b
        c (int): this is
            an int.

    I'm some more docs

    Returns:
        dict: the special thing

    alksdfj
    ''') + '\n'

    assert str(ds[2]) == "I'm some more docs\n\n"
    ds[2].body = 'aaaaaaaaa\ndocsdocsdocs\n'

    ds.body.insert(3, ssd.Block("well hi\n\n"))
    assert str(ds[3]) == "well hi\n\n"

    assert str(ds) == inspect.cleandoc('''This is my docstring description.

    Args:
        b (str): this is b
            yes its b
            yes b
        c (int): this is
            an int.

    aaaaaaaaa
    docsdocsdocs

    well hi

    Returns:
        dict: the special thing

    alksdfj
    ''') + '\n'


def module_items(*ms):
    import tqdm
    for m in ms:
        ks=dir(m)
        pb=tqdm.tqdm(ks, desc=m.__qualname__)
        for name in ks:
            try:
                f = getattr(m, name)
                doc = getattr(f, '__doc__', None)
                if doc:
                    yield getattr(f, '__qualname__', None) or name, doc
                    pb.update()
            except AttributeError:
                print('cant get', name)


import difflib

def cleandoc(doc):
    return '\n'.join(l.lstrip() and l for l in inspect.cleandoc(doc).splitlines())

def checkdiff(doc, **kw):
    doc1 = cleandoc(doc).rstrip('\n')
    d = ssd.parse(doc, **kw)
    doc2 = cleandoc(str(d)).rstrip('\n')
    # print(repr(d))
    assert doc1 == doc2, difflib.unified_diff(doc1.splitlines(), doc2.splitlines()) if doc1 == doc2 else ''

def test_numpy_module():
    try:
        import numpy as np
    except ImportError:
        pass
    for name, doc in module_items(np):
        checkdiff(doc, style='numpy')

def test_scipy_module():
    try:
        import scipy as sp
    except ImportError:
        pass
    for name, doc in module_items(sp):
        checkdiff(doc, style='numpy')

def test_fire_module():
    try:
        import fire
    except ImportError:
        pass
    for name, doc in module_items(fire):
        checkdiff(doc, style='google')

def test_ss_module():
    try:
        import starstar as ss
    except ImportError:
        pass
    for name, doc in module_items(ss):
        checkdiff(doc)
