..  highlight:: boo

Type System
===========

Elementary types
-----------------

- bool
- int8, int16, int32, int64
- uint8, uint16, uint32, uint64
- float32, float64 (these are the C types 'float' and 'double')
- void


Derived types
---------------

- word: alias for the unsiged integer with the same bit size as a pointer
- sword: same as word, only signed integer
- byte: typedef for uint8


User defined types
-------------------

These can be defined using 

- pointers
- structs
- typedefs (aliases) 


Type equivalence
-------------------

Types are considered equal, if they have the same (mangled) typename (with the exception of aliases). For example even two structs with the same contents, but different names are not considered equal. They are only structurally equivalent.



