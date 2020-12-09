# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Red Hat, Inc.
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
This module implements base class for collecting metadata from cloud provider
"""


class CloudCollector(object):
    """
    Base class for collecting metadata and signature of metadata from cloud
    provider. The most of logic is implemented in this class. Subclasses
    for concrete cloud providers usually contains only default values in
    class attributes. All values will be usually loaded from configuration
    files of cloud providers. It is/will be still possible to implement
    custom method for e.g. getting metadata from cloud provider.
    """

    # Unique ID of cloud provider
    # (e.g. "aws", "azure", "gcp", etc.)
    CLOUD_PROVIDER_ID = None

    # Path to configuration file of collector (ini file)
    # (e.g. /etc/rhsm/cloud_providers/cool_cloud.conf
    COLLECTOR_CONF_FILE = None

    # Default value of server URL providing metadata
    # (e.g. http://1.2.3.4./path/to/metadata/document)
    CLOUD_PROVIDER_METADATA_URL = None

    # Type of metadata document returned by server
    # (e.g. json, xml)
    CLOUD_PROVIDER_METADATA_TYPE = None

    # Default value of server URL providing signature of metadata
    # (e.g. http://1.2.3.4/path/to/signature/document)
    CLOUD_PROVIDER_SIGNATURE_URL = None

    # Type of signature document returned by server
    # (e.g. json, xml, pem)
    CLOUD_PROVIDER_SIGNATURE_TYPE = None

    # Default value of path to cache file holding metadata
    # (e.g. /var/lib/rhsm/cache/cool_cloud_metadata.json)
    METADATA_CACHE_FILE = None

    # Default value of path to  holding signature of metadata
    # (e.g. /var/lib/rhsm/cache/cool_cloud_signature.json)
    SIGNATURE_CACHE_FILE = None

    def __init__(self):
        """
        Initialize instance of CloudCollector
        """
        self.metadata = None
        self.signature = None

    def _get_collector_configuration_from_file(self):
        """
        Get configuration of collector from json file
        :return: True, when it was possible to load configuration file of collector
        """
        raise NotImplementedError

    def _get_metadata_from_cache(self):
        """
        Method for gathering metadata from cache file
        :return: string containing metadata
        """
        raise NotImplementedError

    def _get_metadata_from_server(self):
        """
        Method for gathering metadata from server
        :return: string containing metadata
        """
        raise NotImplementedError

    def _get_signature_from_cache_file(self):
        """
        Try to get signature from cache file
        :return: string containing signature
        """
        raise NotImplementedError

    def _get_signature_from_server(self):
        """
        Method for gathering signature of metadata from server
        :return:
        """
        raise NotImplementedError

    def get_signature(self):
        """
        Public method for getting signature (cache file or server)
        :return:
        """
        raise NotImplementedError

    def get_metadata(self):
        """
        Public method for getting metadata (cache file or server)
        :return:
        """
        raise NotImplementedError

    def is_running_on_cloud(self):
        """
        Return True, when server can really server providing metadata information
        :return: True if the system is running on AWS cloud
        """
        # TODO: not sure about this method
        raise NotImplementedError
