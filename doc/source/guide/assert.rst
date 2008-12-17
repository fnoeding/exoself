..  highlight:: boo

assert
=======

The ``assert`` statement checks at runtime whether its parameter evaluates to ``True`` or ``False``. If the parameter evaluates to ``False`` the program is aborted::

    assert(42 == 21 * 2); # ok
    assert(42 == 0); # aborts the program at runtime

    # a useful idiom is:
    assert(answer == 42 and "answer must be 42");

When ``assert`` aborts a program, some context information is displayed to help debugging.

Using compiler options ``assert`` statements can be omitted and it is possible to control the amount of information displayed when the ``assert`` fails.


