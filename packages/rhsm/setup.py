#
# Copyright (c) 2018 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from setuptools import setup, find_packages, Extension

test_require = [
    'mock',
    'nose',
    'iniparse',
    'python-dateutil'
]

setup(
    name="python-rhsm",
    version="1.22.0",
    url="http://www.candlepinproject.org",
    description="Manage Red Hat Subscriptions",
    license="GPLv2",
    author="Vritant Naresh Jain",
    author_email="chainsaw@redhat.com",
    packages=find_packages('../../src', include=["rhsm"]),
    package_dir={
        "rhsm": "../../src/rhsm"
    },
    tests_require=test_require,
    test_suite='nose.collector',
    ext_modules=[Extension(
        'rhsm._certificate',
        ['../../src/certificate.c'],
        libraries=['ssl', 'crypto']
    )],
)
