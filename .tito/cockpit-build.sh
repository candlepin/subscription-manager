#!/bin/bash
set -e

USE_SUSE=`rpm --eval '%{?suse_version}'`
if [ -n "${USE_SUSE}" ] ; then
  echo "Skipping building of cockpit on SLES"
  exit 0
fi

echo "Generating cockpit dist-gzip..."
pushd cockpit
npm ci
make dist-gzip
popd
echo "$(find -name *.tar.gz)"
