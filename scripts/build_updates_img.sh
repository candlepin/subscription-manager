#!/bin/bash

# A script that wraps make install to create an updates.img suitable for anaconda.
PROJECT_ROOT=$(git rev-parse --show-toplevel)
UPDATE_DIR=$(mktemp -d)
pushd $PROJECT_ROOT

rm ./updates.img 2>/dev/null

# Install files to the temporary build dir
export DESTDIR=$UPDATE_DIR
make -e install

# Build img file (See https://fedoraproject.org/wiki/Anaconda/Updates)
find $UPDATE_DIR | cpio -o -c | gzip > ./updates.img

# Clean up after ourselves
rm -rf $UPDATE_DIR
popd
unset DESTDIR


