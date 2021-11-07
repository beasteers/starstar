# starstar  ✨ ✨

[![pypi](https://badge.fury.io/py/starstar.svg)](https://pypi.python.org/pypi/starstar/)
![tests](https://github.com/beasteers/starstar/actions/workflows/ci.yml/badge.svg)
[![docs](https://readthedocs.org/projects/starstar/badge/?version=latest)](http://starstar.readthedocs.io/?badge=latest)
[![License](https://img.shields.io/pypi/l/starstar.svg)](https://github.com/beasteers/starstar/blob/main/LICENSE.md)

Finally! Variable keyword tracing in Python. 

Because this makes me sad:
```python
def main(**kw):
    function_with_a_bunchhhh_of_arguments(**kw)  # I only want to pass some of **kw !!
    another_function_with_a_bunchhhh_of_arguments(**kw)  # and put the other half here !!!

# hmmm let's see what can I pass to this function...
help(main)  # main(**kw)
# HALP????? aljdsflaksjdflkasjd
```
😖😭😭

And why can't we have: 🧞‍♀️ 🧚🏻‍♀️ ✨ ✨ 
```python
import starstar

def function_a(a=1, b=2, c=3): ...
def function_b(x=8, y=9, z=10): ...

@starstar.traceto(function_a, function_b)
def main(**kw):
    kw_a, kw_b = starstar.divide(kw, function_a, function_b)
    function_a(**kw_a)  # gets: a, b, c
    function_b(**kw_b)  # gets: x, y, z

# hmmm let's see what can I pass to this function...
help(main)  # main(a=1, b=2, c=3, x=8, y=9, z=10)
# yayyyy!!!
```
😇🥰🌈

Do you:
 - dislike repeating function arguments and their default values and therefore use `**kwargs` a lot?
 - sometimes need to pass `**kwargs` down to multiple functions, but hate that it requires enumerating all but one of the functions parameters?
 - wish that Python could look inside itself and figure it out for you?

`starstar` attempts to bridge the gap between nice, clean, and concise code (DRY ! EVER! <3) while maintaining informative introspectability of your functions. 

It also tries to do it as efficiently as it can internally by minimizing the amount of overhead added to the actual function calls and trying to use wrapper functions sparingly.

It can: 
 - look at function signatures and uses the parameters described to sort out kwargs into separate dictionaries for each function. (`divide(kw, *funcs)`)
 - modify a function's signature to include parameters from other functions that it wraps and sends its `**kwargs` to (`traceto(*funcs)`)
 - perform `functools.wraps`, while also preserving any arguments from the wrapper function in the signature (`wraps(func)(wrapper)`)

I really hope you find this useful! Please feel free to open issues if you have requests/suggestions cuz I want you to love this too!

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

### Bonus
#### `functools.wraps`, but better
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

And you can also skip certain positional or named arguments if the wrapper already provides them.
```python
import starstar

def deco(func):
    @starstar.wraps(func, skip_n=2, skip_args=('blah',))
    def inner(q, *a, **kw):
        return q, func(1, 2, *a, blah=17, **kw)
    return inner
```

#### Overriding function defaults
Say we want to change the default arguments for a function (e.g. we want to offload that configuration to a yaml config file). 

```python
import starstar

@starstar.defaults
def func_x(x, y=6):
    return x, y

import inspect
print(inspect.signature(func_x))  # <Signature (x, y=6)>

assert func_x(5) == 11
func_x.update(y=7)
assert func_x(5) == 12

import inspect
print(inspect.signature(func_x))  # <Signature (x, y=17)>
```

```python
import yaml

with open(config_file, 'r') as f:
    config = yaml.load(f)

func_x.update(**(config.get('func_x') or {}))
```

## Wishlist
 - merging docstrings? Idk might be too ambitious. 
   - We would just need a reliable docstring parser and it would probably be something that we'd want enabled lazily
   - merge seaborn-style kwarg routing in docstrings
 - tracing pos args? After some thought - this seems troublesome because I'm not sure how we'd deal with name conflicts between kwargs.
 - `traceto` allow skipping?
 - have a more concrete plan around keyword name collisions.
