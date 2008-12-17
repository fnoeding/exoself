..  highlight:: boo

cast
=====

The ``cast`` function performs type conversion:
    - conversion between structurally different types like ``int32`` and ``uint64`` or ``int32`` and ``float64`` or between different user defined types
    - conversion between structurally equivalent types, either typedefs or structs with the same fields, are noops


::

    a = cast(1.23, int32) # assign a the value 1.23 cast to int32, which is simply 1

bitcast
=========

Still in the planning phase.

The idea behind the ``bitcast`` operator is to retrieve the bit pattern of a float32 and store it in a int32. This operation can also be used on other types, as long source and target variable have the same size::
    y = 3.141;

    x = bitcast(y as int64);

This operation is easier to understand than the following idiom and could be more effecient::
    y = 3.141;

    py = &y;
    x = *cast(py as int64*);

    
