#! /usr/bin/env python3
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
    'nose',
    'mock'
]

install_requires = [
    'pep8==1.5.7',
    'flake8==3.0.4',
    'pyflakes',
    'lxml'
]

setup(
    name="build_ext",
    version="1.0.0",
    url="http://www.candlepinproject.org",
    description="Tools for building subscription-manager and friends",
    license="GPLv2",
    author="Alex Wood",
    author_email="chainsaw@redhat.com",
    packages=find_packages(),
    tests_require=test_require,
    install_requires=install_requires,
    test_suite='nose.collector',
)
