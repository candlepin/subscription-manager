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

import imp
import os
import sys

import logging
log = logging.getLogger('rhsm-app.' + __name__)


class GaImporter(object):
    namespace = "subscription_manager.ga"
    virtual_modules = {}

    def __init__(self):
        log.debug("ga_loader %s", self.__class__.__name__)

    def find_module(self, fullname, path):
        if fullname in self.virtual_modules:
            return self
        return None

    def load_module(self, fullname):
        log.debug("ga_loader class %s loading virtual module %s from %s",
                  self.__class__.__name__,
                  fullname, self.virtual_modules[fullname])
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
        ret = sys.modules.setdefault(fullname, imp.new_module(fullname))
        ret.__name__ = fullname
        ret.__loader__ = self
        ret.__filename__ = fullname
        ret.__path__ = [fullname]
        ret.__package__ = '.'.join(fullname.split('.')[:-1])
        return ret

    def _namespace_module(self):
        return self._new_module(self.namespace)

    def _dirprint(self, module):
        return
        print "module ", module, type(module)
        for i in dir(module):
            if i == "__builtins__":
                continue
            print "\t%s = %s" % (i, getattr(module, i))


class GaImporterGtk3(GaImporter):
    virtual_modules = {'subscription_manager.ga': None,
                       'subscription_manager.ga.gtk_compat': ['subscription_manager.ga_impls',
                                                              'ga_gtk3'],
                       'subscription_manager.ga.GObject': ['gi.repository',
                                                           'GObject'],
                       'subscription_manager.ga.Gdk': ['gi.repository',
                                                       'Gdk'],
                       'subscription_manager.ga.Gtk': ['gi.repository',
                                                       'Gtk'],
                       'subscription_manager.ga.GLib': ['gi.repository',
                                                        'GLib'],
                       'subscription_manager.ga.GdkPixbuf': ['gi.repository',
                                                             'GdkPixbuf'],
                       'subscription_manager.ga.Pango': ['gi.repository',
                                                         'Pango']}


class GaImporterGtk2(GaImporter):
    virtual_modules = {'subscription_manager.ga': None,
                       'subscription_manager.ga.gtk_compat': ['subscription_manager.ga_impls',
                                                              'ga_gtk2'],
                       'subscription_manager.ga.GObject': ['subscription_manager.ga_impls.ga_gtk2',
                                                           'GObject'],
                       'subscription_manager.ga.Gdk': ['subscription_manager.ga_impls.ga_gtk2',
                                                       'Gdk'],
                       'subscription_manager.ga.Gtk': ['subscription_manager.ga_impls.ga_gtk2',
                                                       'Gtk'],
                       'subscription_manager.ga.GLib': ['subscription_manager.ga_impls.ga_gtk2',
                                                        'GLib'],
                       'subscription_manager.ga.GdkPixbuf': ['subscription_manager.ga_impls.ga_gtk2',
                                                             'GdkPixbuf'],
                       'subscription_manager.ga.Pango': ['subscription_manager.ga_impls.ga_gtk2',
                                                         'Pango']}


def init_ga():
    GTK_VERSION = "3"
    if 'SUBMAN_GTK_VERSION' in os.environ:
        GTK_VERSION = os.environ.get('SUBMAN_GTK_VERSION')

    if GTK_VERSION == "3":
        sys.meta_path.append(GaImporterGtk3())
    if GTK_VERSION == "2":
        sys.meta_path.append(GaImporterGtk2())
