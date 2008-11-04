======
README
======


Quickstart
----------

1. download, compile and install llvm (at the time of writing this 2.3)
2. add the llvm binary directory to your PATH variable if it's not already there
3. build llvm-py in 3rdparty/llvm-py using ``python setup.py build``, then symlink or copy the results inside the build directory to 3rdparty/pylibs so that a directory llvm with the .py and .so files is created
4. go to src and run ``make``, that should compile the grammar and run the compiler on the tests

