# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import
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

"""
This module contains utilities for manipulating files pertaining to system syspurpose
"""

import collections
import logging
import json
import os
import errno
import io
from syspurpose.utils import system_exit, create_dir, create_file, make_utf8, write_to_file_utf8
from syspurpose.i18n import ugettext as _

# Constants for locations of the two system syspurpose files
USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"
VALID_FIELDS = "/etc/rhsm/syspurpose/valid_fields.json"  # Will be used for future validation
CACHED_SYSPURPOSE = "/var/lib/rhsm/cache/syspurpose.json"  # Stores cached values

# All names that represent syspurpose values locally
ROLE = 'role'
ADDONS = 'addons'
SERVICE_LEVEL = 'service_level_agreement'
USAGE = 'usage'

# Remote values keyed on the local ones
LOCAL_TO_REMOTE = {
    ROLE: 'role',
    ADDONS: 'addOns',
    SERVICE_LEVEL: 'serviceLevel',
    USAGE: 'usage'
}

# All known syspurpose attributes
ATTRIBUTES = [ROLE, ADDONS, SERVICE_LEVEL, USAGE]


# Values used in determining changes between client and server
UNSUPPORTED = "unsupported"



log = logging.getLogger(__name__)


class SyspurposeStore(object):
    """
    Represents and maintains a json syspurpose file
    """

    def __init__(self, path, raise_on_error=False):
        self.path = path
        self.contents = {}
        self.raise_on_error = raise_on_error

    def read_file(self):
        """
        Opens & reads the contents of the store's file based on the 'path' provided to the constructor,
        and stores them on this object. If the user doesn't have access rights to the file, the program exits.
        :return: False if the contents of the file were empty, or the file doesn't exist; otherwise, nothing.
        """
        try:
            with io.open(self.path, 'r', encoding='utf-8') as f:
                self.contents = json.load(f, encoding='utf-8')
                return True
        except ValueError:
            # Malformed JSON or empty file. Let's not error out on an empty file
            if os.path.getsize(self.path):
                system_exit(os.EX_CONFIG,
                    _("Error: Malformed data in file {}; please review and correct.").format(self.path))

            return False
        except OSError as e:
            if e.errno == errno.EACCES and not self.raise_on_error:
                system_exit(os.EX_NOPERM,
                    _('Cannot read syspurpose file {}\nAre you root?').format(self.path))

            if self.raise_on_error:
                raise e
        except IOError as ioerr:
            if ioerr.errno == errno.ENOENT:
                return False
            if self.raise_on_error:
                raise ioerr

    def create(self):
        """
        Create the files necessary for this store
        :return: True if changes were made, false otherwise
        """
        return create_dir(os.path.dirname(self.path)) or \
            self.read_file() or \
            create_file(self.path, self.contents)

    def add(self, key, value):
        """
        Add a value to a list of values specified by key. If the current value specified by the key is scalar/non-list,
        it is not overridden, but maintained in the list, along with the new value.
        :param key: The name of the list
        :param value: The value to append to the list
        :return: None
        """
        value = make_utf8(value)
        key = make_utf8(key)
        try:
            current_value = self.contents[key]
            if current_value is not None and not isinstance(current_value, list):
                self.contents[key] = [current_value]

            if self.contents[key] is None:
                self.contents[key] = []

            if value not in self.contents[key]:
                self.contents[key].append(value)
            else:
                return False
        except (AttributeError, KeyError):
            self.contents[key] = [value]
        return True

    def remove(self, key, value):
        """
        Remove a value from a list specified by key.
        If the current value specified by the key is not a list, unset the value.
        :param key: The name of the list parameter to manipulate
        :param value: The value to attempt to remove
        :return: True if the value was in the list, False if it was not
        """
        value = make_utf8(value)
        key = make_utf8(key)
        try:
            current_value = self.contents[key]
            if current_value is not None and not isinstance(current_value, list) and current_value == value:
                return self.unset(key)

            if value in current_value:
                self.contents[key].remove(value)
            else:
                return False

            return True
        except (AttributeError, KeyError, ValueError):
            return False

    def unset(self, key):
        """
        Unsets a key
        :param key: The key to unset
        :return: boolean
        """
        key = make_utf8(key)

        # Special handling is required for the SLA, since it deviates from the typical CP
        # empty => null semantics
        if key == 'service_level_agreement':
            value = self.contents.get(key, None)
            self.contents[key] = ''
        else:
            value = self.contents.pop(key, None)

        return value is not None

    def set(self, key, value):
        """
        Set a key (syspurpose parameter) to value
        :param key: The parameter of the syspurpose file to set
        :type key: str

        :param value: The value to set that parameter to
        :return: Whether any change was made
        """
        value = make_utf8(value)
        key = make_utf8(key)
        org = make_utf8(self.contents.get(key, None))
        self.contents[key] = value
        return org != value or org is None

    def write(self, fp=None):
        """
        Write the current contents to the file at self.path
        """
        if not fp:
            with io.open(self.path, 'w', encoding='utf-8') as f:
                write_to_file_utf8(f, self.contents)
                f.flush()
        else:
            write_to_file_utf8(fp, self.contents)

    @classmethod
    def read(cls, path, raise_on_error=False):
        """
        Read the file represented by path. If the file does not exist it is created.
        :param path: The path on the file system to read, should be a json file
        :param raise_on_error: When it is set to True, then exceptions are raised as expected.
        :return: new SyspurposeStore with the contents read in
        """
        new_store = cls(path, raise_on_error=raise_on_error)

        if not os.access(path, os.W_OK):
            new_store.create()
        else:
            new_store.read_file()

        return new_store


class SyncResult(object):
    """
    A container class for the results of a sync operation performed by a SyncedStore class.
    """

    def __init__(self, result, remote_changed, local_changed, cached_changed, report):
        self.result = result
        self.remote_changed = remote_changed
        self.local_changed = local_changed
        self.cached_changed = cached_changed
        self.report = report


class SyncedStore(object):
    """
    Stores values in a local file backed by a cache which is then synced with another source
    of the same values.
    """
    PATH = USER_SYSPURPOSE
    CACHE_PATH = CACHED_SYSPURPOSE

    def __init__(self, uep, on_changed=None, consumer_uuid=None, report=None):
        self.uep = uep
        self.filename = self.PATH.split('/')[-1]
        self.path = self.PATH
        self.cache_path = self.CACHE_PATH
        self.report = report
        self.local_file = None
        self.local_contents = None
        self.local_contents = self.get_local_contents()
        self.cache_file = None
        self.cache_contents = None
        self.cache_contents = self.get_cached_contents()
        self.changed = False
        self.on_changed = on_changed
        self.consumer_uuid = consumer_uuid

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()

    def finish(self):
        if self.changed:
            self.sync()
            return True
        return False

    def sync(self):
        log.debug('Attempting to sync syspurpose content...')
        try:
            if self.uep and not self.uep.has_capability('syspurpose'):
                log.debug('Server does not support syspurpose, syncing only locally.')
                return self._sync_local_only()
        except:
            log.debug('Failed to detect whether the server has syspurpose capability')
            return self._sync_local_only()

        remote_contents = self.get_remote_contents()
        local_contents = self.get_local_contents()
        cached_contents = self.get_cached_contents()

        result = self.merge(local=local_contents,
                            remote=remote_contents,
                            base=cached_contents)

        local_result = {key: result[key] for key in result if result[key]}

        sync_result = SyncResult(result, self.update_remote(result),
                          self.update_local(local_result),
                          self.update_cache(result), self.report)

        log.debug('Successfully synced system purpose.')

        # Reset the changed attribute as all items should be synced if we've gotten to this point
        self.changed = False

        if self.report is not None:
            self.report._status = 'Successfully synced system purpose'

        return sync_result

    def _sync_local_only(self):
        local_updated = self.update_local(self.get_local_contents())
        return SyncResult(self.local_contents, False, local_updated, False, self.report)

    def merge(self, local=None, remote=None, base=None):
        result = three_way_merge(local=local, base=base, remote=remote,
                                     on_change=self.on_changed)
        return result

    def get_local_contents(self):
        try:
            if self.local_contents is None:
                self.local_contents = json.load(io.open(self.path, 'r', encoding='utf-8'))
                log.debug('Successfully read local syspurpose contents.')
            return self.local_contents
        except (os.error, ValueError, IOError):
            if self.report is not None:
                self.report._exceptions.append(
                        'Cannot read local syspurpose, trying to update from server only'
                )
            log.debug('Unable to read local system purpose at  \'%s\'\nUsing the server values.'
                      % USER_SYSPURPOSE)
            self.update_local({})
            self.local_contents = {}
            return self.local_contents

    def get_remote_contents(self):
        if self.uep is None or self.consumer_uuid is None:
            log.debug('Failed to read remote syspurpose from server: no available connection, '
                      'or the consumer is not registered.')
            return {}
        if not self.uep.has_capability('syspurpose'):
            log.debug('Server does not support syspurpose, not syncing.')
            return {}

        consumer = self.uep.getConsumer(self.consumer_uuid)
        result = {}

        # Translate from the remote values to the local, filtering out items not known
        for attr in ATTRIBUTES:
            value = consumer.get(LOCAL_TO_REMOTE[attr])
            result[attr] = value
        log.debug('Successfully read remote syspurpose from server.')

        return result

    def get_cached_contents(self):
        if not self.cache_contents:
            try:
                self.cache_contents = json.load(io.open(self.cache_path, 'r', encoding='utf-8'))
                log.debug('Successfully read cached syspurpose contents.')
            except (ValueError, os.error, IOError):
                log.debug('Unable to read cached syspurpose contents at \'%s\'.' % USER_SYSPURPOSE)
                self.cache_contents = {}
                self.update_cache({})
        return self.cache_contents

    def update_local(self, data):
        self.local_contents = data
        return self.update_file(self.path, data)

    def update_cache(self, data):
        self.cache_contents = data
        return self.update_file(self.cache_path, data)

    def update_remote(self, data):
        if self.uep is None or self.consumer_uuid is None:
            log.debug('Failed to update remote syspurpose on the server: no available connection, '
                      'or the consumer is not registered.')
            return False

        addons = data.get(ADDONS)
        self.uep.updateConsumer(
                self.consumer_uuid,
                role=data.get(ROLE) or "",
                addons=addons if addons is not None else [],
                service_level=data.get(SERVICE_LEVEL) or "",
                usage=data.get(USAGE) or ""
        )
        log.debug('Successfully updated remote syspurpose on the server.')
        return True

    def add(self, key, value):
        """
        Add a value to a list of values specified by key. If the current value specified by the key is scalar/non-list,
        it is not overridden, but maintained in the list, along with the new value.
        :param key: The name of the list
        :param value: The value to append to the list
        :return: None
        """
        value = make_utf8(value)
        key = make_utf8(key)
        try:
            current_value = self.local_contents[key]
            if current_value is not None and not isinstance(current_value, list):
                self.local_contents[key] = [current_value]

            if self.local_contents[key] is None:
                self.local_contents[key] = []

            if value not in self.local_contents[key]:
                self.local_contents[key].append(value)
            else:
                log.debug('Will not add value \'%s\' to key \'%s\'.' % (value, key))
                return False
        except (AttributeError, KeyError):
            self.local_contents[key] = [value]
        self.changed = True
        log.debug('Adding value \'%s\' to key \'%s\'.' % (value, key))
        return True

    def remove(self, key, value):
        """
        Remove a value from a list specified by key.
        If the current value specified by the key is not a list, unset the value.
        :param key: The name of the list parameter to manipulate
        :param value: The value to attempt to remove
        :return: True if the value was in the list, False if it was not
        """
        value = make_utf8(value)
        key = make_utf8(key)
        try:
            current_value = self.local_contents[key]
            if current_value is not None and not isinstance(current_value, list) and current_value == value:
                return self.unset(key)

            if value in current_value:
                self.local_contents[key].remove(value)
            else:
                return False
            self.changed = True
            log.debug('Removing value \'%s\' from key \'%s\'.' % (value, key))
            return True
        except (AttributeError, KeyError, ValueError):
            log.debug('Will not remove value \'%s\' from key \'%s\'.' % (value, key))
            return False

    def unset(self, key):
        """
        Unsets a key
        :param key: The key to unset
        :return: boolean
        """
        key = make_utf8(key)

        # Special handling is required for the SLA, since it deviates from the typical CP
        # empty => null semantics
        if key == 'service_level_agreement':
            value = self.local_contents.get(key, None)
            self.local_contents[key] = ''
        elif key == 'addons':
            value = self.local_contents.get(key, None)
            self.local_contents[key] = []
        else:
            value = self.local_contents.pop(key, None)
        self.changed = True
        log.debug('Unsetting value \'%s\' of key \'%s\'.' % (value, key))

        return value is not None

    def set(self, key, value):
        """
        Set a key (syspurpose parameter) to value
        :param key: The parameter of the syspurpose file to set
        :type key: str

        :param value: The value to set that parameter to
        :return: Whether any change was made
        """
        value = make_utf8(value)
        key = make_utf8(key)
        org = make_utf8(self.local_contents.get(key, None))
        self.local_contents[key] = value

        if org != value or org is None:
            self.changed = True
            log.debug('Setting value \'%s\' to key \'%s\'.' % (value, key))

        return org != value or org is None

    @staticmethod
    def update_file(path, data):
        """
        Write the contents of data to file in the first mode we can (effectively to create or update
        the file)
        :param path: The string path to the file location we should update
        :param data: The data to write to the file
        :return: None
        """
        modes = ['w+']
        for mode in modes:
            try:
                f = io.open(path, mode, encoding='utf-8')
            except OSError as e:
                if e.errno != 17:
                    raise
            else:
                write_to_file_utf8(f, data)
                f.flush()
                f.close()
                log.debug('Successfully updated syspurpose values at \'%s\'.' % path)
                return True
        log.debug('Failed to update syspurpose values at \'%s\'.' % path)
        return False


def read_syspurpose(raise_on_error=False):
    """
    Reads the system purpose from the correct location on the file system.
    Makes an attempt to use a SyspurposeStore if available falls back to reading the json directly.
    :return: A dictionary containing the total syspurpose.
    """
    if SyspurposeStore is not None:
        try:
            syspurpose = SyspurposeStore(None).get_local_contents()
        except (OSError, IOError):
            syspurpose = {}
    else:
        try:
            syspurpose = json.load(open(USER_SYSPURPOSE))
        except (os.error, ValueError, IOError):
            # In the event this file could not be read treat it as empty
            if raise_on_error:
                raise
            syspurpose = {}
    return syspurpose


# A simple container class used to hold the values representing a change detected
# during three_way_merge
DiffChange = collections.namedtuple('DiffChange', ['key', 'previous_value', 'new_value', 'source', 'in_base', 'in_result'])


def three_way_merge(local, base, remote, on_conflict="remote", on_change=None):
    """
    Performs a three-way merge on the local and remote dictionaries with a given base.
    :param local: The dictionary of the current local values
    :param base: The dictionary with the values we've last seen
    :param remote: The dictionary with "their" values
    :param on_conflict: Either "remote" or "local" or None. If "remote", the remote changes
                               will win any conflict. If "local", the local changes will win any
                               conflict. If anything else, an error will be thrown.
    :param on_change: This is an optional function which will be given each change as it is
                      detected.
    :return: The dictionary of values as merged between the three provided dictionaries.
    """
    log.debug('Attempting a three-way merge...')
    result = {}
    local = local or {}
    base = base or {}
    remote = remote or {}

    if on_conflict == "remote":
        winner = remote
    elif on_conflict == "local":
        winner = local
    else:
        raise ValueError('keyword argument "on_conflict" must be either "remote" or "local"')

    if on_change is None:
        on_change = lambda change: change

    all_keys = set(local.keys()) | set(base.keys()) | set(remote.keys())

    for key in all_keys:

        local_changed = detect_changed(base=base, other=local, key=key, source="local")
        remote_changed = detect_changed(base=base, other=remote, key=key, source="server")
        changed = local_changed or remote_changed and remote_changed != UNSUPPORTED
        source = 'base'

        if local_changed == remote_changed:
            if local_changed == True:
                log.debug('Three way merge conflict: both local and remote values changed for key \'%s\'.' % key)
            source = on_conflict
            if key in winner:
                result[key] = winner[key]
        elif remote_changed is True:
            log.debug('Three way merge: remote value was changed for key \'%s\'.' % key)
            source = 'remote'
            if key in remote:
                result[key] = remote[key]
        elif local_changed or remote_changed == UNSUPPORTED:
            if local_changed == True:
                log.debug('Three way merge: local value was changed for key \'%s\'.' % key)
            source = 'local'
            if key in local:
                result[key] = local[key]

        if changed:
            original = base.get(key)
            diff = DiffChange(key=key, source=source, previous_value=original,
                              new_value=result.get(key), in_base=key in base,
                              in_result=key in result)
            on_change(diff)

    return result


def detect_changed(base, other, key, source="server"):
    """
    Detect the type of change that has occurred between base and other for a given key.
    :param base: The dictionary of values we are starting with
    :param other: The dictionary of now current values
    :param key: The key that we are interested in knowing how it changed
    :param source: An optional string which indicates where the "other" values came from. Used to
                   make decisions which are one sided. (i.e. only applicable for changes from the
                   server side).
    :return: True if there was a change, false if there was no change
    :rtype: bool
    """
    base = base or {}
    other = other or {}
    if key not in other and source != "local":
        return UNSUPPORTED

    base_val = base.get(key)
    other_val = other.get(key)

    if key not in other and source == "local":
        # If the local values no longer contain the key we want to treat this as removal
        # It would constitute a change if the base had a truthy value. The values tracked from the
        # server all have falsey values.
        return bool(base_val)

    # Handle "addons" (the lists might be out of order from the server)
    if type(base_val) == list and type(other_val) == list:
        return sorted(base_val) != sorted(other_val)

    return base_val != other_val
