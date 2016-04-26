#
# Copyright (c) 2016 Red Hat, Inc.
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
import os
import fnmatch


class Utils(object):
    @staticmethod
    def create_dest_dir(dest):
        if not os.path.exists(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest))

    @staticmethod
    def run_if_new(src, dest, callback):
        Utils.create_dest_dir(dest)
        src_mtime = os.stat(src)[8]
        try:
            dest_mtime = os.stat(dest)[8]
        except OSError:
            dest_mtime = 0
        if src_mtime > dest_mtime:
            callback(src, dest)

    @staticmethod
    def find_files_of_type(directory, glob):
        if not os.path.isabs(directory):
            directory = os.path.join(os.curdir, directory)
        for path, dirnames, filenames in os.walk(directory):
            for f in filenames:
                if fnmatch.fnmatch(f, glob):
                    yield os.path.normpath(os.path.join(path, f))
