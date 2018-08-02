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


import json
import os
import io
from syspurpose.utils import system_exit, create_dir, create_file, make_utf8, write_to_file_utf8
from syspurpose.i18n import ugettext as _

# This modules contains utilities for manipulating files pertaining to system syspurpose

# Constants for locations of the two system syspurpose files
USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"
VALID_FIELDS = "/etc/rhsm/syspurpose/valid_fields.json"  # Will be used for future validation


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
            return False
        except OSError as e:
            if e.errno == os.errno.EACCES and not self.raise_on_error:
                system_exit(os.EX_NOPERM,
                            _('Cannot read syspurpose file {}\nAre you root?').format(self.path))
            if self.raise_on_error:
                raise e
        except IOError as ioerr:
            if ioerr.errno == os.errno.ENOENT:
                return False
            if self.raise_on_error:
                raise e

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
                self.contents[key] = None
                return True

            if value in self.contents[key]:
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
        org = self.contents.get(key, None)
        if org is not None:
            self.contents[key] = None
        return org is not None

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
        :return: new SyspurposeStore with the contents read in
        """
        new_store = cls(path, raise_on_error=raise_on_error)

        if not os.access(path, os.W_OK):
            new_store.create()
        else:
            new_store.read_file()

        return new_store
