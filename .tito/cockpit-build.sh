#!/bin/bash
set -e
echo "Generating cockpit dist-gzip..."
if [ ! $(which yarn) ] ; then
  echo "Unable to build cockpit, yarn not installed (see README)"
  exit 1
fi
pushd cockpit
yarn cache clean
yarn install --frozen-lockfile
make dist-gzip
popd
echo "$(find -name *.tar.gz)"
