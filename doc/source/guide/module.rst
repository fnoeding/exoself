..  highlight:: boo

Module
========

A module is a single compilation unit. A module consists of (exactly in this order):
    - an optional ``package`` statement
    - an (sometimes) optional ``module`` statement
    - any number of global statements

Package Statement
-----------------

A ``package`` statement defines a unique name to be used for name mangling. This is necessary to distinguish multiple modules with the same module name. It is suggested to use a package name of the form ``de.exoself.package``.

You can use any number of different package names in a single project as long as there are no link time problems with clashing module names.

Application writers can often ignore the ``package`` statement, library writers should choose a unique identifier to avoid clashes.

Important: A package name does not affect the search path for modules. It's really only used for link time disambiguation.


Module Statement
-----------------
The ``module`` statement defines the name of the current module. By default this name is the name of the source file without the extension. In the case that the source file name is not a valid identifier name (starts with underscore or letter, then any number of underscores, letters and digits) a module name must be given.

Important: Module names are also only used for link time disambiguation and have nothing to do with importing other modules. That also means that a module that has a filename which is not a legal identifier can not be imported.


Global Statements
-------------------

Global statements are statements other than the package and module statement which can occur at the global file scope. Valid statements are:
    - ``alias``
    - ``def``
    - ``import``
    - ``struct``
    - ``typedef``

Example
--------
::

    package exoself.math;# avoid linktime clashes with other modules called math
    module math;# sets only link time name

    # any global statements may follow here
    # ...


