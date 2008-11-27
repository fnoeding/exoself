#!/bin/bash

# llvm-py
cd pylibs
rm llvm > /dev/null 2> /dev/null
cd ..
cd llvm-py
python setup.py build
cd build
TARGET=`ls -d lib*`
cd ../../pylibs
ln -s ../llvm-py/build/${TARGET}/llvm
cd ..

