from __future__ import annotations
import inspect
from functools import wraps as _builtin_wraps
import docstring_parser as dcp
from .core import signature, _nested

# Needed for issue: https://github.com/rr-/docstring_parser/issues/61
def _build_meta(self, text, title):
    section = self.sections[title]

    if (
        section.type == dcp.google.SectionType.SINGULAR_OR_MULTIPLE
        and not dcp.google.MULTIPLE_PATTERN.match(text)
    ) or section.type == dcp.google.SectionType.SINGULAR:
        return self._build_single_meta(section, text)

    if ":" not in text:
        raise dcp.ParseError("Expected a colon in {}.".format(repr(text)))

    # Split spec and description
    before, desc = text.split(":", 1)
    if desc:
        desc = desc[1:] if desc[0] == " " else desc
        if "\n" in desc:
            lines = desc.splitlines(keepends=True)
            first_line, lines = lines[0], lines[1:]
            i = next((i for i, l in enumerate(lines) if l.strip()), 0)
            spaces = ''.join(lines[:i])
            rest = ''.join(lines[i:])
            desc = first_line + spaces + inspect.cleandoc(rest)
        desc = desc.strip("\n")

    return self._build_multi_meta(section, before, desc)
dcp.google.GoogleParser._build_meta = _build_meta



# class Docstring:
#     def __init__(self, doc, merge=True):
#         self.doc = doc or ''
#         self.merge = merge
#         self._parsed = None

#     def compile(self):
#         return self.doc

#     def __str__(self):
#         if not self.merge:
#             return self.doc or ''
#         if self._parsed is None:
#             self._parsed = self.compile()
#         return str(self._parsed or '')

# class MergedDocstring(Docstring):
#     def __init__(self, doc, funcs, ps=None, **kw):
#         super().__init__(doc, **kw)
#         self.funcs = funcs or []
#         self.ps = ps
        
#     def compile(self):
#         return mergedoc(self.doc, self.funcs, self.ps)

# class NestedDocstring(Docstring):
#     def __init__(self, doc, funcs, **kw):
#         super().__init__(doc, **kw)
#         self.funcs = funcs or {}

#     def compile(self):
#         return nestdoc(self.doc, self.funcs)


def _mergedoc(doc, funcs, ps=None, style=None):
    import docstring_parser as dcp
    funcs = list(_nested(funcs))  # unravel nested functions

    if ps is None:
        ps = [p for f in funcs for p in signature(f).parameters.values()]

    parsed = dcp.parse(doc)
    docstrs = [dcp.parse(f.__doc__ or '') for f in funcs]
    docps = [{p.arg_name: p for p in d.params} for d in docstrs]

    # find the style from the first function that isn't just a description
    style = style or next(
        (d.style for d in [parsed]+docstrs if d.meta), 
        parsed.style)

    # hack to add a new line between description and parameters
    # if the main function doesn't have params of its own.
    if not parsed.meta:
        parsed.blank_after_long_description = True

    # add params to main docstring
    params = []
    existing = {p.arg_name for p in parsed.params}
    for p in ps:
        if p.name in existing:
            continue
        for d in docps:
            if p.name in d:
                existing.add(p.name)
                params.append(d[p.name])
                break

    # find the right place to splice in the params
    meta = parsed.meta
    i = next((
        i+1 for i, m in list(enumerate(meta))[::-1] 
        if isinstance(m, dcp.DocstringParam)), 0)
    parsed.meta = meta[:i] + params + meta[i:]
    return dcp.compose(parsed, style=style)


def _nestdoc(doc, funcs, style=None):
    
    def _indented_doc_args(func):
        dd = dcp.parse(func.__doc__)
        dd.long_description = ''
        dd.short_description = ''
        dd.blank_after_long_description = False
        dd.blank_after_short_description = False
        dd.meta = [m for m in dd.meta if m.args[0] == 'param']
        for m in dd.meta:
            m.arg_name = f' - {m.arg_name}'
        return '\n'.join(dcp.compose(dd).lstrip().splitlines()[1:])

    parsed = dcp.parse(doc)
    docstrs = {k: dcp.parse(f.__doc__ or '') for k, f in funcs.items()}

    # find the style from the first function that isn't just a description
    style = style or next(
        (d.style for d in [parsed]+list(docstrs.values()) if d.meta), 
        parsed.style)

    # hack to add a new line between description and parameters
    # if the main function doesn't have params of its own.
    if not parsed.meta:
        parsed.blank_after_long_description = True

    # add params to main docstring
    params = []
    current_params = parsed.params
    existing = {p.arg_name for p in current_params}

    # add arguments
    for key, func in funcs.items():
        if key in existing:
            for p in current_params:
                if p.name == key:
                    desc = p.description or f'Keyword arguments for :func:`{func.__name__}`.'
                    p.description = f'{desc}\n\n{_indented_doc_args(func)}'
                    p.type_name = p.type_name or 'dict'
                    break
        else:
            params.append(dcp.DocstringParam(
                ['param', f'{key} (dict)'], 
                f'Keyword arguments for :func:`{func.__name__}`.\n\n{_indented_doc_args(func)}',
                arg_name=key, type_name='dict', 
                is_optional=True, default=None))

    # find the right place to splice in the params
    meta = parsed.meta
    i = next((
        i+1 for i, m in list(enumerate(meta))[::-1] 
        if isinstance(m, dcp.DocstringParam)), 0)
    parsed.meta = meta[:i] + params + meta[i:]
    return dcp.compose(parsed, style=style)


def nestdoc(*funcs, template='{}_kw', **named):
    '''Nest a function's docstring parameters as a dict in another
    function's parameters.
    
    Arguments:
        *funcs: functions to nest. The argument name is gotten using ``template``.
        template (str): The keyword argument template for ``*funcs``. 
            Defaults to ``'{}_kw'`` where {} is replaced with ``f.__name__``.
        **named: functions to nest. The key is used as the argument name
            in the parent function.

    .. code-block:: python

        def funcA(a, b):
            """Another function
            
            Arguments:
                a (int): a from funcA
                b (int): b from funcA
            """

        def funcB(b, c):
            """Anotherrrr function
            
            Arguments:
                b (int): b from funcB
                c (int): c from funcB
            """


        def funcC(**kw):
            """Hello"""
        funcD = nested_doc(funcA, funcB)(funcC)

        print(funcD.__doc__)
        """
        Hello

        Args:
            funcA_kw (dict?): Keyword arguments for ``funcA``.
                
                    - a (int): a from funcA
                    - b (int): b from funcA
            funcB_kw (dict?): Keyword arguments for ``funcB``.
                
                    - b (int): b from funcB
                    - c (int): c from funcB
        """

    '''
    allfuncs = {}
    for f in funcs:
        allfuncs[template.format(f.__name__)] = f
    allfuncs.update(named)
    if not all(callable(f) for f in named.values()):
        raise TypeError("all functions must be callable")

    def inner(func):
        @_builtin_wraps(func)
        def func2(*a, **kw):  # copies func
            return func(*a, **kw)
        func2.__doc__ = _nestdoc(func.__doc__, allfuncs) #str(NestedDocstring(func.__doc__, named))
        return func2
    return inner



# def funcA(a, b):
#     '''Another function
    
#     Arguments:
#         a (int): blah
#         b (int): blallhak
#     '''

# def funcB(b, c):
#     '''Anotherrrr function
    
#     Arguments:
#         b (int): blah
#         c (int): blallhak
#     '''


# def funcC(**kw):
#     '''Hello
    
#     Arguments:
#         x: asdfasdf
            
            
#             asdfasdf
#             asdf
#     '''
# funcD = nestdoc(funcA, funcB)(funcC)
