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