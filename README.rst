======
README
======

Exoself is a programming language, runtime and compiler designed and written by Florian Noeding (florian AT noeding DOT com).
For more details see either my blog http://code2code.wordpress.com or http://exoself.de



Quickstart
----------

1. download, compile and install llvm (at the time of writing this 2.4)
2. add the llvm binary directory to your PATH variable if it's not already there
3. in the root directory execute ``./waf configure`` followd by ``./waf``

Known problems
--------------
ANTLR 3.1.1 seems to have problems with some Java versions, at least 1.5.0 and will miscompile the grammar definition, so the compiler will not work. In this case try 1.6.0. Edit src/compiler/Makefile and edit the line ``JAVA=java`` to point to the correct java executable.


Notes for OS X users
--------------------
Instead of installing llvm manually you can also try to use llvm from macports:
sudo port install llvm


License
-------
The compiler and other sources are distributed under the BSD License.
Programs compiled using Exoself are not covered by this license and you may choose an arbitry license for them.
The documentation of Exoself is covered by the CC-SA license: http://creativecommons.org/licenses/by-sa/3.0/


