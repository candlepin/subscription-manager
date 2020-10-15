sudo cp src/zypper/services/rhsm /usr/lib/zypp/plugins/services/
virtualenv env --system-site-packages -p python2 || true
source env/bin/activate
make install-pip-requirements
if [ -d rhsm ]; then
  pushd rhsm
fi
python setup.py build_ext --inplace
cd $WORKSPACE
sudo -i bash -c "cd $WORKSPACE; PYTHONPATH=$WORKSPACE/src:$WORKSPACE/rhsm/src:$WORKSPACE/syspurpose/src nosetests -c playpen/noserc.zypper test/zypper_test"
sudo chown -R $USER $WORKSPACE  # since we just ran w/ sudo
