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
    "pre_product_id_install",
    "post_product_id_install",
    ]


class PluginException(Exception):
    pass


class PluginImportException(PluginException):
    def __init__(self, module_file, module_name, msg=None):
        self.module_file = module_file
        self.module_name = module_name
        self.msg = msg

    def __repr__(self):
        repr = "Plugin \"%s\" can't be imported from file %s" % (module_name, module_file)
        if self.msg:
            "\n".join(repr, "Message: %s" % self.msg)


class PluginImportApiVersionException(PluginImportException):
    def __init__(self, module_file, module_name, module_ver, api_ver, msg=None):
        self.module_file = module_file
        self.module_name = module_name
        self.module_ver = module_ver
        self.api_ver = api_ver
        self.msg = msg

    def __repr__(self):
        repr = "Plugin \"%s\" requires API version %s. Supported API is %s." % (module_name, module_ver, api_ver)
        if self.msg:
            "\n".join(repr, "Message: %s" % self.msg)


class BaseConduit(object):
    slots = []
    def __init__(self, clazz):
        self.logger = logging.getLogger("rhsm-app." + clazz.__name__)

    def confValue(self, section, option, default=None):
        pass


class ProductConduit(BaseConduit):
    slots = ['pre_product_id_install', 'post_product_id_install']
    pass


class PluginManager(object):
    def __init__(self, search_path, plugin_conf_path=None):
        if not plugin_conf_path:
            plugin_conf_path = "/etc/rhsm/pluginconf.d"

        self.search_path = search_path
        self.plugin_conf_path = plugin_conf_path

        self._plugins = {}
        self._plugin_funcs = {}
        self.conduits = [BaseConduit, ProductConduit]
        self._slot_to_conduit = {}

        for conduit_class in self.conduits:
            slots = conduit_class.slots
            for slot in slots:
                self._slot_to_conduit[slot] = conduit_class

        for slot in SLOTS:
            self._plugin_funcs[slot] = []

    def run(self, slot_name, **kwargs):
        #TODO figure out which conduit to send in
        for func in self._plugin_funcs[slot_name]:
            log.debug("Running %s plugin" % func)
            # resolve slot_name to conduit
            print self._slot_to_conduit
            conduit = self._slot_to_conduit[slot_name]
            func(conduit(func.im_class))

    def _import_plugins(self):
        """Load all the plugins in the search path."""
        if not os.path.isdir(self.search_path):
            return

        mask = os.path.join(self.search_path, "*.py")
        for module_file in sorted(glob.glob(mask)):
            try:
                self._load_plugin(module_file)
            except PluginException, e:
                log.error(e)

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
            raise PluginImportException(module_file, module_name)

        if not hasattr(module, "requires_api_version"):
            raise PluginImportException(module_file, module_name, "Plugin doesn't specify required API version")
        if not api_version_ok(API_VERSION, module.requires_api_version):
            raise PluginImportApiVersionException(module_file, module_name, module_ver=module.requires_api_version, api_ver=API_VERSION)

        def is_plugin(c):
            return inspect.isclass(c) and c.__module__ == module_name and issubclass(c, SubManPlugin)

        plugin_classes = inspect.getmembers(sys.modules[module_name], is_plugin)
        for name, clazz in sorted(plugin_classes):
            conf = self._get_plugin_conf(name)
            #TODO check if plugin is disabled

            instance = clazz()
            plugin_key = ".".join([module_name, name])
            if plugin_key not in self._plugins:
                self._plugins[plugin_key] = (instance, conf)
            else:
                # This shouldn't ever happen
                raise PluginException("Two or more plugins with the name \"%s\" exist " \
                    "in the plugin search path" % name)

            for slot in SLOTS:
                func_name = slot + "_hook"
                if hasattr(instance, func_name):
                    self._plugin_funcs[slot].append(getattr(instance, func_name))

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
    subman_plugins.run("post_product_id_install")
