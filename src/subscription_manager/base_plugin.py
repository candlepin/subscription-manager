from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
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


class SubManPlugin(object):
    """Base class for all subscription-manager "rhsm-plugins"

    Plugins need to subclass SubManPlugin() to be found
    """
    name = None
    conf = None
    # if all_slots is set, the plugin will get registered to all slots
    # it is up to the plugin to handle providing callables
    all_slots = None

    # did we have hooks that match provided slots? aka
    # is this plugin going to be used
    found_slots_for_hooks = False

    def __init__(self, conf=None):
        if conf:
            self.conf = conf
        if self.conf is None:
            raise TypeError("SubManPlugin can not be constructed with conf=None")

    def __str__(self):
        return self.name or self.__class__.__name__

    @classmethod
    def get_plugin_key(cls):
        return ".".join([cls.__module__, cls.__name__])
