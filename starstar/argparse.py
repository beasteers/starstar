import argparse
import inspect
import starstar
from starstar import docstr

def make_parser(func, parser, docstyle=None, **kw):
    parser = parser or argparse.ArgumentParser(**kw)
    s = starstar.signature(func)
    docs = docstr.parse(func, style=docstyle)
    docargs = docs['args'] if docs else None

    for name, p in s.parameters.items():
        argnames = [f'--{name}']
        pkw = {}
        default = p.default
        if default == inspect._empty:
            pkw['required'] = True
        else:
            pkw['default'] = default

        for dp in docargs or []:
            if dp.name == name:
                helpmsg = dp.get('desc')
                if helpmsg:
                    pkw['help'] = helpmsg
                    break
        
        parser.add_argument(*argnames, **pkw)
