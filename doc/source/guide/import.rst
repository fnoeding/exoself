..  highlight:: boo

import
=======

The ``import`` statement insert symbols from another module into the current module.

Import all symbols accessible through the module path::

    import exoself.c.math;

    // ...
    x = exoself.c.math.sin(2.0);


Import all symbols accessible through a new identifier::

    import exoself.c.math as cmath;

    // ...
    x = cmath.sin(2.0);

Import all symbols into the global namespace (not recommended)::

    from exoself.c.math import *;

    // ...
    x = sin(2.0);

Import only some symbols into the global namespace::

    from exoself.c.math import sin, cos;

    // ...
    x = sin(2.0);

Import some symbols into the global namespace with new names::

    from exoself.c.math import sin as csin, cos as ccos;

    // ...
    x = csin(2.0);


