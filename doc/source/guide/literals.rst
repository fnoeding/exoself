..  highlight:: boo

Literals
=========


Integer literals
-----------------
An integer literal consists of

- an optional prefix, specifying the base

    * ``0x`` and ``0X`` are base 16
    * ``0b`` and ``0B`` are base 2
    * ``0`` is base 8
    * no prefix is base 10

- the number itself according to the specified base, mixed with arbitrarily many underscores
- an optional suffix specifying the type

    * ``uhh`` uint8
    * ``uh`` uint16
    * ``u`` uint32
    * ``ul`` uint64
    * ``hh`` int8
    * ``h`` int16
    * no suffix int32
    * ``l`` int64

examples::

    a = 0xDEAD_BEAF
    b = 0xDEAD_BEAF_ul
    c = 0X___D_E___A___D_BEAFul
    d = 4___2l
    e = 0B10_1010
    f = 42uhh



Floating point literals
-------------------------
Floating point literals are supported in the usual scientific notation

- any number of digits mixed with any number of underscores
- a dot
- at least one digit mixed with any number of underscores
- an optional exponent consisting of

    * either ``e`` or ``E``
    * an optional sign of the exponent
    * at least one digit mixed with any number of underscores

- an optional suffix specifying the type

    * ``f`` for float32
    * no suffix for float64

examples::

    .05
    1.323f
    4.2E+1f



Boolean literals
-------------------

The literals ``True`` and ``False`` are interpreted as values of type ``bool``.



String literals
-----------------
still in the planning phase.



Other literals
----------------
The ``None`` literal is a special case. It is handled as a pointer which can circumvent the otherwise very strict type checking: ``None`` can be converted to any pointer type and is equivalent to a ``cast(0 as PointerType)``.


