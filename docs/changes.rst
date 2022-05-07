.. _changes

Ch-ch-ch-ch-changes
====================

0.4.0
--------------
 
 - adding support for instance methods in :func:`starstar.signature` (bug fix for attribute setting)
 - adding :func:`starstar.required_args` to pull out arguments that are required.
 - adding :func:`popkw` to pull out kwargs specified in a function's signature
 - setting ``doc=False`` by default for :func:`traceto` because there's a bug where it strips out code examples...
 - added :module:`starstar.docstring` - will probably deprecate docstring_parser as a dependency, 
   but I want to do more rigorous testing for it first.

0.3.0
--------

 - Adding :func:`starstar.unpack`