from __future__ import print_function, division, absolute_import

from unittest import TestCase, skip
import glob
import os
import subprocess
import time

from nose.plugins.attrib import attr


@attr('zypper')
class TestProductIdPlugin(TestCase):
    def setUp(self):
        # remove all product certs
        subprocess.call('rm -rf /etc/pki/product/*.pem', shell=True)
        missing = []
        for name in ['RHSM_USER', 'RHSM_PASSWORD', 'RHSM_URL', 'RHSM_POOL', 'RHSM_TEST_REPO', 'RHSM_TEST_PACKAGE']:
            if name not in os.environ:
                missing.append(name)
        if missing:
            raise EnvironmentError('Missing {0} environment variables'.format(str(missing)))

    @skip("See BZ 1633304")
    def test_updates_products_after_install(self):
        subprocess.call('subscription-manager register --username={RHSM_USER} --password={RHSM_PASSWORD} --serverurl={RHSM_URL}'.format(**os.environ), shell=True)
        subprocess.call('subscription-manager attach --pool={RHSM_POOL}'.format(**os.environ), shell=True)
        subprocess.check_call('subscription-manager repos --enable={RHSM_TEST_REPO}'.format(**os.environ), shell=True)

        # remove our test package if it exists
        subprocess.call('zypper --non-interactive rm {RHSM_TEST_PACKAGE}'.format(**os.environ), shell=True)

        # install test package
        subprocess.check_call('zypper --non-interactive --no-gpg-checks in {RHSM_TEST_PACKAGE}'.format(**os.environ), shell=True)
        time.sleep(5)  # give the productid process a little time to work its magic

        self.assertTrue(len(glob.glob('/etc/pki/product/*.pem')) > 0, 'Missing product cert(s)')
