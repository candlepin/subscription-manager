# needs xorg-x11-server-Xvfb rpm installed
# needs python-rhsm

# "make jenkins" will install these via `pip install -r test-requirements.txt'
#  if it can
#  (either user pip config, or virtualenvs)
# needs python-nose installed
# needs polib installed, http://pypi.python.org/pypi/polib
# probably will need coverage tools installed
# needs mock  (easy_install mock)
# needs PyXML installed
# needs pyflakes insalled
# if we haven't installed/ran subsctiption-manager (or installed it)
#   we need to make /etc/pki/product and /etc/pki/entitlement

echo "GIT_COMMIT:" "${GIT_COMMIT}"

cd $WORKSPACE

sudo yum clean expire-cache
sudo yum-builddep -y subscription-manager.spec || true  # ensure we install any missing rpm deps
virtualenv env -p python3
source env/bin/activate

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

make set-versions
# capture exit status of 'make stylish' and not 'tee'
( set -o pipefail; make stylish | tee stylish_results.txt )
