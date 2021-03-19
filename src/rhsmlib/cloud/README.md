RHSM & Cloud
============

This package contains modules for detecting cloud providers and collecting cloud metadata. The
metadata then can be for example reported in system facts. Three main cloud providers are
supported ATM: Amazon Web Services, Microsoft Azure and Google Cloud Platform. If you want to add
support for another cloud provider, then add subclasses of CloudProvider, CloudCollector and
CloudDetector to module in providers sub-package and modify list of supported classes in `utils.py`.

Example: you want to add support for Foo Cloud Provider. You will create package `fcp.py` in
folder `providers`. Content of `fcp.py` will look like this:

```python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Foo Company
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

# TODO: test Python3 syntax using flake8
# flake8: noqa

"""
This is module implementing detector and metadata collector of virtual machine running on Foo Cloud Provider
"""

import logging

from typing import Union

from rhsmlib.cloud._base_provider import BaseCloudProvider


log = logging.getLogger(__name__)


class FooCloudProvider(BaseCloudProvider):
    """
    Base class for Foo cloud provider
    """

    CLOUD_PROVIDER_ID = "foo"

    CLOUD_PROVIDER_METADATA_URL = "http://1.2.2.4/metadata/"

    CLOUD_PROVIDER_METADATA_TYPE = "application/json"

    CLOUD_PROVIDER_SIGNATURE_URL = "http://169.254.169.254/signature"

    CLOUD_PROVIDER_SIGNATURE_TYPE = "application/json"

    METADATA_CACHE_FILE = None

    SIGNATURE_CACHE_FILE = None

    HTTP_HEADERS = {
        'user-agent': 'RHSM/1.0',
    }

    def __init__(self, hw_info):
        """
        Initialize instance of FooCloudDetector
        """
        super(FooCloudProvider, self).__init__(hw_info)

    def is_vm(self):
        """
        Is system running on virtual machine or not
        :return: True, when machine is running on VM; otherwise return False
        """
        return super(FooCloudProvider, self).is_vm()

    def is_running_on_cloud(self):
        """
        Try to guess if cloud provider is Foo using collected hardware information (output of dmidecode,
        virt-what, etc.)
        :return: True, when we detected sign of Foo in hardware information; Otherwise return False
        """

        # TODO: Check if this is true for Foo Cloud Provider
        if self.is_vm() is False:
            return False

        # This is valid for virtual machines running on Foo
        if 'dmi.chassis.asset_tag' in self.hw_info and \
                self.hw_info['dmi.chassis.asset_tag'] == 'FOO':
            return True
        # In other cases return False
        return False

    def is_likely_running_on_cloud(self):
        """
        Return non-zero value, when the machine is virtual machine and it is running on Foo
        hypervisor and some Foo string can be found in output of dmidecode
        :return: Float value representing probability that vm is running on Foo
        """
        probability = 0.0

        # TODO: Check if this is true for Foo Cloud Provider 
        if self.is_vm() is False:
            return 0.0

        if 'dmi.chassis.asset_tag' in self.hw_info and \
                self.hw_info['dmi.chassis.asset_tag'] == 'FOO':
            probability += 0.3

        # Try to find "Foo" keyword in output of dmidecode
        found_foo = False
        for hw_item in self.hw_info.values():
            if type(hw_item) != str:
                continue
            if 'foo' in hw_item.lower():
                found_foo = True
        if found_foo is True:
            probability += 0.3

        return probability


    def _get_metadata_from_cache(self) -> Union[str, None]:
        """
        TODO: implement something or return None
        """
        raise NotImplementedError

    def _get_data_from_server(self, data_type, url):
        """
        This method tries to get data from server using GET method
        :param data_type: string representation of data type used in log messages (e.g. "metadata", "signature")
        :param url: URL of GET request
        :return: String of body, when request was successful; otherwise return None
        """
        return super(FooCloudProvider, self)._get_data_from_server(data_type, url)

    def _get_metadata_from_server(self) -> Union[str, None]:
        """
        Try to get metadata from server
        :return: String with metadata or None
        """
        return super(FooCloudProvider, self)._get_metadata_from_server()

    def _get_signature_from_cache_file(self) -> Union[str, None]:
        """
        TODO: implement something or return None
        """
        raise NotImplementedError

    def _get_signature_from_server(self) -> Union[str, None]:
        """
        Method for gathering signature of metadata from server
        :return: String containing signature or None
        """
        return super(FooCloudProvider, self)._get_signature_from_server()

    def get_signature(self) -> Union[str, None]:
        """
        Public method for getting signature (cache file or server)
        :return: String containing signature or None
        """
        return super(FooCloudProvider, self).get_signature()

    def get_metadata(self) -> Union[str, None]:
        """
        Public method for getting metadata (cache file or server)
        :return: String containing metadata or None
        """
        return super(FooCloudProvider, self).get_metadata()
```

When implementation of cloud provider is finished, then please modify list of providers
in `rhsmlib/cloud/provider.py` accordingly:

```python
# List of detector classes with supported cloud providers
CLOUD_PROVIDERS = [
    ...,
    FooCloudProvider
]
```

When implementation of your cloud detector and collector is finished, then please implement some unit tests in
`test/rhsmlib_test/test_cloud.py` or you can implement tests first if you prefer test driven development.