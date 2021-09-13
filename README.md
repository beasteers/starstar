# starstar

Finally! Variable keyword tracing in Python.

Do you:
 - dislike repeating function arguments and their default values and therefore use `**kwargs` a lot?
 - sometimes need to pass `**kwargs` down to multiple functions, but hate that it requires enumerating all but one of the functions parameters?
 - wish that Python could look inside itself and figure it out for you?

`starstar` attempts to bridge the gap between nice, clean, and concise code (DRY ! <3) while maintaining informative introspectability of your functions.

It can: 
 - look at function signatures and uses the parameters described to sort out kwargs into separate dictionaries for each function. (`divide(kw, *funcs)`)
 - modify a function's signature to include parameters from other functions that it wraps and sends its `**kwargs` to (`traceto(*funcs)`)
 - perform `functools.wraps`, while also preserving any arguments from the wrapper function in the signature (`wraps(func)(wrapper)`)

## Install

```bash
pip install starstar
```

## Usage

### Pass arguments to multiple functions!
We have a function that wants to pass arguments to two different functions without having to enumerate those arguments in that function.
```python
import starstar

def func_a(a=None, b=None, c=None):
		return a, b, c

def func_b(d=None, e=None, f=None):
    return d, e, f

def main(**kw):
    kw_a, kw_b = starstar.divide(kw, func_a, func_b)
    func_a(**kw_a)
    func_b(**kw_b)
```



### Pass arguments to multiple functions down multiple levels!
Here we're passing it down two levels so we break up arguments for `func_a` and `func_b` into the first dictionary and `func_d` into the second.
```python
def func_c(**kw):
    kw_a, kw_b = starstar.divide(kw, func_a, func_b)
    func_a(**kw_a)
    func_b(**kw_b)

def func_d(g=None, h=None, i=None):
    return g, h, i

def main(**kw):
    kw_c, kw_d = starstar.divide(kw, (func_a, func_b), func_d)  # combine multiple functions into one kw dict
    func_c(**kw_c)
    func_d(**kw_d)
```

But we can even make this one step easier! Here we are modifying the signature of `func_c` to say that its arguments are sent to `func_a` and `func_b`.
```python
@starstar.traceto(func_a, func_b)
def func_c(**kw):
    kw_a, kw_b = starstar.divide(kw, func_a, func_b)
    func_a(**kw_a)
    func_b(**kw_b)

@starstar.traceto(func_c, func_d)
def main(**kw):
    kw_c, kw_d = starstar.divide(kw, func_c, func_d)
    func_c(**kw_c)
    func_d(**kw_d)
```
Which results in these signatures:
```python
import inspect
print(inspect.signature(func_c))
print(inspect.signature(main))
# (a=None, b=None, c=None, d=None, e=None, f=None)
# (a=None, b=None, c=None, d=None, e=None, f=None, g=None, h=None, i=None)
```

### `functools.wraps`, but better
Builtin `functools.wraps` doesn't consider the arguments to `inner` so its wrapped signature doesn't know about them which can be misleading for any tools that rely on accurate signatures.
```python
import functools

def deco(func):
    @functools.wraps(func)
    def inner(q, *a, **kw):
        return q, func(*a, **kw)
    return inner

@deco
def asdf(x, y, z):
    pass

import inspect
print(inspect.signature(asdf))  # (x, y, z)
```

But now it can!
```python
import starstar

def deco(func):
    @starstar.wraps(func)
    def inner(q, *a, **kw):
        return q, func(*a, **kw)
    return inner

@deco
def asdf(x, y, z):
    pass

import inspect
print(inspect.signature(asdf))  # (q, x, y, z)
```

## Wishlist
 - merging docstrings? Idk might be too ambitious.
 - tracing pos args?