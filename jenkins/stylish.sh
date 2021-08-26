#!/bin/bash

echo "GIT_COMMIT:" "${GIT_COMMIT}"
WORKSPACE="$(git rev-parse --show-toplevel)"

cd $WORKSPACE

sudo yum clean expire-cache
sudo yum-builddep -y subscription-manager.spec || true  # ensure we install any missing rpm deps
virtualenv env-stylish -p python3
source env-stylish/bin/activate

make install-pip-requirements

# build/test python-rhsm
if [ -d $WORKSPACE/python-rhsm ]; then
  pushd $WORKSPACE/python-rhsm
fi
PYTHON_RHSM=$(pwd)

# build the c modules
python3 setup.py build
python3 setup.py build_ext --inplace

pushd $WORKSPACE
export PYTHONPATH="$PYTHON_RHSM"/src

# make set-versions
make stylish
