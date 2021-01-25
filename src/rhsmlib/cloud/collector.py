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

# TODO: test Python3 syntax using flake8
# flake8: noqa

"""
This module implements base class for collecting metadata from cloud provider.
"""

import requests
import logging
import json
import os
import time

from typing import Union

log = logging.getLogger(__name__)


class CloudCollector(object):
    """
    Base class for collecting metadata and signature of metadata from cloud
    provider. The most of logic is implemented in this class. Subclasses
    for concrete cloud providers usually contains only default values in
    class attributes. Logic of gathering metadata/signature will be implemented
    in this base class and subclasses will need to set only class attributes.
    It will be still possible to implement custom method for e.g. getting
    metadata from cloud provider.
    """

    # Unique ID of cloud provider
    # (e.g. "aws", "azure", "gcp", etc.)
    CLOUD_PROVIDER_ID = None

    # Default value of server URL providing metadata
    # (e.g. http://1.2.3.4./path/to/metadata/document)
    CLOUD_PROVIDER_METADATA_URL = None

    # Type of metadata document returned by server
    # (e.g. "application/json", "text/xml")
    CLOUD_PROVIDER_METADATA_TYPE = None

    # Default value of server URL providing signature of metadata
    # (e.g. http://1.2.3.4/path/to/signature/document)
    CLOUD_PROVIDER_SIGNATURE_URL = None

    # Type of signature document returned by server
    # (e.g. "application/json", "text/xml", "text/pem")
    CLOUD_PROVIDER_SIGNATURE_TYPE = None

    # Default value of path to cache file holding metadata
    # (e.g. /var/lib/rhsm/cache/cool_cloud_metadata.json)
    METADATA_CACHE_FILE = None

    # Default value of path to holding signature of metadata
    # (e.g. /var/lib/rhsm/cache/cool_cloud_signature.json)
    SIGNATURE_CACHE_FILE = None

    # Custom HTTP headers like user-agent
    HTTP_HEADERS = {}

    # Some collector can use a token that expires within some time limit. Thus such token can be
    # cached to some file
    TOKEN_CACHE_FILE = None

    # When a token is supported by cloud provider, then this value is in seconds
    CLOUD_PROVIDER_TOKEN_TTL = None

    def __init__(self) -> None:
        """
        Initialize instance of CloudCollector.
        """
        # In-memory cache of token. The token is simple string
        self._token = None
        # Time, when token was received. The value is in seconds (unix time)
        self._token_ctime = None
        # Time to Live of token
        self._token_ttl = None

    def _write_token_to_cache_file(self) -> None:
        """
        Try to write token to cache file
        :return: None
        """
        if self._token is None or self._token_ctime is None or self.TOKEN_CACHE_FILE is None:
            log.debug(f'Unable to write {self.CLOUD_PROVIDER_ID} token to cache file due to missing data')
            return None

        token_cache_content = {
            "ctime": str(self._token_ctime),
            "ttl": str(self._token_ttl),
            "token": self._token
        }

        log.debug(f'Writing {self.CLOUD_PROVIDER_ID} token to file {self.TOKEN_CACHE_FILE}')

        with open(self.TOKEN_CACHE_FILE, "w") as token_cache_file:
            json.dump(token_cache_content, token_cache_file)

        # Only owner (root) should be able to read the token file
        os.chmod(self.TOKEN_CACHE_FILE, 0o600)

    def _is_in_memory_cached_token_valid(self) -> bool:
        """
        Check if cached token is still valid
        :return: True, when cached token is valid; otherwise return False
        """
        if self._token is None or self._token_ctime is None:
            return False

        current_time = time.time()
        if current_time < self._token_ctime + self.CLOUD_PROVIDER_TOKEN_TTL:
            return True
        else:
            return False

    def _get_token_from_cache_file(self) -> Union[str, None]:
        """
        Try to get token from cache file. Cache file is JSON file with following structure:

        {
          "ctime": "1607949565.9036307",
          "ttl": "3600",
          "token": "ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=="
        }

        The cache file can be read only by owner.
        :return: String with token or None, when it possible to load token from cache file
        """
        log.debug(f'Reading cache file with {self.CLOUD_PROVIDER_ID} token: {self.TOKEN_CACHE_FILE}')

        if not os.path.exists(self.TOKEN_CACHE_FILE):
            log.debug(f'Cache file: {self.TOKEN_CACHE_FILE} with {self.CLOUD_PROVIDER_ID} token does not exist')
            return None

        with open(self.TOKEN_CACHE_FILE, "r") as token_cache_file:
            try:
                cache_file_content = token_cache_file.read()
            except OSError as err:
                log.error(f'Unable to load token cache file: {self.TOKEN_CACHE_FILE}: {err}')
                return None
        try:
            cache = json.loads(cache_file_content)
        except json.JSONDecodeError as err:
            log.error(f'Unable to parse token cache file: {self.TOKEN_CACHE_FILE}: {err}')
            return None

        required_keys = ['ctime', 'token', 'ttl']
        for key in required_keys:
            if key not in cache:
                log.error(f'Required key: {key} is not included in token cache file: {self.TOKEN_CACHE_FILE}')
                return None

        try:
            ctime = float(cache['ctime'])
        except ValueError as err:
            log.error(f'Wrong ctime value in {self.TOKEN_CACHE_FILE}, error: {err}')
            return None
        else:
            self._token_ctime = ctime

        try:
            ttl = float(cache['ttl'])
        except ValueError as err:
            log.warning(
                f'Wrong TTL value in {self.TOKEN_CACHE_FILE} '
                f'error: {err} '
                f'using default value: {self.CLOUD_PROVIDER_TOKEN_TTL}'
            )
            ttl = self.CLOUD_PROVIDER_TOKEN_TTL
        self._token_ttl = ttl

        if time.time() < ctime + ttl:
            log.debug(f'Cache file: {self.TOKEN_CACHE_FILE} with {self.CLOUD_PROVIDER_ID} token read successfully')
            return cache['token']
        else:
            log.debug(f'Cache file with {self.CLOUD_PROVIDER_ID} token file: {self.TOKEN_CACHE_FILE} timed out')
            return None

    def _get_metadata_from_cache(self) -> Union[str, None]:
        """
        Method for gathering metadata from cache file
        :return: string containing metadata
        """
        raise NotImplementedError

    def _get_data_from_server(self, data_type, url) -> Union[str, None]:
        """
        Try to get some data from server using method GET
        :data_type: string representing data type (metadata, signature, token)
        :param url: URL of the GET request
        :return: String representing body, when status code is 200; Otherwise return None
        """
        log.debug(f'Trying to get {data_type} from {url}')

        try:
            response = requests.get(url, headers=self.HTTP_HEADERS)
        except requests.ConnectionError as err:
            log.debug(f'Unable to get {self.CLOUD_PROVIDER_ID} {data_type}: {err}')
        else:
            if response.status_code == 200:
                return response.text
            else:
                log.debug(f'Unable to get {self.CLOUD_PROVIDER_ID} {data_type}: {response.status_code}')

    def _get_metadata_from_server(self) -> Union[str, None]:
        """
        Method for gathering metadata from server
        :return: String containing metadata or None
        """
        return self._get_data_from_server("metadata", self.CLOUD_PROVIDER_METADATA_URL)

    def _get_signature_from_cache_file(self) -> Union[str, None]:
        """
        Try to get signature from cache file
        :return: String containing signature or None
        """
        raise NotImplementedError

    def _get_signature_from_server(self) -> Union[str, None]:
        """
        Method for gathering signature of metadata from server
        :return: String containing signature or None
        """
        return self._get_data_from_server("signature", self.CLOUD_PROVIDER_SIGNATURE_URL)

    def get_signature(self) -> Union[str, None]:
        """
        Public method for getting signature (cache file or server)
        :return: String containing signature or None
        """
        signature = self._get_signature_from_cache_file()

        if signature is None:
            signature = self._get_signature_from_server()

        return signature

    def get_metadata(self) -> Union[str, None]:
        """
        Public method for getting metadata (cache file or server)
        :return: String containing signature or None
        """
        metadata = self._get_metadata_from_cache()

        if metadata is not None:
            return metadata

        return self._get_metadata_from_server()
