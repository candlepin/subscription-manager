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
sudo yum-builddep -y subscription-manager.spec  || true # ensure we install any missing rpm deps
virtualenv env --system-site-packages -p python2 || true
source env/bin/activate

make install-pip-requirements
pip install --user -r ./test-requirements.txt

# build rhsm package
if [ -d $WORKSPACE/rhsm ]; then
  pushd $WORKSPACE/rhsm
  # build the C modules
  python setup.py build
  python setup.py build_ext --inplace
  PYTHON_RHSM=$(pwd)
  export PYTHONPATH="$PYTHON_RHSM"/src
  pushd $WORKSPACE
fi

echo
echo "PYTHONPATH=$PYTHONPATH"
echo "PATH=$PATH"
echo

make build
make coverage
