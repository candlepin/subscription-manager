#
# Copyright (c) 2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import datetime
import logging
import os

# FIXME: We can likely dump this now
from rhsm import ourjson as json

log = logging.getLogger(__name__)


class Cache(object):
    def __init__(self, store=None):
        self.store = store or Store()

    @property
    def timestamp(self):
        return self.store.timestamp

    @property
    def exists(self):
        return self.store.exists

    @property
    def valid(self):
        return self.store.valid

    def write(self, data):
        self.store.write(data)

    def read(self):
        return self.store.read()

    def clear(self):
        pass


class Store(object):
    @property
    def timestamp(self):
        return None

    @property
    def exists(self):
        return None

    def write(self):
        pass

    def read(self):
        pass

    def clear(self):
        pass

# Will we need to make this prefix/chroot aware?


class FileStore(Store):
    def __init__(self, path=None):
        self.path = path
        self.fd = None

    def read(self):
        try:
            with open(self.path) as fd:
                return fd.read()
        except EnvironmentError as e:
            log.exception(e)
            log.error('Unable to read cache store at %s: %s', self.path, e)
            # FIXME: raise a specific useful exception

    def write(self, data):
        try:
            with open(self.path, 'w') as fd:
                fd.write(data)
        except EnvironmentError as e:
            log.exception(e)
            log.error('Unable to write cache store at %s: %s', self.path, e)
            # FIXME: raise useful exception

    def delete(self):
        try:
            os.remove(self.path)
        except EnvironmentError as e:
            log.debug('Unable to delete cache store at %s: %s', self.path, e)

    # TODO: write properties
    @property
    def timestamp(self):
        try:
            return datetime.fromtimestamp(os.stat(self.path).st_mtime)
        except Exception:
            return None

    @property
    def exists(self):
        try:
            return os.access(self.path, os.R_OK)
        except EnvironmentError as e:
            log.debug('Unable to access cache store at %s: %s', self.path, e)
            # TODO: raise something useful...
            return False


class FileCache(Cache):
    CACHE_FILE = None

    def __init__(self, file_store):
        self.store = file_store or FileStore(path=self.CACHE_FILE)


class JsonFileCache(FileCache):
    def __init__(self, file_store):
        super(JsonFileCache, self).__init__(file_store)
        self._json_encoder = json.JSONEncoder(default=json.encode)
        self._json_decoder = json.JSONDecoder()

    def write(self, data):
        self.store.write(self._json_encode(data))

    def read(self):
        return self._json_decode(self.store.read())

    def _json_encode(self, data):
        return self._json_encoder(data)

    def _json_decode(self, json_string):
        return self._json_decoder.decode(json_string)
