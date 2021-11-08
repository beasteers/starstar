.. starstar documentation master file, created by
   sphinx-quickstart on Thu Nov  4 13:54:59 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

starstar  ✨ ✨
===============

Finally! Variable keyword tracing in Python. 

Because this makes me sad:

.. code-block:: python

   def main(**kw):
      function_with_a_bunchhhh_of_arguments(**kw)  # I only want to pass some of **kw !!
      another_function_with_a_bunchhhh_of_arguments(**kw)  # and put the other half here !!!

   # hmmm let's see what can I pass to this function...
   help(main)  # main(**kw)
   # HALP????? aljdsflaksjdflkasjd

😖😭😭

And why can't we have: 🧞‍♀️ 🧚🏻‍♀️ ✨ ✨ 

.. code-block:: python

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

😇🥰🌈

Installation
---------------

.. code-block:: bash

   pip install starstar


.. toctree::
   :maxdepth: 2
   :titlesonly:
   :hidden:

   self


.. Quick Reference
.. -----------------


.. .. code-block:: python

..    def func_a(a=None, b=None, c=None):
..       return a, b, c

..    def func_b(b=None, c=None, d=None):
..       return b, c, d

.. .. code-block:: python

..    # divide:

..    # a) all kw match

..    kw = {'a': 5, 'b': 6, 'd': 8}
..    kw_a, kw_b = starstar.divide(kw, func_a, func_b)
..    # {'a': 5, 'b': 6}, {'b': 6, 'd': 8}


..    # b) receive extra argument "x"

..    kw = {'a': 5, 'b': 6, 'd': 8, 'x': 2}
..    kw_a, kw_b = starstar.divide(kw, func_a, func_b)
..    # raise TypeError('Unexpected argument: {"x"}')


..    # c) receive extra argument and set it aside

..    kw_a, kw_b, kw_extra = starstar.divide(kw, func_a, func_b, mode='separate')
..    # {'a': 5, 'b': 6}, {'b': 6, 'd': 8}, {'x': 2}

.. .. code-block:: python

..    @starstar.traceto(func_a, func_b)
..    def func_c(**kw):
..       ...

   


.. toctree::
   :maxdepth: 1
   :caption: Getting Started:

   tutorial

.. toctree::
   :maxdepth: 1
   :caption: API documentation

   essentials
   getting_args
   defaults
   utils
   docs

Contributions
=================

If you have feature requests or ideas on how to make this package better, please
open an issue! 

This package covers a Python pain point that I've been wanting a solution for
for a while now, and until now, I handled it through one off functions in some
``util.py`` per project. This project is about rejecting the notion that there
is a trade-off between developer convenience and good documentation. You
shouldn't have to choose between tons of duplicate arguments and docstrings,
kitchen-sink functions, and un-introspectable code. 

You should be able to not repeat yourself, break things up into smaller
functions, and use function-introspection tools to build automagical user
interfaces!

.. image:: https://memegenerator.net/img/instances/69299281.jpg
   :alt: (¿Por qué no los tres?)
   :width: 200px


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
