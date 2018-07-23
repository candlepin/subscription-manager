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
from syspurpose.utils import system_exit, create_dir, create_file

# This modules contains utilities for manipulating files pertaining to system syspurpose

# Constants for locations of the two system syspurpose files
USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"
VALID_FIELDS = "/etc/rhsm/syspurpose/valid_fields.json"  # Will be used for future validation


class SyspurposeStore(object):
    """
    Represents and maintains a json syspurpose file
    """

    def __init__(self, path):
        self.path = path
        self.contents = {}

    def read_file(self):
        """
        Opens & reads the contents of the store's file based on the 'path' provided to the constructor,
        and stores them on this object. If the user doesn't have access rights to the file, the program exits.
        :return: False if the contents of the file were empty, or the file doesn't exist; otherwise, nothing.
        """
        try:
            with open(self.path, 'r') as f:
                self.contents = json.load(f)
                return True
        except ValueError:
            return False
        except OSError as e:
            if e.errno == os.errno.EACCES:
                system_exit(os.EX_NOPERM,
                            'Cannot read syspurpose file {}\nAre you root?'.format(self.path))
        except IOError as ioerr:
            if ioerr.errno == os.errno.ENOENT:
                return False

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
        Add a value to a list of values specified by key
        :param key: The name of the list
        :param value: The value to append to the list
        :return: None
        """
        try:
            self.contents[key].append(value)
        except (AttributeError, KeyError):
            self.contents[key] = [value]
        return True

    def remove(self, key, value):
        """
        Remove a value from a list specified by key.
        :param key: The name of the list parameter to manipulate
        :param value: The value to attempt to remove
        :return: True if the value was in the list, False if it was not
        """
        try:
            self.contents[key].remove(value)
            return True
        except (AttributeError, KeyError, ValueError):
            return False

    def unset(self, key):
        """
        Unsets a key
        :param key: The key to unset
        :return: boolean
        """
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
        org = self.contents.get(key, None)
        self.contents[key] = value
        return org != value or org is None

    def write(self, fp=None):
        """
        Write the current contents to the file at self.path
        """
        if not fp:
            with open(self.path, 'w') as f:
                json.dump(self.contents, f)
                f.flush()
        else:
            json.dump(self.contents, fp)

    @classmethod
    def read(cls, path):
        """
        Read the file represented by path. If the file does not exist it is created.
        :param path: The path on the file system to read, should be a json file
        :return: new SyspurposeStore with the contents read in
        """
        new_store = cls(path)

        if not os.access(path, os.W_OK):
            new_store.create()
        else:
            new_store.read_file()

        return new_store
