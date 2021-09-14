from six.moves import configparser
from unittest import TestCase
import os
import subprocess
import tempfile

from test import subman_marker_functional, subman_marker_needs_envvars, subman_marker_zypper


@subman_marker_functional
@subman_marker_zypper
@subman_marker_needs_envvars('RHSM_USER', 'RHSM_PASSWORD', 'RHSM_URL', 'RHSM_POOL', 'RHSM_TEST_REPO', 'RHSM_TEST_PACKAGE')
class TestServicePlugin(TestCase):

    SUB_MAN = "PYTHONPATH=./src python -m subscription_manager.scripts.subscription_manager"

    def setUp(self):
        # start in a non-registered state
        subprocess.call('{sub_man} unregister'.format(sub_man=self.SUB_MAN), shell=True)

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
        subprocess.call('{sub_man} register --username={RHSM_USER} --password={RHSM_PASSWORD} --serverurl={RHSM_URL}'.format(sub_man=self.SUB_MAN, **os.environ), shell=True)
        subprocess.call('{sub_man} attach --pool={RHSM_POOL}'.format(sub_man=self.SUB_MAN, **os.environ), shell=True)
        self.assertTrue(self.has_subman_repos())

    def test_can_download_rpm(self):
        subprocess.check_call('{sub_man} register --username={RHSM_USER} --password={RHSM_PASSWORD} --serverurl={RHSM_URL}'.format(sub_man=self.SUB_MAN, **os.environ), shell=True)
        subprocess.check_call('{sub_man} attach --pool={RHSM_POOL}'.format(sub_man=self.SUB_MAN, **os.environ), shell=True)
        subprocess.check_call('{sub_man} repos --enable={RHSM_TEST_REPO}'.format(sub_man=self.SUB_MAN, **os.environ), shell=True)

        # remove cached subman packages
        subprocess.call('rm -rf /var/cache/zypp/packages/subscription-manager*', shell=True)
        # remove test package if installed
        subprocess.call('PYTHONPATH=./src zypper --non-interactive rm {RHSM_TEST_PACKAGE}'.format(**os.environ), shell=True)
        subprocess.call('PYTHONPATH=./src zypper --non-interactive --no-gpg-checks in --download-only {RHSM_TEST_PACKAGE}'.format(**os.environ), shell=True)

        subprocess.check_call('test "$(find /var/cache/zypp/packages/ -name \'{RHSM_TEST_PACKAGE}*.rpm\' | wc -l)" -gt 0'.format(**os.environ), shell=True)
