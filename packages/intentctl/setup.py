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

from setuptools import setup, find_packages

test_require = [
    'mock',
    'nose'
]

setup(
    name="intentctl",
    version="1.22.1",
    url="http://www.candlepinproject.org",
    description="Manage Red Hat System Intent",
    license="GPLv2",
    author="Chris Snyder",
    author_email="chainsaw@redhat.com",
    packages=find_packages('../../src', include=["intentctl"]),
    package_dir={
        "intentctl": "../../src/intentctl"
    },
    tests_require=test_require,
    test_suite='nose.collector',
    entry_points={
        "console_scripts": [
            "intentctl = intentctl.main:main"
        ]
    }
)
