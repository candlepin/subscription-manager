sudo cp src/zypper/services/rhsm /usr/lib/zypp/plugins/services/
virtualenv env --system-site-packages -p python2 || true
source env/bin/activate
make install-pip-requirements
if [ -d python-rhsm ]; then
  pushd python-rhsm
fi
python setup.py build_ext --inplace
cd $WORKSPACE
sudo -i bash -c "cd $WORKSPACE; PYTHONPATH=$WORKSPACE/src:$WORKSPACE/python-rhsm/src:$WORKSPACE/syspurpose/src nosetests -c playpen/noserc.zypper test/zypper_test"
sudo chown -R $USER $WORKSPACE  # since we just ran w/ sudo
