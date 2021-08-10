from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2015 Red Hat, Inc.
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

import types
import sys

import logging
log = logging.getLogger(__name__)

""" Try importing from a 'ga' that is dynamic and imports
    the gi.repository style names into the module. This
    uses python's sys.metapath support to add a custom
    importer to the "front" of sys.path. The custom
    importer knows how to handle imports for
    'subscription_manager.ga'. The importer is in the
    ga_loader module, and is used to decide which impl
    of 'ga' is used (gtk2 or gtk3).

    Currently doing 'from subscription_manager.ga import GObject as ga_Gobject'
    since for gtk2 cases, it's not really GObject, and we avoid
    shadowing well known names, but maybe it doesn't matter.

    The 'virtual' module 'ga' will import the correct
    implementation from the ga_impls/ dir. ga_loader
    decides which version to use. It currently defaults
    to gtk3, with an env variable to override for testing.

"""


class GaImporter(object):
    """Module importer protocol that finds and loads 'ga' modules.

    Previously this was used to load GTK 2 or GTK 3 code to provide different
    implementations depending on what was available on the system.

    GUI in subscription-manager has been deprecated and removed. GLib is
    currently used for dbus communication.
    """

    namespace = "subscription_manager.ga"
    virtual_modules = {
        'subscription_manager.ga': None,
        'subscription_manager.ga.GObject': ['gi.repository', 'GObject'],
        'subscription_manager.ga.GLib': ['gi.repository', 'GLib'],
    }

    def __init__(self):
        log.debug("ga_loader %s", self.__class__.__name__)

    def find_module(self, fullname, path):
        if fullname in self.virtual_modules:
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]

        if fullname not in self.virtual_modules:
            raise ImportError(fullname)

        # The base namespace
        if fullname == self.namespace:
            return self._namespace_module()

        real_module_name = real_module_from = None
        mod_info = self.virtual_modules[fullname]
        if mod_info:
            real_module_name, real_module_from = mod_info

        if not real_module_from:
            raise ImportError(fullname)

        # looks like a real_module alias
        return self._import_real_module(fullname, real_module_name, real_module_from)

    def _import_real_module(self, fullname, module_name, module_from):
        ret = __import__(module_name, globals(), locals(), [module_from])
        inner_ret = getattr(ret, module_from)
        ret = inner_ret
        ret.__name__ = fullname
        ret.__loader__ = self
        ret.__package__ = True
        sys.modules[fullname] = ret
        return ret

    def _new_module(self, fullname):
        """Create a an empty module, we can populate with impl specific."""
        ret = sys.modules.setdefault(fullname, types.ModuleType(fullname))
        ret.__name__ = fullname
        ret.__loader__ = self
        ret.__filename__ = fullname
        ret.__path__ = [fullname]
        ret.__package__ = '.'.join(fullname.split('.')[:-1])
        return ret

    def _namespace_module(self):
        """Create and return a 'ga' package module.

        Since the 'ga' module has to work for Gtk2/Gtk3, but can't import
        either, we create a new module instance and add it to the system
        path.

        Imports like 'from ga import Gtk3' first have to import 'ga'. When
        they do, the module instance is the one we create here.
        """
        return self._new_module(self.namespace)


def init_ga():
    """Decide which GaImporter implementation to load.

    We are relying in GLib for the dbus communication. Previously, this function
    imported GTK 2 or GTK 3 depending on their support in the system.

    Now that GUI is deprecated only some parts of GTK 3 import code are used
    to provide the dbus communication.
    """
    sys.meta_path.append(GaImporter())
