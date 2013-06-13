# Copyright (c) 2011 Red Hat, Inc.
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


class LazyLoader(object):
    """
    Allows the injector to load singleton objects as needed
    To implement this, you must not have an init method
    The load method should do all initialization
    """
    loaded = False

    def __init__(self, *args, **kwargs):
        # Save args to pass through to self.load()
        self.args = args
        self.kwargs = kwargs

        # We would use default __init__(self, lazy_load=False):
        # However we want to preserve args to pass to load
        # Let's hope load doesn't also want an arg called lazy_load
        lazy_load = False
        if 'lazy_load' in kwargs:
            lazy_load = kwargs['lazy_load']
            del self.kwargs['lazy_load']

        if not lazy_load:
            self.load(*self.args, **self.kwargs)

    def load(self):
        self.loaded = True
