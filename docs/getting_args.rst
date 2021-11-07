
Getting Arguments
===================

.. automodule:: starstar
    :members: signature, get_args, as_args_kwargs, unmatched_kw


Single Argument Types (``int``): 

.. code-block:: python

    def func(POS_ONLY, /, POS_KW, *VAR_POS, KW_ONLY, **VAR_KW):
        ...

======================  ============================
Name                    Description
======================  ============================
``starstar.POS_ONLY``   Positional Only
``starstar.POS_KW``     Positional or Keyword
``starstar.VAR_POS``    Variable Positional (*)
``starstar.KW_ONLY``    Keyword Only
``starstar.VAR_KW``     Variable Keyword (**)
======================  ============================

Combination Argument Types (``set``):

======================  ===================================================
Name                    Description
======================  ===================================================
``starstar.ALL``        ``= {POS_ONLY, KW_ONLY, POS_KW, VAR_POS, VAR_KW}``
``starstar.POS``        ``= {POS_ONLY, POS_KW}``
``starstar.KW``         ``= {POS_KW, KW_ONLY}``
``starstar.VAR``        ``= {VAR_POS, VAR_KW}``
======================  ===================================================

