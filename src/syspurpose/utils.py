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
Utility methods for the syspurpose command
"""

import io
import json
import os
import errno
import logging

log = logging.getLogger(__name__)


def create_dir(path: str) -> bool:
    """
    Attempts to create the path given (less any file)
    :param path: path
    :return: True if changes were made, false otherwise
    """
    try:
        os.makedirs(path, mode=0o755)
    except OSError as e:
        if e.errno == errno.EEXIST:
            # If the directory exists no changes necessary
            return False
        if e.errno == errno.EACCES:
            log.error("Cannot create directory {}".format(path))
    return True


def create_file(path: str, contents: dict) -> bool:
    """
    Attempts to create a file, with the given contents
    :param path: The desired path to the file
    :param contents: The contents to write to the file, should json-serializable
    :return: True if the file was newly created, false otherwise
    """
    try:
        with io.open(path, "w", encoding="utf-8") as f:
            write_to_file_utf8(f, contents)
            f.flush()

    except OSError as e:
        if e.errno == errno.EEXIST:
            # If the file exists no changes necessary
            return False
        if e.errno == errno.EACCES:
            log.error("Cannot create file {}".format(path))
        else:
            raise
    return True


def write_to_file_utf8(file, data: dict) -> None:
    """
    Writes out the provided data to the specified file, with user-friendly indentation,
    and in utf-8 encoding
    :param file: The file to write to
    :param data: The data to be written
    :return:
    """
    file.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
