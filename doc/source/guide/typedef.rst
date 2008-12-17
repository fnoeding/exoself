..  highlight:: boo

typedef
========

A ``typedef`` introduces a new type that has the same structure as the old type. The new and old type can not be used interchangeably.

There are no implicit conversions between the old and new type.

Example::

    typedef FileNum as int32;

    stdin = (cast 0 as FileNum);
    stdout = (cast 1 as FileNum);
    stderr = (cast 2 as FileNum);

    write(stdout, "Hello\n", 6); # ok
    write(1, "Hello\n", 6); # fails, since 1 is of type int32 which can not be implicitly converted to FileNum

