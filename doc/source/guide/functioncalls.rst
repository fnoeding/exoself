..  highlight:: boo

function calls
==============

Functions are called by using their name followed by all parameters inside parenthesis::

    f(a, b, c, 42);

Future versions of Exoself will also feature passing parameters by name::

    // def f(key as byte*, value as int32) as void
    f(key="answer", value=42);


See the ``def`` statement for more details, especially regarding function overloading.

