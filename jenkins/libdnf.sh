#!/bin/bash

echo "GIT_COMMIT:" "${GIT_COMMIT}"

export BUILD_DIR='./build'

cd './src/plugins/libdnf'
rm -rf "${BUILD_DIR}"
mkdir "${BUILD_DIR}"
cd "${BUILD_DIR}"
cmake ../ -DCMAKE_VERBOSE_MAKEFILE:BOOL=ON
make
CTEST_OUTPUT_ON_FAILURE=1 make test
