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
import os
import sys

import logging
log = logging.getLogger(__name__)

from subscription_manager import version

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
    """Custom module importer protocol that finds and loads the 'ga' Gtk2/Gtk3 compat virtual module.

    This implements the module "Importer Protocol" as defined
    in PEP302 (https://www.python.org/dev/peps/pep-0302/). It provides
    both a module finder (find_modules) and a module loader (load_modules).

    This lets different sub classes of this module to all provide a set of
    module names in the 'ga' namespace, but to provide different implementations.

    When an instance of this class is added to sys.meta_path, all imports that
    reference modules by name (ie, normal 'import bar' statements) the names are first passed
    to this classes 'find_module' method. When this class is asked for modules in
    the 'ga' package, it returns itself (which is also a module loader).

    This classes load_module() is used to decide which implemention of the 'ga'
    package to load. GaImporter.virtual_modules is a dict mapping full module name
    to the full name of the module that is to be loaded for that name.

    The 'ga' module implementations are in the ga_impls/ module.
    The available implementations are 'ga_gtk2' and 'ga_gtk3'.

    The 'ga' module itself provides a Gtk3-like API.

    The 'ga_impls/ga_gtk3' implementation is an export of the full 'gi.repository.Gtk',
    and a few helper methods and names.

    The 'ga_impls/ga_gtk2' implementation is more complicated. It maps a subset of
    Gtk2 names and widgets to their Gtk3 equilivent. This includes an assortment
    of class enums, and helper methods. The bulk of the API compat is just mapping
    names like 'gtk.Window' to Gtk style names like 'gi.repository.Gtk.Window'.

    NOTE: Only symbols actually used in subscription-manager are provided. This
          is not a general purpose Gtk3 interface for Gtk2. Names are imported
          directly and export directly in module __all__ attributes. This is to
          make sure any Gtk3 widgets used in subman have working gtk2 equilivents
          and ga_gtk2 provides it.
    """

    namespace = "subscription_manager.ga"
    virtual_modules = {}

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
                       'subscription_manager.ga.gtk_compat': ['subscription_manager.ga_impls.ga_gtk2',
                                                              'gtk_compat'],
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


def init_ga(gtk_version=None):
    """Decide which GaImporter implementation to load.

    Applications should import this module and call this method before
    importing anything from the 'ga' namespace.

    After calling this method, a GaImporter implementation is added to sys.meta_path.
    This sets up a module finder and loader that will return 'virtual' modules
    when asked for 'ga.Gtk' for example. Depending on the GaImporter, 'ga.Gtk'
    may be implemented with Gtk3 or gtk2.

    The default implementation is the gtk2 based one (DEFAULT_GTK_VERSION).

    The acceptable values of 'gtk_version' are '2' and '3', for gtk2 and
    gtk3.

    It can be overridden by, in order:

        Hardcoded DEFAULT_GTK_VERSION.
        (default is '2')

        The value of subscription_manager.version.gtk_version if it exists
        and is not None.
        (As set at build time)

        The 'gtk_version' argument to this method if not None.
        (The default is None)

        The value of the environment variable 'SUBMAN_GTK_VERSION' if set
        to '2' or '3'.
        (default is unset)
    """

    DEFAULT_GTK_VERSION = "2"
    gtk_version_from_build = None
    gtk_version_from_environ = os.environ.get('SUBMAN_GTK_VERSION')

    # ignore version.py info if it hasn't been set.
    if version.gtk_version != "GTK_VERSION":
        gtk_version_from_build = version.gtk_version
    else:
        # We should only be hitting this code in development when the version.py
        # hasn't been through the setup.py rendering process.
        import rpm
        import warnings
        # 0 if %rhel is undefined, rhel version if not
        rhel = rpm.expandMacro('%rhel', True)

        if rhel and rhel == 6:
            gtk_version_from_build = "2"
        else:
            gtk_version_from_build = "3"
        if gtk_version_from_environ is None:
            warnings.warn("GTK_VERSION is unset in version.py.  Using GTK %s" % gtk_version_from_build)

    GTK_VERSION = gtk_version_from_environ or gtk_version or gtk_version_from_build \
        or DEFAULT_GTK_VERSION

    if GTK_VERSION == "3":
        sys.meta_path.append(GaImporterGtk3())
    if GTK_VERSION == "2":
        sys.meta_path.append(GaImporterGtk2())
