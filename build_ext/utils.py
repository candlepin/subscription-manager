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
import fnmatch
import os

from distutils import cmd


def memoize(f):
    """ Memoization decorator for functions taking one or more arguments. """
    # Thanks to http://code.activestate.com/recipes/578231-probably-the-fastest-memoization-decorator-in-the-/
    class memodict(dict):
        def __init__(self, f):
            self.f = f

        def __call__(self, *args):
            return self[args]

        def __missing__(self, key):
            ret = self[key] = self.f(*key)
            return ret

    return memodict(f)


class BaseCommand(cmd.Command):
    """Command is an abstract class that requires initialize_options, finalize_options,
    and user_options to be defined.  This class provides stub definitions and other
    utility methods.
    """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


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
    def find_files_of_type(directory, *globs):
        if not os.path.isabs(directory):
            directory = os.path.join(os.curdir, directory)
        for path, dirnames, filenames in os.walk(directory):
            for f in filenames:
                for g in globs:
                    if fnmatch.fnmatch(f, g):
                        yield os.path.normpath(os.path.join(path, f))
