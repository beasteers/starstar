import ast

def parse(value):
    """Parse a python literal from a string, allowing for some flexibilities in syntax.
    
    .. code-block:: python
    
        import starstar.parse.parse as ssparse
        assert ssparse('5') == 5
        assert ssparse('asdf') == 'asdf'
        assert ssparse('True') == True
        assert ssparse('None') == None
        assert ssparse('[1,2,3]') == [1, 2, 3]
        assert ssparse('[1,2,asdf]') == [1, 2, 'asdf']
        assert ssparse('{a:5}') == {'a': 5}
        assert ssparse('{a:[1,2,3]}') == {'a': [1, 2, 3]}
    """
    try:
        return _literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def _literal_eval(value):
    root = ast.parse(value, mode='eval')
    if isinstance(root.body, ast.BinOp):  # pytype: disable=attribute-error
        raise ValueError(value)

    for node in ast.walk(root):
        for field, child in ast.iter_fields(node):
            if isinstance(child, list):
                for index, subchild in enumerate(child):
                    if isinstance(subchild, ast.Name):
                        child[index] = _replacement(subchild)
            elif isinstance(child, ast.Name):
                node.__setattr__(field, _replacement(child))

    # supports: strings, bytes, numbers, tuples, lists, dicts, sets, booleans, and None
    return ast.literal_eval(root)


_BUILTIN = ('True', 'False', 'None')  # TODO: '...'
def _replacement(node):
  """Returns a node to use in place of the supplied node in the AST."""
  value = node.id
  return node if value in _BUILTIN else ast.Str(value)


if __name__ == '__main__':
    def testit(s, v):
        print(f'input: {s!r}')
        print(f'expected: {v!r}')
        print(f'got: {parse(s)!r}')
        print()

    def main():
        testit('5', 5)
        testit('asdf',  'asdf')
        testit('True',  True)
        testit('None',  None)
        testit('[1,2,3]',  [1, 2, 3])
        testit('[1,2,asdf]',  [1, 2, 'asdf'])
        testit('{a:5}',  {'a': 5})
        testit('{a:[1,2,3]}',  {'a': [1, 2, 3]})
    import fire
    fire.Fire(main)