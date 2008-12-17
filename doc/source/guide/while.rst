..  highlight:: boo

while
======

The ``while`` statement constructs a loop::

    i = 0;
    s = 0;
    while i < 100
    {
        s += i;
    }

The curly braces are mandatory.

while else
===========

::

    n = ...
    // ...

    i = 0;
    s = 0;
    while i < n;
    {
        // executes like a normal while loop
        s += i;
    }
    else
    {
        // this code is only run, if the associated while loop body is not executed at least once
        s = -1;
    }

The ``while else`` construct is only syntactic sugar for an additional if, that checks whether the loop body executes at least once, and if not executes the else case.

