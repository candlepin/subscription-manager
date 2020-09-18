# needs python-nose installed
# needs an xserver or vncserver running
# see http://www.oracle-base.com/articles/linux/configuring-vnc-server-on-linux.php for an example for f16
# needs polib installed, http://pypi.python.org/pypi/polib
# probably will need coverage tools installed
# systemctl start vncserver@:3.service
# systemctl stop vncserver@:3.service
# needs python-rhsm
# needs mock  (easy_install mock)
# needs PyXML installed
# needs pyflakes insalled
# if we haven't installed/ran subsctiption-manager (or installed it)
#   we need to make /etc/pki/product and /etc/pki/entitlement

#env

echo "GIT_COMMIT:" "${GIT_COMMIT}"

sudo yum clean expire-cache
sudo yum-builddep -y subscription-manager.spec || true # ensure we install any missing rpm deps
virtualenv env -p python3 --system-site-packages || virtualenv-3 env --system-site-packages || true
source env/bin/activate
pip install -I -r test-requirements.txt

# so we can run these all everytime, we don't actually fail on each step, so checkout for output
#TMPFILE=`mktemp`|| exit 1; $(make stylish | tee $TMPFILE); if [ -s $TMPFILE ] ; then echo "FAILED"; cat $TMPFILE; exit 1; fi

# build the c modules
python3 setup.py build
python3 setup.py build_ext --inplace

# not using "setup.py nosetests" yet
# since they need a running candlepin

# Run just the unit tests, functional needs a running candlepin
#pushd test/unit
# make sure we have a dbus session for the dbus tests
dbus-run-session nosetests --with-xunit --with-cover --cover-package rhsm --cover-package subscription_manager --cover-erase

coverage3 html
coverage3 xml
