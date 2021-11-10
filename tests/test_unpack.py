import starstar


def test_unpack():
    data = {'a': 5, 'b': 6, 'x': 0, 'y': 1, 'z': 2}

    a, b = starstar.unpack(data)
    assert (a, b) == (5, 6)

    a, b, q = starstar.unpack(data)
    assert (a, b, q) == (5, 6, None)

    a, b, z = starstar.unpack(data)
    assert (a, b, z) == (5, 6, 2)

    a, b, *(c,) = starstar.unpack(data)
    assert (a, b, c) == (5, 6, {'x': 0, 'y': 1, 'z': 2})


def test_unpack_list():
    data = [1, 2, [3, [4]]]

    a, b = starstar.unpack(data)
    assert (a, b) == (1, 2)

    a, b, (c, (d,)) = starstar.unpack(data)
    assert (a, b, c, d) == (1, 2, 3, 4)

    a, b, c, d = starstar.unpack(data)
    assert (a, b, c, d) == (1, 2, [3,[4]], None)

    a, b, c, d = starstar.unpack(data, 1, 1, 1, 1, 1)
    assert (a, b, c, d) == (1, 2, [3,[4]], 1)


def test_unpack_multiline():
    (
        a, b, c) = starstar.unpack({})

    (
        a, b, c
    ) = starstar.unpack({})

    (
        a, 
        b, 
        c
    ) = starstar.unpack({})

    (
        a, 
        b, 
        c
    ) = starstar.unpack(
        
        {})


    (
        a, 
        b, 
        c
    ) = (starstar.unpack(
        
        {}))

def test_assignto():
    (
        a, 
        b, 
        c
    ) = starstar.assignedto()
    assert (a, b, c) == ('a', 'b', 'c')

    (




        a, 
        b, 


        (x, y, (z, q, w))
    ) = starstar.assignedto()
    assert (a, b, w, x, y, z, q) == ('a', 'b', 'w', 'x', 'y', 'z', 'q')