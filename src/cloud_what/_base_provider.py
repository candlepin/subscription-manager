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
This module contains base class for generic cloud provider. This module
should not be imported outside this package.
"""

import enum
import requests
import logging
import json
import os
import time

from typing import Union

log = logging.getLogger(__name__)


class COLOR(enum.Enum):
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def colorize(text: str, color: COLOR) -> str:
    return color.value + text + COLOR.RESET.value


class BaseCloudProvider:
    """
    Base class of cloud provider. This class is used for cloud detecting
    and collecting metadata/signature.

    The most of logic is implemented in this class. Subclasses
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
    # (e.g. /var/lib/cloud-what/cache/cool_cloud_metadata.json)
    METADATA_CACHE_FILE = None

    # Default value of path to holding signature of metadata
    # (e.g. /var/lib/cloud-what/cache/cool_cloud_signature.json)
    SIGNATURE_CACHE_FILE = None

    # Custom HTTP headers like user-agent
    HTTP_HEADERS = {}

    # Some collector can use a token that expires within some time limit. Thus such token can be
    # cached to some file
    TOKEN_CACHE_FILE = None

    # When a token is supported by cloud provider, then this value is in seconds
    CLOUD_PROVIDER_TOKEN_TTL = None

    # Time to live of in-memory cache for metadata and signature (value is in seconds)
    IN_MEMORY_CACHE_TTL = 10.0

    # Timeout for connection with IMDS server. The value is in seconds. Default value 1.0 second
    # should be enough, because IMDS server is usually in the same datacenter and delay should
    # be in milliseconds
    TIMEOUT = 1.0

    # Instances of BaseCloudProviders and subclasses behave as singletons to be able
    # to use in-memory cache
    _instance = None

    # Instance of singleton is initialized only once, when instance is created
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """
        Instance of cloud provider is singleton
        :param args:
        :param kwargs:
        """
        if not isinstance(cls._instance, cls):
            # When there is not existing instance, then create first one
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self, hw_info: dict = None):
        """
        Initialize cloud provider
        :param hw_info: Dictionary with hardware information.
        """

        # When instance of singleton have been already initialized, then
        # it is not necessary to initialize instance anymore
        if self._initialized is True:
            return

        # In-memory cache of metadata
        self._cached_metadata: Union[str, None] = None
        # Time, when metadata was received. The value is in seconds (unix time)
        self._cached_metadata_ctime: Union[float, None] = None
        # In-memory cache of signature
        self._cached_signature: Union[str, None] = None
        # Time, when signature was received. The value is in seconds (unix time)
        self._cached_signature_ctime: Union[float, None] = None

        # Dictionary with hardware information
        if hw_info is None:
            self.hw_info: dict = self.collect_hw_facts()
        else:
            self.hw_info: dict = hw_info

        # HTTP Session
        self._session = requests.Session()
        if os.environ.get("SUBMAN_DEBUG_PRINT_RESPONSE", ""):
            self._session.hooks["response"].append(self._cb_debug_print_http_response)

        # In-memory cache of token. The token is simple string
        self._token: Union[str, None] = None
        # Time, when token was received. The value is in seconds (unix time)
        self._token_ctime: Union[float, None] = None
        # Time to Live of token
        self._token_ttl: Union[float, None] = None

        self._initialized = True

    @staticmethod
    def collect_hw_facts() -> dict:
        """
        Try to collect hardware facts
        :return: Dictionary with hardware facts
        """
        # TODO: implement some minimalistic hardware collector
        return {}

    def is_vm(self) -> bool:
        """
        Is current system virtual machine?
        :return: Return True, when it is virtual machine; otherwise return False
        """
        return "virt.is_guest" in self.hw_info and self.hw_info["virt.is_guest"] is True

    def is_running_on_cloud(self) -> bool:
        """
        Try to guess cloud provider using collected hardware information
        (output of dmidecode, virt-what, etc.)

        :return:
            True, when we detected sign of cloud provider in hw info;
            otherwise False
        """
        raise NotImplementedError

    def is_likely_running_on_cloud(self) -> float:
        """
        When all subclasses cannot detect cloud provider using method
        is_running_on_cloud, because cloud provider started to provide something
        else in output of dmidecode, then try to use this heuristics method

        :return:
            Float value representing probability that vm is running using
            specific cloud provider
        """
        raise NotImplementedError

    def _write_token_to_cache_file(self) -> None:
        """
        Try to write token to cache file
        :return: None
        """
        if self._token is None or self._token_ctime is None or self.TOKEN_CACHE_FILE is None:
            log.debug(f"Unable to write {self.CLOUD_PROVIDER_ID} token to cache file due to missing data")
            return None

        token_cache_content = {
            "ctime": str(self._token_ctime),
            "ttl": str(self._token_ttl),
            "token": self._token,
        }

        token_cache_dir = os.path.dirname(self.TOKEN_CACHE_FILE)
        try:
            os.makedirs(token_cache_dir, exist_ok=True)
        except OSError as err_msg:
            log.debug(f"Unable to create cache directory {token_cache_dir}: {err_msg}")
            return

        log.debug(f"Writing {self.CLOUD_PROVIDER_ID} token to file {self.TOKEN_CACHE_FILE}")

        try:
            with open(self.TOKEN_CACHE_FILE, "w") as token_cache_file:
                json.dump(token_cache_content, token_cache_file)
        except IOError as err_msg:
            log.error(f"Unable to write token to cache file: {self.TOKEN_CACHE_FILE}: {err_msg}")
        else:
            # Only owner (root) should be able to read the token file
            os.chmod(self.TOKEN_CACHE_FILE, 0o600)

    @staticmethod
    def _is_in_memory_cache_valid(cache, ctime: float, ttl: float) -> bool:
        """
        Check if in-memory cache is still valid
        :param cache: cache object
        :param ctime: time, when cache was created
        :param ttl: time to live of cache
        :return: Return True, when cache is still valid. Otherwise return False.
        """
        if cache is None or ctime is None:
            return False

        current_time = time.time()
        if current_time < ctime + ttl:
            return True
        else:
            return False

    def _is_in_memory_cached_token_valid(self) -> bool:
        """
        Check if cached token is still valid
        :return: True, when cached token is valid; otherwise return False
        """
        return self._is_in_memory_cache_valid(
            self._token,
            self._token_ctime,
            self.CLOUD_PROVIDER_TOKEN_TTL,
        )

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
        log.debug(f"Reading cache file with {self.CLOUD_PROVIDER_ID} token: {self.TOKEN_CACHE_FILE}")

        if not os.path.exists(self.TOKEN_CACHE_FILE):
            log.debug(
                f"Cache file: {self.TOKEN_CACHE_FILE} with {self.CLOUD_PROVIDER_ID} token does not exist"
            )
            return None

        with open(self.TOKEN_CACHE_FILE, "r") as token_cache_file:
            try:
                cache_file_content = token_cache_file.read()
            except OSError as err:
                log.error(f"Unable to load token cache file: {self.TOKEN_CACHE_FILE}: {err}")
                return None
        try:
            cache = json.loads(cache_file_content)
        except json.JSONDecodeError as err:
            log.error(f"Unable to parse token cache file: {self.TOKEN_CACHE_FILE}: {err}")
            return None

        required_keys = ["ctime", "token", "ttl"]
        for key in required_keys:
            if key not in cache:
                log.error(f"Required key: {key} is not included in token cache file: {self.TOKEN_CACHE_FILE}")
                return None

        try:
            ctime = float(cache["ctime"])
        except ValueError as err:
            log.error(f"Wrong ctime value in {self.TOKEN_CACHE_FILE}, error: {err}")
            return None
        else:
            self._token_ctime = ctime

        try:
            ttl = float(cache["ttl"])
        except ValueError as err:
            log.warning(
                f"Wrong TTL value in {self.TOKEN_CACHE_FILE} "
                f"error: {err} "
                f"using default value: {self.CLOUD_PROVIDER_TOKEN_TTL}"
            )
            ttl = self.CLOUD_PROVIDER_TOKEN_TTL
        self._token_ttl = ttl

        if time.time() < ctime + ttl:
            log.debug(
                f"Cache file: {self.TOKEN_CACHE_FILE} with {self.CLOUD_PROVIDER_ID} token read successfully"
            )
            return cache["token"]
        else:
            log.debug(
                f"Cache file with {self.CLOUD_PROVIDER_ID} token file: {self.TOKEN_CACHE_FILE} timed out"
            )
            return None

    def _get_metadata_from_in_memory_cache(self) -> Union[str, None]:
        """
        Method for getting metadata from in-memory cache
        :return: String, when cache is valid. Otherwise return None
        """
        valid = self._is_in_memory_cache_valid(
            self._cached_metadata,
            self._cached_metadata_ctime,
            self.IN_MEMORY_CACHE_TTL,
        )

        if valid is True:
            return self._cached_metadata
        else:
            return None

    def _get_metadata_from_cache(self) -> Union[str, None]:
        """
        Method for gathering metadata from cache file
        :return: string containing metadata
        """
        raise NotImplementedError

    @staticmethod
    def _debug_print_http_request(request: requests.PreparedRequest) -> None:
        """
        Print HTTP request that will be sent using requests Python package
        :param request: prepared HTTP request
        :return: None
        """
        print(colorize("Request:", COLOR.GREEN))
        print(colorize(f"{request.method} {request.url}", COLOR.RED))

        if os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST_HEADER", ""):
            print(colorize("Request headers:", COLOR.GREEN))
            print(colorize(f"{request.headers}", COLOR.BLUE))

        if os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST_BODY", "") and hasattr(request, "body"):
            print(colorize("Request body:", COLOR.GREEN))
            print(colorize(f"{request.body}", COLOR.YELLOW))

        print()

    @staticmethod
    def _cb_debug_print_http_response(response: requests.Response, *args, **kwargs) -> requests.Response:
        """
        Callback method for printing HTTP response. It uses requests API.
        :param response: Instance of response. The response is not altered
        :param *args: Not used
        :param **kwargs: Not used
        :return: Instance of response
        """
        print(colorize("Response:", COLOR.GREEN))
        print(colorize(f"{response.status_code}", COLOR.RED))

        print(colorize("Response headers:", COLOR.GREEN))
        print(colorize(f"{response.headers}", COLOR.BLUE))

        print(colorize("Response content:", COLOR.GREEN))
        print(colorize(f"{response.text}", COLOR.YELLOW))

        return response

    def _get_data_from_server(self, data_type: str, url: str, headers: dict = None) -> Union[str, None]:
        """
        Try to get some data from server using method GET
        :param data_type: string representing data type (metadata, signature, token, etc.)
        :param url: URL of the GET request
        :param headers: optional headers parameters. When not set, then self.HTTP_HEADERS are used
        :return: String representing body, when status code is 200; Otherwise return None
        """
        log.debug(f"Trying to get {data_type} from {url}")

        if headers is None:
            headers = self.HTTP_HEADERS

        http_req = requests.Request(method="GET", url=url, headers=headers)
        prepared_http_req = self._session.prepare_request(http_req)

        if os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST", ""):
            self._debug_print_http_request(prepared_http_req)

        try:
            response = self._session.send(prepared_http_req, timeout=self.TIMEOUT)
        except requests.RequestException as err:
            log.debug(f"Unable to get {self.CLOUD_PROVIDER_ID} {data_type}: {err}")
        else:
            if response.status_code == 200:
                return response.text
            else:
                log.debug(f"Unable to get {self.CLOUD_PROVIDER_ID} {data_type}: {response.status_code}")

    def _get_metadata_from_server(self, headers: dict = None) -> Union[str, None]:
        """
        Method for gathering metadata from server
        :return: String containing metadata or None
        """
        self._cached_metadata = self._get_data_from_server(
            data_type="metadata",
            url=self.CLOUD_PROVIDER_METADATA_URL,
            headers=headers,
        )
        if self._cached_metadata is not None:
            self._cached_metadata_ctime = time.time()
        return self._cached_metadata

    def _get_signature_from_in_memory_cache(self) -> Union[str, None]:
        """
        Method for getting signature from in-memory cache
        :return: String, when cache is valid. Otherwise return None
        """
        valid = self._is_in_memory_cache_valid(
            self._cached_signature,
            self._cached_signature_ctime,
            self.IN_MEMORY_CACHE_TTL,
        )

        if valid is True:
            return self._cached_signature
        else:
            return None

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
        self._cached_signature = self._get_data_from_server("signature", self.CLOUD_PROVIDER_SIGNATURE_URL)
        if self._cached_signature is not None:
            self._cached_signature_ctime = time.time()
        return self._cached_signature

    def get_signature(self) -> Union[str, None]:
        """
        Public method for getting signature (cache file or server)
        :return: String containing signature or None
        """
        signature = self._get_signature_from_in_memory_cache()
        if signature is not None:
            log.debug("Using signature from in-memory cache")
            return signature

        signature = self._get_signature_from_cache_file()
        if signature is not None:
            return signature

        return self._get_signature_from_server()

    def get_metadata(self) -> Union[str, None]:
        """
        Public method for getting metadata (cache file or server)
        :return: String containing signature or None
        """
        metadata = self._get_metadata_from_in_memory_cache()
        if metadata is not None:
            log.debug("Using metadata from in-memory cache")
            return metadata

        metadata = self._get_metadata_from_cache()
        if metadata is not None:
            return metadata

        return self._get_metadata_from_server()
