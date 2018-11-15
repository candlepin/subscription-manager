from __future__ import print_function, division, absolute_import

from six.moves import configparser
from unittest import TestCase
import os
import subprocess
import tempfile

from nose.plugins.attrib import attr


@attr('zypper')
class TestServicePlugin(TestCase):
    def setUp(self):
        missing = []
        for name in ['RHSM_USER', 'RHSM_PASSWORD', 'RHSM_URL', 'RHSM_POOL', 'RHSM_TEST_REPO', 'RHSM_TEST_PACKAGE']:
            if name not in os.environ:
                missing.append(name)
        if missing:
            raise EnvironmentError('Missing {0} environment variables'.format(str(missing)))

        # start in a non-registered state
        subprocess.call('subscription-manager unregister', shell=True)

    def has_subman_repos(self):
        repos = configparser.ConfigParser()
        with tempfile.NamedTemporaryFile(suffix='.repo') as repofile:
            subprocess.call('zypper lr -e {0}'.format(repofile.name), shell=True)
            repos.read(repofile.name)
        for repo in repos.sections():
            repo_info = dict(repos.items(repo))
            service = repo_info.get('service', None)
            if service == 'rhsm':
                return True
        return False

    def test_provides_no_subman_repos_if_unregistered(self):
        self.assertFalse(self.has_subman_repos())

    def test_provides_subman_repos_if_registered_and_subscribed(self):
        subprocess.call('subscription-manager register --username={RHSM_USER} --password={RHSM_PASSWORD} --serverurl={RHSM_URL}'.format(**os.environ), shell=True)
        subprocess.call('subscription-manager attach --pool={RHSM_POOL}'.format(**os.environ), shell=True)
        self.assertTrue(self.has_subman_repos())

    def test_can_download_rpm(self):
        subprocess.check_call('subscription-manager register --username={RHSM_USER} --password={RHSM_PASSWORD} --serverurl={RHSM_URL}'.format(**os.environ), shell=True)
        subprocess.check_call('subscription-manager attach --pool={RHSM_POOL}'.format(**os.environ), shell=True)
        subprocess.check_call('subscription-manager repos --enable={RHSM_TEST_REPO}'.format(**os.environ), shell=True)

        # remove cached subman packages
        subprocess.call('rm -rf /var/cache/zypp/packages/subscription-manager*', shell=True)
        # remove test package if installed
        subprocess.call('zypper --non-interactive rm {RHSM_TEST_PACKAGE}'.format(**os.environ), shell=True)
        subprocess.call('zypper --non-interactive --no-gpg-checks in --download-only {RHSM_TEST_PACKAGE}'.format(**os.environ), shell=True)

        subprocess.check_call('test "$(find /var/cache/zypp/packages/ -name \'{RHSM_TEST_PACKAGE}*.rpm\' | wc -l)" -gt 0'.format(**os.environ), shell=True)
