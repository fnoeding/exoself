..  highlight:: boo

new
====

The ``new`` operator allocates memory from the garbage collected heap::

    p = new(int32); # allocates memory for a single int32 and returns a pointer to it
    p100 = new(int32); # allocates memory for 100 int32 and returns a pointer to it


In the case that you wish to manage the memory yourself just use the C ``malloc`` and ``free`` calls. As long as you don't store pointers to managed memory in manually managed memory everything should work. But if you want to store managed pointers in unmanaged memory you have to inform the garbage collector.


delete
=======

The ``delete`` operator is not implemented at the moment since ``new`` together with garbage collection does not mandatorily need it.

