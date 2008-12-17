..  highlight:: boo

Variables
===========

Variables can be defined by simply assigning them a value::

    a = 5 # a will be an int32
    b = 1125899906842624 # b will be an int64, since the value does not fit into an int32

    c, d = a, b # as a and b are of type int32, so c and d will also be of type int32

Variables can also be defined by assigning them an explicit type::

    x, y, z as float64;


Variables use local type inference. That means you usually don't need to add types for local variables, but still the variables are statically typed.

