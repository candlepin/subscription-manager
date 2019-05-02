from __future__ import print_function, division, absolute_import

# Copyright (c) 2019 Red Hat, Inc.
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
Some REST API calls returns still the same result (usually some server capabilities).
Thus it is wise to cache such result to some file. This modules is used for caching
such REST API calls.
"""

import json
import socket
import logging

import rhsm.connection as connection
import subscription_manager.injection as inj
import subscription_manager.version as version

log = logging.getLogger(__name__)


class ServerCache(object):
    """
    Class providing cached information about resources and capabilities of candlepin server
    """

    CACHE_FILE = "/var/lib/rhsm/server_capabilities.json"

    @classmethod
    def _load_cache_file(cls):
        """
        Try to load data from cache file
        :return:
        """
        data = None

        try:
            with open(cls.CACHE_FILE, 'r') as fp:
                json_str = fp.read()
                data = json.loads(json_str)
        except IOError:
            pass

        return data

    @classmethod
    def _write_cache_file(cls, data):
        """
        Try to write data to cache file
        :param data: fresh data
        :return: None
        """
        log.debug("Writing cached server capabilities: %s" % data)

        # Write fresh data to cache file
        with open(cls.CACHE_FILE, 'w') as fp:
            json.dump(data, fp)

    @staticmethod
    def _get_supported_resources_from_server(uep=None):
        """
        Try to load supported resources from the server
        :param uep: connection to candlepin server
        :return: dictionary of supported resources
        """
        resources = {}

        if uep is None:
            cp_provider = inj.require(inj.CP_PROVIDER)
            uep = cp_provider.get_consumer_auth_cp()
        try:
            resources = uep.get_supported_resources()
        except (socket.error, connection.ConnectionException) as e:
            log.exception(e)

        return resources

    @staticmethod
    def _loaded_data_obsoleted(data, consumer_uuid):
        """
        Try to validate loaded data from cache file to not be obsoleted by re-register or new version
        of subscription-manager
        :param data: loaded data
        :return: True, when data are valid. False otherwise.
        """
        if data is None:
            return True

        # Data has to be valid for current consumer (system could be registered to different candlepin server
        # with different set of features)
        if consumer_uuid not in data:
            log.debug("Server capabilites cache file is obsoleted (old consumer UUID)")
            return True

        # Data has to be valid for current version of subscription-manager (some new features could be added
        # to subscription-manager). Thus resources are reloaded from candlepin server for every new version
        # of subscription-manager
        if "version" not in data:
            log.warning("Server capabilites cache file has wrong structure (missing version)")
            return True
        elif data["version"] != version.rpm_version:
            log.debug("Server capabilites cache file is obsoleted (old version)")
            return True

        return False

    @staticmethod
    def _assembly_capabilities(consumer_uuid, old_data, resources=None):
        """
        Assembly capabilities to structure to be saved in JSON file. Note: this method could be extended
        in the future. We will want to cache other REST API calls.
        :param resources: supported resources
        :return: data
        """
        if resources is None:
            try:
                resources = old_data[consumer_uuid]["supported_resources"]
            except (TypeError, KeyError):
                resources = {}
        data = {
            consumer_uuid: {
                "supported_resources": resources
            },
            "version": version.rpm_version
        }
        return data

    @classmethod
    def get_supported_resources(cls, consumer_uuid, uep=None):
        """
        Try to get supported resources for given consumer UUID from cache file. When cache file
        does not exist or the cache file is obsolete, then load supported resources from server
        and save fresh data to cache file.
        :param consumer_uuid: UUID of consumer
        :param uep: connection to candlepin server
        :return: array of supported resources
        """
        resources = {}

        data = cls._load_cache_file()

        if data is not None:
            data_obsoleted = cls._loaded_data_obsoleted(data, consumer_uuid)
            if data_obsoleted is False and "supported_resources" in data[consumer_uuid]:
                resources = data[consumer_uuid]["supported_resources"]

        # If it wasn't able to load supported resources from cache for some reason, then
        # try to load supported resources from candlepin server
        if not resources:
            resources = cls._get_supported_resources_from_server(uep)

            data = cls._assembly_capabilities(consumer_uuid, data, resources)

            cls._write_cache_file(data)

        return resources
