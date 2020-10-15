#!/usr/bin/env python
from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2014 Red Hat, Inc.
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

"""
Setup tool for python-rhsm package including binary module _certificate.so
"""

import os
from glob import glob

from setuptools import setup, find_packages, Extension

from distutils import log
from distutils.command.clean import clean as _clean
from distutils.dir_util import remove_tree


class clean(_clean):
    def initialize_options(self):
        self.egg_base = None
        _clean.initialize_options(self)

    def finalize_options(self):
        self.set_undefined_options('egg_info', ('egg_base', 'egg_base'))
        _clean.finalize_options(self)

    def run(self):
        if self.all:
            for f in glob(os.path.join(self.egg_base, '*.egg-info')):
                log.info("removing %s" % f)
                remove_tree(f, dry_run=self.dry_run)
        _clean.run(self)


cmdclass = {
    'clean': clean,
}

setup(
    name="rhsm",
    version='1.19.4',
    description='A Python library to communicate with a Red Hat Unified Entitlement Platform',
    author='Devan Goodwin',
    author_email='dgoodwin@redhat.com',
    url='https://www.candlepinproject.org',
    license='GPLv2',
    package_dir={
        'rhsm': 'src/rhsm',
    },
    packages=find_packages('src'),
    include_package_data=True,
    ext_modules=[Extension('rhsm._certificate', ['src/certificate.c'],
                           libraries=['ssl', 'crypto'])],
    classifiers=[
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python'
    ],
    install_requires=['iniparse'],
)
