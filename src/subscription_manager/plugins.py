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

from iniparse import SafeConfigParser
from iniparse.compat import NoSectionError, NoOptionError

from subscription_manager.base_plugin import SubManPlugin

import logging
log = logging.getLogger('rhsm-app.' + __name__)

from rhsm.config import initConfig
cfg = initConfig()

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


# TODO: we should be able to just collect slots class attributes
# from classes derived from BaseConduit, perhaps ala metaclasses...
SLOTS = [
    "pre_product_id_install",
    "post_product_id_install",
    "pre_register_consumer",
    "post_register_consumer",
    "post_facts_collection",
    ]


class PluginException(Exception):
    def _add_message(self, repr):
        if hasattr(self, "msg") and self.msg:
            repr = "\n".join([repr, "Message: %s" % self.msg])
        return repr


class PluginImportException(PluginException):
    def __init__(self, module_file, module_name, msg=None):
        self.module_file = module_file
        self.module_name = module_name
        self.msg = msg

    def __str__(self):
        repr = "Plugin \"%s\" can't be imported from file %s" % \
            (self.module_name, self.module_file)
        return self._add_message(repr)


class PluginImportApiVersionException(PluginImportException):
    def __init__(self, module_file, module_name, module_ver, api_ver, msg=None):
        self.module_file = module_file
        self.module_name = module_name
        self.module_ver = module_ver
        self.api_ver = api_ver
        self.msg = msg

    def __str__(self):
        repr = "Plugin \"%s\" requires API version %s. Supported API is %s" % \
            (self.module_name, self.module_ver, self.api_ver)
        return self._add_message(repr)


class PluginConfigException(PluginException):
    def __init__(self, plugin_name, msg=None):
        self.plugin_name = plugin_name
        self.msg = msg

    def __str__(self):
        repr = "Cannot load configuration for plugin \"%s\"" % (self.plugin_name)
        return self._add_message(repr)


# if code try's to run a hook for a slot_name that doesn't exist
class SlotNameException(Exception):
    def __init__(self, slot_name):
        self.slot_name = slot_name

    def __str__(self):
        return "slot name %s does not have a conduit to handle it" % self.slot_name


class BaseConduit(object):
    slots = []

    def __init__(self, clazz, conf):
        self._conf = conf

        self.log = logging.getLogger("rhsm-app." + clazz.__name__)

    def confString(self, section, option, default=None):
        try:
            self._conf.get(section, option)
        except (NoSectionError, NoOptionError):
            if default is None:
                return None
            return str(default)

    def confBool(self, section, option, default=None):
        try:
            self._conf.getboolean(section, option)
        except (NoSectionError, NoOptionError):
            if default is True:
                return True
            elif default is False:
                return False
            else:
                raise ValueError("Boolean value expected")

    def confInt(self, section, option, default=None):
        try:
            self._conf.getint(section, option)
        except (NoSectionError, NoOptionError):
            try:
                val = int(default)
            except (ValueError, TypeError):
                raise ValueError("Integer value expected")
            return val

    def confFloat(self, section, option, default=None):
        try:
            self._conf.getfloat(section, option)
        except (NoSectionError, NoOptionError):
            try:
                val = float(default)
            except (ValueError, TypeError):
                raise ValueError("Float value expected")
            return val


class ProductConduit(BaseConduit):
    slots = ['pre_product_id_install', 'post_product_id_install']

    def __init__(self, clazz, conf, product_list):
        super(ProductConduit, self).__init__(clazz, conf)
        self.product_list = product_list

    def getProductList(self):
        return self.product_list


class RegistrationConduit(BaseConduit):
    slots = ['pre_register_consumer', 'post_register_consumer']

    def __init__(self, clazz, conf, name, facts):
        super(RegistrationConduit, self).__init__(clazz, conf)
        self.name = name
        self.facts = facts

    def getName(self):
        return self.name

    def getFacts(self):
        return self.facts


class FactsConduit(BaseConduit):
    slots = ['post_facts_collection']

    def __init__(self, clazz, conf, facts):
        super(FactsConduit, self).__init__(clazz, conf)
        self.facts = facts

    def getFacts(self):
        return self.facts


class PluginConfig(object):
    @classmethod
    def fromClass(cls, plugin_conf_path, plugin_class):
        plugin_key = ".".join([plugin_class.__module__, plugin_class.__name__])
        return cls(plugin_conf_path, plugin_key)

    def __init__(self, plugin_conf_path,
                 plugin_key=None):
        self.plugin_conf_path = plugin_conf_path
        self.plugin_key = plugin_key

        self.conf_file = os.path.join(plugin_conf_path, self.plugin_key + ".conf")
        if not os.access(self.conf_file, os.R_OK):
            raise PluginConfigException(self.plugin_key, "Unable to find configuration file")

        self.parser = SafeConfigParser()
        try:
            self.parser.read(self.conf_file)
        except Exception, e:
            raise PluginConfigException(self.plugin_key, e)

    def is_plugin_enabled(self):
        try:
            enabled = self.parser.getboolean('main', 'enabled')
        except Exception, e:
            raise PluginConfigException(self.plugin_key, e)

        if not enabled:
            log.debug("Not loading \"%s\" plugin as it is disabled" % self.plugin_key)
            return False
        return True


class BasePluginManager(object):
    #_plugins = {}
    #_plugins_conf = {}
    def __init__(self, search_path, plugin_conf_path):
        self.search_path = search_path
        self.plugin_conf_path = plugin_conf_path

        # self._plugins is mostly for bookkeeping, it's a dict
        # that maps 'plugin_key':instance
        #     'plugin_key', aka plugin_module.plugin_class
        #      instance is the instaniated plugin class
        # self._plugins_conf maps 'plugin_key' to a plugin Config object
        #      plugin_conf is a Config object created from
        #     the plugin classes config file
        self._plugins = {}
        self._plugins_conf = {}

        self.conduits = []

        # maps a slot_name to a list of methods from a plugin class
        self._slot_to_funcs = {}
        self._slot_to_conduit = {}

    def run(self, slot_name, **kwargs):
        log.debug("PluginManager.run called for %s with args: %s" % (slot_name, kwargs))
        # slot's called should always exist here, if not
        if slot_name not in self._slot_to_funcs:
            raise SlotNameException(slot_name)

        for func in self._slot_to_funcs[slot_name]:
            plugin_key = ".".join([func.im_class.__module__, func.im_class.__name__])
            log.debug("Running %s in %s" % (func.im_func.func_name, plugin_key))
            # resolve slot_name to conduit
            conduit = self._slot_to_conduit[slot_name]

            conf = self._plugins_conf[plugin_key]
            func(conduit(func.im_class, conf, **kwargs))


#NOTE: need to be super paranoid here about existing of cfg variables
# BasePluginManager with our default config info
class PluginManager(BasePluginManager):
    def __init__(self, search_path=None, plugin_conf_path=None):
        init_search_path = search_path or cfg.get("rhsm", "pluginDir")
        init_plugin_conf_path = plugin_conf_path or cfg.get("rhsm", "pluginConfDir")
        super(PluginManager, self).__init__(search_path=init_search_path,
                                            plugin_conf_path=init_plugin_conf_path)

        self.conduits = self._get_conduits()

        # populate self._slot_to_conduit
        # and create keys for self._slot_to_func
        self._populate_slots()

        # populate self._plugins with
        self._import_plugins()

        print "plugins", self._plugins

    def _get_conduits(self):
        if self.conduits:
            log.debug("already loaded conduits")
            return self.conduits
        # we should be able to collect this from the sub classes of BaseConduit
        return [BaseConduit, ProductConduit, RegistrationConduit, FactsConduit]

    def _populate_slots(self):
        # already loaded..
        if self._slot_to_conduit and self._slot_to_funcs:
            log.debug("already loaded slots")
            return
        for conduit_class in self.conduits:
            slots = conduit_class.slots
            for slot in slots:
                self._slot_to_conduit[slot] = conduit_class
                self._slot_to_funcs[slot] = []

    def _import_plugins(self):
        """Load all the plugins in the search path."""
        print self._plugins
        if self._plugins:
            log.debug("already loaded plugins")
            return
        if not os.path.isdir(self.search_path):
            log.error("Could not find %s for plugin import" % self.search_path)
            # NOTE: if this is not found, we don't load any plugins
            # so self._plugins/_plugins_funcs are empty
            return

        mask = os.path.join(self.search_path, "*.py")
        for module_file in sorted(glob.glob(mask)):
            try:
                self._load_plugin(module_file)
            except PluginException, e:
                log.error(e)

        loaded_plugins = ", ".join(self._plugins)
        log.debug("Loaded plugins: %s" % loaded_plugins)

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

        self.add_plugins_from_module(module)

    def add_plugins_from_module(self, module):
        # verify we are a class, and in particular, a subclass
        # of SubManPlugin
        def is_plugin(c):
            return inspect.isclass(c) and c.__module__ == module.__name__ and issubclass(c, SubManPlugin)

        # note we sort the list of plugin classes, since that potentially
        # alters order hooks are mapped to slots
        plugin_classes = sorted(inspect.getmembers(module, is_plugin))
        for name, clazz in sorted(plugin_classes):
            plugin_conf = self._get_plugin_conf(clazz)

            if plugin_conf.is_plugin_enabled():
                self.add_plugin_class(clazz, plugin_conf)

    def add_plugin_class(self, plugin_clazz, conf):
        plugin_key = ".".join([plugin_clazz.__module__, plugin_clazz.__name__])

        instance = plugin_clazz()
        if plugin_key not in self._plugins:
            self._plugins[plugin_key] = instance
            self._plugins_conf[plugin_key] = conf
        else:
            # This shouldn't ever happen
            raise PluginException("Two or more plugins with the name \"%s\" exist " \
                "in the plugin search path" % plugin_clazz.__name__)

        # look for any plugin class methods that match the name
        # format of slot_name_hook
        # only look for func's that match slot's we have in our conduits
        for slot in self._slot_to_funcs.keys():
            func_name = slot + "_hook"
            if hasattr(instance, func_name):
                self._slot_to_funcs[slot].append(getattr(instance, func_name))

    def get_plugin_conf(self, plugin_key):
        return PluginConfig(self.plugin_conf_path, plugin_key)

    def _get_plugin_conf(self, plugin_class):
        return PluginConfig.fromClass(self.plugin_conf_path, plugin_class)


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
