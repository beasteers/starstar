Tutorial
=========

Passing arguments to multiple functions is as easy as: (:func:`starstar.traceto`, :func:`starstar.divide`)

.. code-block:: python

    import starstar

    def func_a(a=1, b=2, c=3): ...
    def func_b(x=8, y=9, z=10): ...

    @starstar.traceto(func_a, func_b)
    def main(**kw):
        kw_a, kw_b = starstar.divide(kw, func_a, func_b)
        func_a(**kw_a)
        func_b(**kw_b)



Have a decorator that splices in its own arguments? (:func:`starstar.wraps`)

.. code-block:: python

    import starstar

    def can_save(func):
        @starstar.wraps(func)
        def inner(*a, save=False, **kw):
            result = func(*a, **kw)
            if save:
                ...
            return result
        return inner

    @can_save
    def asdf(n, k=5):
        return np.random.random(n) * k

    assert asdf.__name__ == 'asdf'
    assert str(starstar.signature(asdf)) == '(n, k=5, *, save=False)'
    asdf(100, save=True)

Don't care if your function receives arguments its not supposed to get? (:func:`starstar.filtered`, :func:`starstar.filter_kw`)

.. code-block:: python

    import starstar

    @starstar.filtered
    def asdf(x, y):
        return x+y

    assert asdf(x=1, y=2, a=1, b=2, c=3, d=4) == 3

    kw = dict(x=1, y=2, a=1, b=2, c=3, d=4)
    assert starstar.filter_kw(asdf, kw) == dict(x=1, y=2)

Want to get a certain type of argument from a function signature? (:func:`starstar.get_args`)

.. code-block:: python

    import starstar

    def func(a, b, *xs, c):
        ...

    assert [p.name for p in starstar.get_args(func)] == ['a', 'b', 'xs', 'c']
    assert [p.name for p in starstar.get_args(func, starstar.POS)] == ['a', 'b']
    assert [p.name for p in starstar.get_args(func, starstar.KW)] == ['a', 'b', 'c']
    assert [p.name for p in starstar.get_args(func, starstar.KW_ONLY)] == ['c']
    assert [p.name for p in starstar.get_args(func, ignore=starstar.VAR)] == ['a', 'b', 'c']


Example X: You're training a machine learning model
-----------------------------------------------------------

Showcasing: :func:`starstar.traceto`, :func:`starstar.divide`

Scenario: You have a highly parameterized script that passes arguments to many places. Originally, you started duplicating all of the 
arguments from each function in the parent signature, but then you ended up with a fifteen line function signature with 
30+ arguments and as many duplicated default values.

A solution: Split the keyword arguments by analyzing each function's signature. In addition, modify 
the parent signature so that function introspection tools will know exactly which arguments 
the function takes, for example ``fire`` which uses a function's signature to create an 
automagical CLI.

.. code-block:: python

    import starstar

    def build_model(n_mels=128, output_size=128, n_channels=2, ...):
        ...

    def get_data_loader(n_channels=2, hop_size=0.1, n_mels=128, n_fft=512, ...):
        ...

    @starstar.traceto(build_model, get_data_loader)
    def main(**kw):
        kw_model, kw_data = starstar.divide(build_model, get_data_loader, kw)

        model = build_model(**kw_model)

        train_data = get_data_loader(**kw_data)

        model.fit(train_data)

    # now you use your auto-magical CLI creator
    if __name__ == '__main__':
        import fire
        fire.Fire(main)  # HAS THE COMBINED POWER OF BOTH SIGNATURES !!!!


Example X: You're managing a plugin system
----------------------------------------------

Showcasing: :func:`starstar.filtered`

Scenario: You have a collection of functions that you want to call using a single function.
You want each of these functions to be able to accept their own (arbitrary) arguments,
but you need the parent caller to be agnostic to which arguments are going to which function.

A solution: Decorate each callback function with a wrapper that will filter out any arguments 
that are not in the callback function's signature. That way each callback can ignore each other's 
arguments.

.. code-block:: python

    import starstar

    plugins = []

    def add_plugin(func):
        return plugins.append(starstar.filtered(func))

    def do_plugins(x, **kw):
        for func in plugins:
            func(x, **kw)

    # add two callbacks that have their own settings

    @add_plugin
    def save_file(x, format='json'):
        ...

    @add_plugin
    def plot_distribution(x, n_bins=30):
        ...

    def all_done(result, **kw):
        print('all done! just cleaning some stuff up')
        print('.. just doing some stuff...')
        do_plugins(result, **kw)

    # call the callbacks
    x = np.random.random(100)
    all_done(x, n_bins=10, format='csv')

Now you can have functions that take arbitrary arguments and those arguments will only be passed to the functions that need them.

Example X: You want to modify function default arguments from a configuration file
-------------------------------------------------------------------------------------

Showcasing: :func:`starstar.defaults`

Scenario: You've written a function, but its used in multiple places using the default values. You want to change the defaults,
but managing it in the source is cumbersome and you'd like to shift to using external configuration files.

A solution: Update the default function signature using a yaml configuration.

Your configuration:

.. code-block:: yaml

    model:
        n_fft: 2048

    n_epochs: 300


Your code:

.. code-block:: python

    import starstar

    @starstar.defaults
    def build_model(n_fft=2048, n_mels=128, output_size=128, n_channels=2, ...):
        pass

    def load_config():
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.load(f)

        build_model.update(**(config.pop('model', None) or {}))
        return config

    if __name__ == '__main__':
        cfg = load_config()

        ...


Example X: You want to nest another function's signature as a dict parameter. (like seaborn)
----------------------------------------------------------------------------------------------

Showcasing: :func:`starstar.nestdoc`

Scenario: You have keywords that you want to pass to multiple places, but you want to take a simpler approach
where the function accepts a dictionary for each function ``func_a_kw={...}`` which you can then pass to each 
nested function. However, you still want to be able to provide documentation for them in the parent docstring.

A solution: Pull the parameters from the children docstrings and splice them into the parent docstring.


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

    @starstar.nestdoc(funcA, b_kw=funcB)
    def funcC(funcA_kw=None, funcB_kw=None, **kw):
        """Hello"""

    print(funcC.__doc__)
    """
    Hello

    Args:
        funcA_kw (dict?): Keyword arguments for :func:`funcA`.
            
                - a (int): a from funcA
                - b (int): b from funcA
        b_kw (dict?): Keyword arguments for :func:`funcB`.
            
                - b (int): b from funcB
                - c (int): c from funcB
    """