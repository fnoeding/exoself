..  highlight:: boo

def
======

The ``def`` statement defines or declares a function. The basic form is::
    
    def fib(x as uint64) as uint64;

which declares a function ``fib`` with a single parameter ``x`` of type ``uint64`` and return type ``uint64``. To define a function the semicolon is replaced by the body of the function::

    def fib(x as uint64) as uint64
    {
        // produces the values: 0, 1, 1, 2, 3, 5, 8, 13, ...

        if x == 0
        {
            return 0;
        }
        elif x == 1
        {
            return 1;
        }
        else
        {
            return fib(x - 1) + fib(x - 2);
        }
    }

Exoself does not require forward declarations, so the function ``fib`` can be used anywhere inside the module where it is defined.

To define functions with special properties the ``def`` statement provides several parameters. For example to declare a function as ``extern C`` use::
    
    def(mangling=C) sin(x as float64) as float64;

Which is the prototype for the C standard library function ``double sin(double x);``. Declarations of functions are automatically extern, so only the mangling had to be changed here.

Available options:
    - mangling
    - linkage



Mangling
---------

Mangling is the process of transformaning source code identifier names to link time names. Link time identifiers must be unique across a whole program. Since Exoself provides function overloading and other ways to use the same identifier to access different implementations names are mangled.

The available mangling types are:
    - ``C``: use the source code identifiers. This mangling type can not be used together with function overloading. It is used to access C libraries.
    - ``default``: the default Exoself name mangling scheme.


Linkage
---------

Linkage tells the linker where to look for the symbol, if it is only used internally or exported / imported.

The available linkage types are:
    - ``default``: accessible in the whole program, but not outside
    - ``extern``: not defined in this compilation unit. Depending on the shared library implementation of the operating system this can also mean not defined in this program but a shared library.



