#!/bin/bash

# llvm-py
cd pylibs || exit 1
rm llvm > /dev/null 2> /dev/null
cd ..
cd llvm-py || exit 1
python setup.py build || exit 1
cd build || exit 1
TARGET=`ls -d lib*`
cd ../../pylibs || exit 1
ln -s ../llvm-py/build/${TARGET}/llvm || exit 1
cd ..

