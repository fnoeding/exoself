..  highlight:: boo

for
=====

The ``for`` statement exists in two different forms. A simple C style ``for`` and a Python style ``for x in``.

C style::

    s = 0
    for i = 0; i < 100; i += 1
    {
        s += i;
    }
    

Python style::

    s = 0
    for i in range(99, -1, -1)
    {
        s += i;
    }

This loop calculates the same value as the C style loop, but in reverse order. At the moment the ``for x in`` loop accepts only the hard coded ``range(start, stop, step)`` expression.

The curly braces are mandatory.
