#!/usr/bin/python
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

import glob
import imp
import inspect
import os
import sys

from subscription_manager.base_plugin import SubManPlugin

import logging
log = logging.getLogger('rhsm-app.' + __name__)

import gettext
_ = gettext.gettext

# The API_VERSION constant defines the current plugin API version. It is used
# to decided whether or not plugins can be loaded. It is compared against the
# 'requires_api_version' attribute of each plugin. The version number has the
# format: "major_version.minor_version".
#
# For a plugin to be loaded, the major version required by the plugin must match
# the major version in API_VERSION. Additionally, the minor version in
# API_VERSION must be greater than or equal the minor version required by the
# plugin.
#
# If a change is made that breaks backwards compatibility with regard to the plugin
# API, the major version number must be incremented and the minor version number
# reset to 0. If a change is made that doesn't break backwards compatibility,
# then the minor number must be incremented.
API_VERSION = "1.0"

SLOTS = [
    "post_product_id_install",
    ]


class PluginException(Exception):
    pass


class BaseConduit(object):
    def __init__(self, plugin_name):
        self.logger = logging.getLogger("rhsm-app." + plugin_name)

    def confValue(self, section, option, default=None):
        pass


class PluginManager(object):
    def __init__(self, search_path, plugin_conf_path=None):
        if not plugin_conf_path:
            plugin_conf_path = "/etc/rhsm/pluginconf.d"

        self.search_path = search_path
        self.plugin_conf_path = plugin_conf_path

    def run(self, slot_name, **kwargs):
        pass

    def _import_plugins(self):
        """Load all the plugins in the search path."""
        if not os.path.isdir(self.search_path):
            return

        self._plugins = {}
        self._plugin_funcs = {}
        for slot in SLOTS:
            self._plugin_funcs[slot] = []

        mask = os.path.join(self.search_path, "*.py")
        for module_file in sorted(glob.glob(mask)):
            self._load_plugin(module_file)

    def _load_plugin(self, module_file):
        """Load an individual plugin."""
        dir, module_name = os.path.split(module_file)
        module_name = module_name.split(".py")[0]

        try:
            fp, pathname, description = imp.find_module(module_name, [dir])
            try:
                module = imp.load_module(module_name, fp, pathname, description)
            finally:
                fp.close()
        except:
            log.error("Plugin \"%s\" can't be imported" % module_name)
            return

        if not hasattr(module, "requires_api_version"):
            log.error("Plugin \"%s\" doesn't specify required API version" % module_name)
            return
        if not api_version_ok(API_VERSION, module.requires_api_version):
            log.error("Plugin \"%s\" requires API version %s. Supported API is %s." %
                (module_name, module.requires_api_version, API_VERSION))
            return

        def is_plugin(c):
            return inspect.isclass(c) and c.__module__ == module_name and issubclass(c, SubManPlugin)

        plugin_classes = inspect.getmembers(sys.modules[module_name], is_plugin)
        for name, clazz in plugin_classes:
            conf = self._get_plugin_conf(name)
            #TODO check if plugin is disabled

            if name not in self._plugins:
                self._plugins[name] = (clazz, conf)
            else:
                raise PluginException("Two or more plugins with the name \"%s\" exist " \
                    "in the plugin search path" % name)

            for slot in SLOTS:
                func_name = slot + "_hook"
                if hasattr(clazz, func_name):
                    self._plugin_funcs[slot].append((name, getattr(clazz, func_name)))

    def _get_plugin_conf(self, module_name):
        pass

    def get_plugins(self):
        return self._plugins.keys()

    def get_hooks(self):
        return self._plugin_funcs


def parse_version(api_version):
    maj, min = api_version.split('.')
    return int(maj), int(min)


def api_version_ok(a, b):
    """
    Return true if API version "a" supports API version "b"
    """
    a = parse_version(a)
    b = parse_version(b)

    if a[0] != b[0]:
        return False

    if a[1] >= b[1]:
        return True

    return False


if __name__ == "__main__":
    from subscription_manager import logutil
    logutil.init_logger()
    subman_plugins = PluginManager("/tmp/my_plugins")
    subman_plugins._import_plugins()
    print "Plugins imported..."
    print subman_plugins.get_plugins()
    print "Hooks registered..."
    print subman_plugins.get_hooks()
