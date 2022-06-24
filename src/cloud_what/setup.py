# Copyright (c) 2021 Red Hat, Inc.
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
#

"""
Setup for cloud-what
"""

from setuptools import setup

setup(
    name="cloud-what",
    version="1.29.14",
    description="Detection of public cloud provider and gathering metadata from IMDS servers",
    author="Jiri Hnidek",
    author_email="chainsaw@redhat.com",
    url="https://github.com/candlepin/subscription-manager/",
    license="GPLv2",
    long_description="""cloud-what enables to detect cloud provider using information provided
    SM BIOS. The package tries to use dmidecode and virt-what for this purpose. This package
    also allows to gather metadata and signature from IMDS servers provided by public cloud
    providers. Three cloud providers are supported at this moment: AWS, Azure and GCP.""",
    packages=["cloud-what"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GPL License",
        "License :: OSI Approved :: Python Software Foundation License",
        "Operating System :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=["requests"],
)
