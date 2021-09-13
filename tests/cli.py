import starstar


def func_a(a=None, b=None, c=None):
		return a, b, c

def func_b(d=None, e=None, f=None):
    return d, e, f

def func_d(g=None, h=None, i=None):
    return g, h, i

@starstar.traceto(func_a, func_b)
def func_c(**kw):
    kw_a, kw_b = starstar.divide(kw, func_a, func_b)
    func_a(**kw_a)
    func_b(**kw_b)

@starstar.traceto(func_c, func_d)
def run(**kw):
    '''This is a test of starstar with a Fire CLI.
    
    You should see this message along with flags from [a-i].
    '''
    kw_c, kw_d = starstar.divide(kw, func_c, func_d)
    func_c(**kw_c)
    func_d(**kw_d)

if __name__ == '__main__':
    import fire
    fire.Fire(run)