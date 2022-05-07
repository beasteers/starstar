import sys
import re
import ast
import inspect

'''
data = {'a': 5, 'b': 6}
a, b, c = unpack(data, b=0, c=10)
assert a == 5 and b == 6 and c == 10

data = 5, 6
a, b, c = unpack(data, b=0, c=10)
assert a == 5 and b == 6 and c == 10


data = {'a': 5, 'b': 6}
a, (b, (c, d)), *c = unpack(data, b=0, c=10)
assert a == 5 and b == 6 and c == 10
'''

# https://stackoverflow.com/questions/58720279/python-inspect-stacks-code-context-only-returns-one-line-of-context


def _SYM(name):
    return '_AST_DESTRUCTURE_{}__'.format(name.upper())

_STAR = _SYM('star')


_FRAME_CACHE = {}
def assignedto(up=0, cache=True):
    '''Parse the assignment of a line of code and get the names of the assignment variables.
    
    Arguments:
        up (int): How many frames should we go up? If you wrap this function, it's recommended
            to pass in ``_up + 1`` where ``_up=0`` is an arguments that callers can provide 
            if they want to wrap your function.
        cache (bool): This can be (slightly) expensive especially if called repeatedly
            in a critical bit of code. By default, we cache the result of this value using
            the frame filename and line number. I realize this could break in some (?) situations
            so you have the ability to disable as needed. Keep in mind, when run repeatedly
            over time, it's about 26x slower than using caching (tested using 100k iters).

    Returns:
        (str, tuple): This will assign the names of the variables used for the assignment.
        
    .. note::

        This is less useful used on its own, and is more useful when used inside of wrapper 
        functions. See :func:`unpack` for a real example.

    .. code-block:: python

        # simple call

        x, y, z = assignedto()
        assert (x, y, z) == ('x', 'y', 'z')

        x, y, (a, (b, c)) = assignedto()
        assert (x, y, z, a, b, c) == ('x', 'y', 'z', 'a', 'b', 'c')

        # nested call

        def asdf(_up=0):
            return assignedto(_up+1)

        x, y, z = asdf()
        assert (x, y, z) == ('x', 'y', 'z')

        def asdf_flipped(_up=0):
            keys = assignedto(_up+1)
            return keys[::-1]

        x, y, z = asdf_flipped()
        assert (x, y, z) == ('z', 'y', 'x')

    Use it to define constants:

    .. code-block:: python

        OPEN, CLOSE = assignedto()

        something = 'OPEN'
        if something == OPEN: ...

    Or internal symbols:

    .. code-block:: python

        def tokens(_up=0):
            keys = assignedto(_up+1)
            return deep_apply(keys, '||| token: {} |||'.format)
        
        a, b = tokens()
        assert (a, b) == ('||| token: a |||', '||| token: b |||')
    '''
    frame = sys._getframe(up)
    func_name = frame.f_code.co_name
    frame = frame.f_back
    if cache:
        # XXX: Is this valid? From small tests it is, but idk
        c = frame.f_code
        i = c.co_filename, frame.f_lineno
        if i[0] and i in _FRAME_CACHE:
            return _FRAME_CACHE[i]
    lines, lnum = inspect.findsource(frame)

    # find the assignment ... = xxx.unpack
    statement = ''
    func_pattern = r'\s*\(*(?:[\w]+\.)*' + func_name + r'\(.*'
    assigned_func_pattern = r'(.+[^!<>])=' + func_pattern
    ilines = iter(lines[lnum:frame.f_lineno][::-1])
    for l in ilines:
        # find the last part of the assignment line (i.e. `) = assignedto()`)
        m = re.match(assigned_func_pattern, l)
        if m:
            statement = m.group(1)
            break
        # find an empty assignment (i.e. `assignedto()`)
        m = re.match(func_pattern, l)
        if m:
            return None

    # keep track of open / closed paretheses
    open_paras = sum(
        1 if c in '([' else -1 if c in ')]' else 0 for c in statement)
    if open_paras:
        for l in ilines:
            # if '=' in l: compute this line then break
            open_paras += sum(
                1 if c in '([' else -1 if c in ')]' else 0 for c in l)
            statement = l + statement
            if not open_paras:
                break

    keys = _literal_eval(f'{statement.strip()} = _')
    if cache:
        _FRAME_CACHE[i] = keys
    return keys


def unpack(data=None, *pos_defaults, _up_=0, _default_None_=True, _cached_assignment_=True, **defaults):
    '''Javascript-esque dict unpacking! Don't tell me you haven't wished this was possible before.

    Here's how you can do it with Javascript ES6

    .. code-block:: javascript

        const d = { a: 1, x: 1, y: 2 }
        const { a, b: 5, ...c } = d

    And here's the closest possible equivalent in Python (without hacking the literal grammar lol)!

    .. code-block:: python

        d = { 'a': 1, 'x': 1, 'y': 2 }

        a, b = starstar.unpack(d, b=5)
        assert (a, b) = (1, 5)

        # approximating the js spread operator
        a, b, *(c,) = starstar.unpack(d, b=5)
        assert (a, b, c) = (1, 5, { 'x': 1, 'y': 2 })

    The reason you need to use ``*(c,)`` and not just ``*c`` is because python
    will always assign a list to ``c`` when using the star operator, so instead
    we return ``[{...}]`` and therefore we need to do a quick destructure to get
    the dict from the single element list.

    Arguments:
        data (dict, iterable): The data to unpack. Most commonly this is a dict although it 
            also works for iterables. Unpacking iterables is already possible, but this 
            allows you to use default values.
        *pos_defaults (any): Default values (correspond to unpacked position).
        **defaults (any): Named default values.

    .. code-block:: python

        # unpack a dictionary

        d = {'a': 5, 'b': 6}

        a, b, c = unpack(d)
        assert (a, b, c) == (5, 6, None)

        a, b, c = unpack(d, c=10)
        assert (a, b, c) == (5, 6, 10)

        a, b, c = unpack(d, 1, 2, 3)
        assert (a, b, c) == (5, 6, 3)

        a, b, c = unpack({'a': 5}, 1, 2, 3)
        assert (a, b, c) == (5, 2, 3)

        # unpack a list

        a, b, c = unpack([5, 6], 1, 2, 3)
        assert (a, b, c) == (5, 6, 3)


    How is this possible ????

    Basically we:

     - parse the line(s) of code from the stack frame
     - crawl the preceeding lines of code until we find the beginning of the assignment. 
       For multi-line statements, this is done by finding the assignment ``) = (`` and
       continuing upward until the parentheses are balanced.
     - use ``ast`` to parse the left side of the assignment into a (nested) tuple of strings
       matching the format of the assignment.
     - cache the assignment tuple using the frame's filename and lineno for repeat calls.
     - use that nested tuple to pull out values from the dict/iterable in the format of the
       assignment, falling back to the supplied defaults.

    Conditions needed for this to work:

      - the left side must be a single assignment i.e. ``a, b, c = unpack({...})``, not ``x, y = a, b, c = unpack({...})``
      - the right side must be a single assignment i.e. ``a, b = unpack({...})``, not ``x, y = (a, b), c = unpack({...}), 2``
      - don't use backslashes for in-statement line breaks. I could technically fix it to support this,
        but honestly I'm not sure I want to condone such behavior anyways lol (just use parentheses !!)
    
    '''
    # parse the assignment from the current line of code
    keys = assignedto(_up_+1, _cached_assignment_)
    # assigned to a single value or not assigned at all
    if keys is None or isinstance(keys, str):
        return data
    # assigned to multiple values (a tuple)
    return _unpack(data, keys, pos_defaults, defaults, default_None=_default_None_)


def _unpack(data, keys, pos_defaults, defaults, default_None=True):
    # this is where the real magic happens !!
    if isinstance(data, dict):
        # unpack each key
        for i, k in enumerate(keys):
            # this doesn't make sense because there's no key
            # but this could be a way to do nested dict unpacking
            if isinstance(k, (list, tuple)):
                raise ValueError(k)
            # a, b, *rest = unpack() - like: { a, b, ...rest }
            if _STAR == k[:len(_STAR)]:
                yield {k: data[k] for k in set(data) - set(keys)}
                return
            # normal dict get key
            yield _get_dict_fallback(
                k, data, i, pos_defaults, defaults, 
                default_None=default_None)
        return

    # for recursive things (I think?)
    if isinstance(data, str):
        yield data
        return

    if data is None:
        return

    if isinstance(data, (list, tuple)):
        # unpack each item
        vals = iter(data)
        for i, k in enumerate(keys):
            # nested tuple
            if isinstance(k, (list, tuple)):
                try:
                    v = next(vals)
                except StopIteration:
                    v = [None]*len(k)
                yield _unpack(
                    v, k,
                    pos_defaults[i] if i < len(pos_defaults) else [],
                    defaults.get(k, {}), 
                    default_None=True)
            # a, b, *rest = unpack([1, 2, 3, 4, 5, 6])
            elif _STAR == k[:len(_STAR)]:
                yield from vals
            else:
                # normal values
                try:
                    yield next(vals)
                    continue
                except StopIteration:
                    # we ran out of values to yield
                    try:
                        yield pos_defaults[i]
                        continue
                    except IndexError:
                        pass
                    try:
                        yield defaults[k]
                        continue
                    except KeyError:
                        pass

                # if we want strict unpacking, raise an error if we run out of vaues
                if not default_None:
                    raise IndexError(k)
                yield None
        return

    yield data


def _get_dict_fallback(k, data, i, pos_defaults, defaults, default_None=True):
    try:
        return data[k]
    except KeyError:
        pass
    try:
        return pos_defaults[i]
    except IndexError:
        pass
    try:
        return defaults[k]
    except KeyError:
        pass
    if default_None:
        return None
    raise KeyError(k)


def _literal_eval(value):
    root = ast.parse(value, mode='exec')
    # get the last assignment expression
    assign = root.body[0]
    if not isinstance(assign, ast.Assign):
        return None
    root = assign.targets[0]
    if isinstance(root, (ast.List, ast.Tuple)):
        # replace all variables with strings
        for node in ast.walk(root):
            for field, child in ast.iter_fields(node):
                if isinstance(child, list):
                    for index, subchild in enumerate(child):
                        child[index] = _replacement(subchild)
                setattr(node, field, _replacement(child))
    else:
        root = _replacement(root)
    # convert ast to tuple
    return ast.literal_eval(root)


_BUILTINS = ('True', 'False', 'None')  # only builtin constants supported by literal_eval.
def _replacement(node, prefix=None):
    """Returns a node to use in place of the supplied node in the AST."""
    if isinstance(node, ast.Name):
        value = node.id
    elif isinstance(node, ast.Starred):
        node = node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            node = node.elts[0]
        return _replacement(node, prefix=_STAR)
    elif isinstance(node, ast.Constant):
        value = node.value
    else:
        return node
    if value in _BUILTINS:
        return node
    if prefix:
        value = prefix + value
    return ast.Str(value)



def deep_apply(x, func, *a, types=(list, tuple), **kw):
    '''Apply a function recursively, maintaining the input type.'''
    if isinstance(x, types):
        return type(x)(deep_apply(xi, func, *a, types, **kw) for xi in x)
    return func(x, *a, **kw)




if __name__ == '__main__':
    

    # Performance Check

    import time

    N = 100000
    data = {'a': 5, 'b': 6, 'x': 0, 'y': 1, 'z': 2}

    print('Baseline dict unpack assignment')
    print("a, b, c = data['a'], data['b'], {k: data[k] for k in set(data) - {'b','a'}}")
    t0 = time.time()
    for _ in range(N):
        a, b, c = data['a'], data['b'], {k: data[k] for k in set(data) - {'b','a'}}
    dtbase = (time.time() - t0)/N
    print(dtbase*N, dtbase)
    

    print('a, b, *(c,) = unpack(data, b=0, c=10)')
    t0 = time.time()
    for _ in range(N):
        a, b, *(c,) = unpack(data, b=0, c=10)
    dt = (time.time() - t0)/N
    print(dt*N, dt, dt/dtbase)

    print('a, b, *(c,) = unpack(data, b=0, c=10)', 'no cache')
    t0 = time.time()
    for _ in range(N):
        a, b, *(c,) = unpack(data, b=0, c=10, _cached_assignment_=False)
    dt = (time.time() - t0)/N
    print(dt*N, dt, dt/dtbase)

    import pyinstrument

    def asdf():
        a, b = unpack(data, b=0, c=10)

    print('Profiling:')
    prof = pyinstrument.Profiler()
    with prof:
        t0 = time.time()
        for _ in range(N):
            a, b, *(c,) = unpack(data, b=0, c=10)
        dt = (time.time() - t0)/N
        print(dt*N, dt, dt/dtbase)
    prof.print()

    print('----')
    (
        a,
        b, # adfasdfasdf
        c, d, e,
    ) = assignedto()
    print(a, b, c, d, e,)

    (
        a,
        b, # adfasdfasdf
        c, d, e,
    ) = unpack(data)
    print(a, b, c, d, e)