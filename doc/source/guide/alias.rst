..  highlight:: boo

alias
======

The ``alias`` statement introduces an alias for an existing type name. The new and old name can be used interchangeably.


Example::

    alias int as int32; # int is another name for int32 and can be used whereever an int32 can be used
    alias pint as int32*; # pint is another name for the type int32*

