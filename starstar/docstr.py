"""

.. note::
    
    It currently works for Google and Numpy docstrings, but it's still a bit of a WIP.

It tries its best to preserve the surrounding whitespace, and it will separate out
whitespace, below, above, and to the left (common indentation) of the text block, so 
you can edit the content of the block and the rest of it will be preserved.

.. code-block:: python

    from starstar.docstr import Google, Numpy

    doc = Google('''This is my docstring description.

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
    ''')

    # renders the docstring (looks the same as the input)
    print(doc)

    # see the breakdown of the different sections/parameters.
    print(repr(doc))

    doc['args'].append(doc.Param.new(
        'c', 'list', 
        'this is c, that holds some values.\\nsome more text.'))
    
    assert str(doc) == '''This is my docstring description.

    Args:
        a (str): this is a
        b (str): this is b
            yes its b
            yes b
        c (list): this is c, that holds some values.
            some more text.

    I'm some more docs

    Returns:
        dict: the special thing
        list: other

    alksdfj
    '''
"""
import re
# import copy
import inspect
import starstar as ss

# https://realpython.com/documenting-python-code/#docstring-types



class Block:
    '''This represents a block of text. This will separate out any leading or trailing blank lines
    as well as factor out the common indentation. This lets you safely modify the content of the
    block while preserving the surrounding whitespace. It also can use an optional section title
    with it's own separate indentation (like with google docstring sections).

    .. code-block:: python

        block = Block('\n\n\n    blah\n\n\n\n')
        block.body = ['blorg', 'blagh']
        assert str(block) == '\n\n\n    blorg\n    blagh\n\n\n\n'
    '''
    INDENT_WIDTH = 4
    def __init__(self, text, title=None, name=None, kind=None, cleandoc=False, end_newline=True, raw=False, indent=0):
        if cleandoc:  # NOTE: this fails if Block is given a list
            text = inspect.cleandoc(text)
        lines = aslines(text, end_newline=end_newline)
        leading, body, trailing, min_indent = ([],lines,[],None) if raw else separate_whitespace(lines)
        self.leading, self.body, self.trailing = leading, body, trailing

        # get the title/body indent offset
        min_indent = min_indent or 0
        title_indent = len(title) - len(title.lstrip()) if title else min_indent
        self.min_indent = min(title_indent, min_indent) + (indent or 0)
        self.child_indent = min_indent - title_indent
        # store everything
        self.kind = kind
        self.title = title = title.lstrip() if title else None
        self.name = name or title

    def __repr__(self):
        '''A string representation of the block that shows the 
        division of sections.
        '''
        return border(self._format_body(), f'{self.__class__.__name__}(name={self.name})')

    def __str__(self):
        '''The fully formatted string.'''
        return self._format_body()

    def __bool__(self):
        '''Checks if the block has any non-whitespace content. 
        Analogous to ``bool('    '.strip())``  
        '''
        return self.title or any(l.strip() for l in self.leading + self.body + self.trailing)

    def __eq__(self, other):
        '''Checks if the string representations are the same. Whitespace does count.'''
        return str(self) == str(other)

    def __iter__(self):
        '''Iterate over lines in the body. Does not include whitespace or title.'''
        return iter(self.body)

    # def format(self, mode='s'):
    #     '''Format the block. Equivalent to ``str(block)``.'''
    #     return self._format_body(mode=mode)

    def _format_body(self, body=None, mode='s'):
        body = self.body if body is None else aslines(body)
        if mode == 'r':  # allow drawing boxes around children
            body = [repr(l) if isinstance(l, Block) else l for l in body]
        # indent the body and make sure it ends with a new line
        body = [indent(str(l), self.min_indent + self.child_indent) for l in body]
        # join everything together
        return ''.join(
            ([indent(self.title, self.min_indent)] if self.title else []) + 
            self.leading + body + self.trailing)

    # lets you set body with a string.
    _body = None
    @property
    def body(self): return self._body
    @body.setter
    def body(self, value): self._body = aslines(value)


    def children(self, kind=..., name=..., include_self=False):
        '''Return children recursively matching some query.
        
        A block can contain other blocks, so this could be used to iterate over 
        all "Example" or "Arguments" blocks, for example.

        Arguments:
            kind (str): The block kind to match - e.g. ``'args'``, ``'returns'``
            name (str): The block name to match. This is the exact name of the section,
                So if you had a custom section ``My Examples:``, you'd enter ``'my examples'``.
                
        .. note::

            The difference between ``name`` and ``kind`` is that ``kind`` has recognized 
            sections with multiple variations and will normalize the name so a single string
            e.g. ``Arguments, Args => ARGS``. This makes it easier to search for all ARGS
            sections without having to check for each possible variation. ``name`` is there 
            when you want to search with the actual name of the section.
        '''
        if include_self and (kind != ... or self.kind == kind.upper()) and (name != ... or (self.name or '').lower() == name.lower()):
            yield self
        for b in self.body:
            if isinstance(b, Block):
                yield from b.children(kind, name, include_self=True)

    def first(self, kind=..., name=...):
        '''Return the first child matching a query. See ``children`` for arguments.'''
        return next(iter(self.children(kind, name)), None)

    def __getitem__(self, k):
        '''Return a direct child matching a name or index. Basically, you can 
        index like a list or a dict.
        '''
        return self.body[k] if isinstance(k, (int, slice)) else next((b for b in self.body if nocase(b.name, k)), None)

    def __delitem__(self, k):
        '''Delete a line from the Block.'''
        if isinstance(k, (int, slice)):
            del self.body[k]
        else:
            for i, b in enumerate(self.body):
                print(b.name, k, nocase(b.name, k))
                if nocase(b.name, k):
                    del self.body[i]
                    return
            raise KeyError(k)

    # basic manipulation

    def prepend(self, *x):
        '''Prepend lines to the body.'''
        self.body[0:0] = x
        return self

    def append(self, *x):
        '''Append lines to the body.'''
        self.body.extend(x)
        return self

    def indent(self, n=1, width=None):
        '''Indent the entire block.'''
        width = self.INDENT_WIDTH if width is None else width
        self.min_indent = max(self.min_indent + n * width, 0)
        return self

    def dedent(self, n=1, width=None):
        '''Dedent the entire block.'''
        return self.indent(-n, width)

    def set_indent(self, indent):
        if indent is not None:
            self.min_indent = indent
        return self

    # def strip(self): # XXX: THIS SHOULDNT HAPPEN INPLACE !!
    #     '''Strip whitespace from the block.'''
    #     self.leading, self.trailing = [], []
    #     return self

    def section_partition(self, pattern, get_kind=None, break_unnamed_sections=None):
        self.body = _section_partition(''.join(map(str, self.body)), pattern, get_kind, break_unnamed_sections)
        return self



class Param(Block):
    '''Represents the text belonging to a single parameter. 

    Most of this code is just to facilitate the parsing, 
    changing, and reformatting of the parameter data.
    '''
    _keys = ()
    _format=None
    pattern=None
    name = dtype = desc = None
    changed = False
    def __init__(self, text, can_be_unnamed=False, block_kind=None, **kw):
        self.__data = {}
        self.pattern = p = re.compile(self.pattern)
        self._keys = self._keys or [k for k, i in sorted(p.groupindex.items(), key=lambda x: x[1])]
        self._can_be_unnamed = can_be_unnamed
        self.block_kind = block_kind

        super().__init__(text + '\n' if not text.endswith('\n') else text, kind='PARAM', **kw)        

        # parse out the data
        m = re.match(p, ''.join(self.body) + '\n')
        self.__data = self.prepare(**(m.groupdict() if m else {}))
        self.__dict__.update(self.__data)
        self.changed = False

    def __setattr__(self, k, v):
        if k in self._keys:  # track changes
            self.__data[k] = v
            self.changed = True
        super().__setattr__(k, v)

    def update(self, **kw):  # update multiple
        if set(kw) - set(self._keys):
            raise TypeError(set(kw) - set(self._keys))
        self.__data.update(kw)
        self.__dict__.update(kw, changed=True)

    def _format_body(self, body=None, *a, **kw):
        if self.changed and body is None:  # the param text was changed - recompile the text
            self.body = self.format(**self.__data).splitlines(keepends=True)
            self.changed = False
        return super()._format_body(body, *a, **kw)

    def replace(self, **kw):
        return self.__class__(
            self.format(**dict(self.__data, **kw)), 
            can_be_unnamed=self._can_be_unnamed)

    @classmethod
    def new(cls, *a, **kw):
        return cls(cls.format(cls, *a, **kw))

    def prepare(self, **kw):
        return kw


class Docstring(Block):
    '''This represents an entire docstring with each section '''
    HEADER_GROUPS = dict(
        ARGS=["Arguments", "Args", "Parameters", "Params"],
        EXCEPT=["Raises", "Exceptions", "Except"],
        ATTRS=["Attributes"],
        EXAMPLE=["Example", "Examples"],
        RETURN=["Returns"],
        YIELD=["Yields"])
    SUPPORTS_PARAMS = ('ARGS', 'ATTRS')
    SUPPORTS_UNNAMED_PARAMS = ('RETURN', 'YIELD', 'EXCEPT')

    def __init__(self, doc=None, name=None):
        if callable(doc):
            name = name or doc.__name__
            doc = getattr(doc, '__doc__', None)
        self.doc = doc
        self.name = name

        super().__init__(doc or '', name=name, cleandoc=True, raw=True)
        self.parse()

    def __repr__(self):
        return border(self._format_body(mode='r'), f'{self.__class__.__name__}(name={self.name})')

    def parse(self):
        kinds = {v: k for k, vs in self.HEADER_GROUPS.items() for v in vs}

        self.body = body = _section_partition(
            ''.join(map(str, self.body)), 
            self.header_format.format("|".join(kinds)), 
            kinds.get, 
            self._break_unnamed_sections)
        for b in body:
            self.handle_section(b)
        return self

    def _break_unnamed_sections(self, body):
        return [body]

    def handle_section(self, block):
        if block.kind in self.SUPPORTS_UNNAMED_PARAMS:
            block.body = [self.Param(l, can_be_unnamed=True) for l in _group_indents(block.body)]
        elif block.kind in self.SUPPORTS_PARAMS:
            block.body = [self.Param(l) for l in _group_indents(block.body)]
        return block

    def children(self, *a, **kw):
        for p in self.body:
            yield from p.children(*a, **kw)

    def first(self, *a, **kw):
        return next(iter(self.children(*a, **kw)), None)

    def __getitem__(self, k):
        return self.body[k] if isinstance(k, (int, slice)) else next((b for b in self.body if nocase(b.name, k)), None)



class Google(Docstring):
    '''Google docstring parser.

    .. code-block:: python

        ds = Google("""This is my docstring description.

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

        .. code-block:: python

            print("this is something")

            print("hmm nice")


        ksnkdsjkdsksd ljksdfkjl
        asjkldf

        .. code-block:: python

            print("neat!")
        """)
    '''
    header_format = r'^({}):? *\n'

    def _break_unnamed_sections(self, body):
        '''This breaks of mid doc text (in between sections)'''
        return _break_minimum_indent(body)

    class Param(Param):
        '''The Google parameter format.

        .. code-block::

            {name} ({type}): {description}
        
        '''
        pattern = r'^ *(?P<name>\w*) *(?:\((?P<dtype>[^)]+)\))?: *(?P<desc>(?:\n|.)*)'
        def format(self, name=None, dtype=None, desc=None):
            return '{}: {}'.format(
                f'{name} ({dtype})' if name and dtype else name or dtype,
                # ' '.join(filter(None, [name, f'({dtype})' if dtype else None])), 
                indent(desc).lstrip(' '))

        def prepare(self, name=None, dtype=None, desc=None):
            # if self.block_kind != 'ARGS' and not dtype:
            #     name, dtype = None, name
            return dict(name=name, dtype=dtype, desc=inspect.cleandoc(desc or ''))


class Numpy(Docstring):
    '''Numpy docstring parser.

    .. code-block:: python

        ds = Numpy("""Gets and prints the spreadsheet's header columns

        Parameters
        ----------
        file_loc : str
            The file location of the spreadsheet
        print_cols : bool, optional
            A flag used to print the columns to the console (default is False)
            asjdfklasjdfkl

        Returns
        -------
        list
            a list of strings representing the header columns
        """)
    '''
    header_format = r'^({}) *\n[-=]+ *\n'

    def _break_unnamed_sections(self, body):
        return _break_full_newline(body)

    class Param(Param):
        '''The Numpy parameter format.

        .. code-block::

            {name} : {type}
                {description}
        
        '''
        pattern = r'^ *(?P<name>\w+) *(?:: *(?P<dtype>[^\n]+))? *\n(?P<desc>(?: +.*\n)*)'
        def format(self, name=None, dtype=None, desc=None):
            return '{}\n{}'.format(' : '.join(filter(None, [name, dtype])), indent(desc))


# block utils

def _break_sections(doc, pattern):
    '''Break text and body pairs for doc sections with headers.'''
    # find all matches
    matches = list(re.finditer(pattern, doc, flags=re.M))

    yield '', doc[:matches[0].start() if matches else None]
    for m1, m2 in zip(matches, matches[1:] + [None]):
        # select the title of the heading
        title = doc[m1.start():m1.end()]
        body = doc[m1.end():m2 and m2.start()]
        yield title, body

def _section_partition(doc, pattern, get_kind=None, break_unnamed_sections=None):
    sections = []
    for title, body in _break_sections(doc, pattern):
        # pull info from title
        name = re.match(pattern, title).group(1) if title else None
        kind = get_kind(name) if get_kind else None
        body, *others = break_unnamed_sections(body) if break_unnamed_sections else [body]

        sections.append(Block(body, title, name, kind=kind))
        for other in others:
            sections.append(Block(other))
    return sections


def _break_minimum_indent(section):
    '''Break indent when the indentation drops below the indentation of the first line.
    
    Example

    .. code-block:: rst

            arg1 (int): laksdfjklaj

        --- break here ---
        This is some discussion
    '''
    lines = section.splitlines(keepends=True)
    indent = next((
        len(l) - len(l.lstrip()) for l in lines 
        if l.strip()), None)
    if indent is None:
        return [lines]

    i_break = next((
        i for i, l in enumerate(lines) 
        if l.strip() and len(l) - len(l.lstrip()) < indent
    ), None)
    if i_break is None or i_break >= len(lines):
        return [lines]
    return [lines[:i_break], lines[i_break:]]


def _break_full_newline(section):
    '''Break after an entirely blank line'''
    lines = section.splitlines(keepends=True)
    i_start = next((i+1 for i, l in enumerate(lines) if l.strip()), None)
    i_break = next((i+1 for i, l in enumerate(lines) if i >= i_start and not l.strip()), None)
    if i_break is None or i_break >= len(lines):
        return [lines]
    return [lines[:i_break], lines[i_break:]]


def _group_indents(lines):
    '''Break into indentation groups (one for every top level group). e.g. google arguments.

    Example

    .. code-block:: rst

            arg1 (int): laksdfjklaj
                jasflkjdslkf
            --- break here ---
            arg2 (int): lkasdfjlaksdf
            --- break here ---
            arg3 (int): laksfdkjla
    '''
    indents = [len(l) - len(l.lstrip()) for l in lines]
    min_indent = min((i for i, l in zip(indents, lines) if l.strip()), default=0)
    tops = [i for i, (idt, l) in enumerate(zip(indents, lines)) if l.strip() and min_indent >= idt]
    groups = []
    if tops and tops[0]:
        groups.append(lines[:tops[0]])
    for i, j in zip([0] + tops, tops + [None]):
        if i != j:
            groups.append(lines[i:j])
    return [''.join(ls) for ls in groups]


# text utils

def indent(text, n=4):
    '''Indent a block of text'''
    return ''.join([' '*n + l for l in str(text).splitlines(keepends=True)])

def comment(text, ch='#'):
    '''Add a prefix to each line of a text block. Like commenting out code.'''
    return ''.join(f'{ch} {l}' for l in str(text).splitlines(keepends=True))

def border(text, title=None, top_ch='-', side_ch='|', n_top=3):
    '''Adds a border to the left and top sides, with an optional title.'''
    return top_ch * n_top + (f' {title} {top_ch}' if title else '') + '\n' + comment(text, side_ch)

def nocase(a, b):
    '''Compare two values case-insensitively.'''
    return (a.lower() if isinstance(a, str) else a) == (b.lower() if isinstance(b, str) else b)

def aslines(text, end_newline=True):
    '''Convert a block of text to lines, preserving new lines.'''
    lines = text.splitlines(keepends=True) if isinstance(text, str) else text or []
    if end_newline and lines and isinstance(lines[-1], str) and not lines[-1].endswith('\n'):
        lines[-1] = lines[-1] + '\n'
    return lines


# def separate_whitespace(lines):
#     '''Separate whitespace above, below, and common indentation for a block of text.'''
#     # break off the leading and trailing spaces
#     nonblank = [i for i, l in enumerate(lines) if l.strip()]
#     i, j = (nonblank[0], nonblank[-1]+1) if nonblank else (0,0)
#     leading, body, trailing = lines[:i], lines[i:j], lines[j:]

#     # separate off the indentation from the body / title
#     min_indent = min((
#         len(l) - len(l.lstrip()) for l in body 
#         if l.strip()), default=None)
#     body = [l[min_indent:] if l.strip() else l for l in body]
#     return leading, body, trailing, min_indent


def separate_whitespace(lines):
    '''Separate whitespace above, below, and common indentation for a block of text.'''
    # break off the leading and trailing spaces
    is_block = [isinstance(l, Block) for l in lines]
    has_content = [is_block[i] or bool(l.strip()) for i, l in enumerate(lines)]
    nonblank = [i for i, l in enumerate(lines) if has_content[i]]
    i, j = (nonblank[0], nonblank[-1]+1) if nonblank else (0,0)
    leading, body, trailing = lines[:i], lines[i:j], lines[j:]
    is_block, has_content = is_block[i:j], has_content[i:j]
    # print(leading, body, trailing)

    # separate off the indentation from the body / title
    min_indent = min((
        l.min_indent if is_block[i] else len(l) - len(l.lstrip()) 
        for i, l in enumerate(body) if has_content[i]), default=None)
    body = [
        l.set_indent(min_indent) if is_block[i] else 
        l[min_indent:] if has_content[i] else l
        for i, l in enumerate(body)
    ]
    return leading, body, trailing, min_indent


STYLES = {
    'google': Google(),
    'numpy': Numpy(),
}


# def _resub_groups(pattern, body, *a, **kw):  # FIXME: how to handle missing ???
#     '''Replace the content of regex capture groups.'''
#     p = re.compile(pattern, re.M) if not isinstance(pattern, re.Pattern) else pattern
#     names, idxs = map(list, zip(*sorted(p.groupindex.items(), key=lambda x: x[1])))
#     a = list(a) + [kw.pop(n, None) for n in names[len(a):]]

#     m = p.match(body)
#     joined = ''
#     for k, kj, x in zip(idxs, idxs[1:]+[None], a):
#         print('replacing', k and m.end(k), kj and m.start(kj), repr(str(x)), repr(body[k and m.end(k):kj and m.start(kj)]))
#         joined += f'{x}' + body[k and m.end(k):kj and m.start(kj)]
#     print('substituted:', repr(joined))
#     return joined


if __name__ == '__main__':

    ds = Google('''This is my docstring description.

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

    .. code-block:: python

        print("this is something")

        print("hmm nice")


    ksnkdsjkdsksd ljksdfkjl
    asjkldf

    .. code-block:: python

        print("neat!")
    ''').parse()

    ds['args'].append(ds.Param.new('somethingggg', None, 'kjlsadjkfdsajkl\ndfgad\nasdf'))
    ds['args'].append(ds.Param.new(None, 'dict', '819723789'))
    ds['args'].append(ds.Param.new(
        'nested_kw', 'dict', Block([
            # '\n', '\n',
            'nested parameters that go to somewhere else\n',
            ds.Param.new('a', 'int', 'aaa'),
            ds.Param.new('b', 'int', 'aaa'),
        ])))

    print(repr(ds))
    print(ds)

    ds2 = Google('''This is my docstring description.

    Args:
        x (str): this is x
        y: im y
          yes hi

    alksdfj
    ''').parse()

    ds['args'].append(*ds2['args'].body)

    ds['args']['somethingggg'].name = 'bsak'

    print(repr(ds))
    print(ds)

    # print(ds.compose())

    ds = Numpy('''Gets and prints the spreadsheet's header columns

    Parameters
    ----------
    file_loc : str
        The file location of the spreadsheet
    print_cols : bool, optional
        A flag used to print the columns to the console (default is False)
        asjdfklasjdfkl

    Returns
    -------
    list
        a list of strings representing the header columns
    ''').parse()

    ds['Parameters'].append(ds.Param.new('somethingggg', None, 'kjlsadjkfdsajkl\n  dfgad\n    asdf'))
    ds['Parameters'].append(ds.Param.new(None, 'dict', '819723789'))

    # print(ds.compose())
    print(repr(ds))
    ds['Parameters']['somethingggg'].name = 'bsak'
    p = ds['Parameters']['dict']
    p.name = 'bloop'
    p.desc = 'hello\nasdf'
    print(repr(p))
    print(ds)

    # print(ds.compose())
