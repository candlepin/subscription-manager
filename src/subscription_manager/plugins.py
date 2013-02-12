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


class PluginException(Exception):
    """Base exception for rhsm plugins"""
    def _add_message(self, repr):
        if hasattr(self, "msg") and self.msg:
            repr = "\n".join([repr, "Message: %s" % self.msg])
        return repr


class PluginImportException(PluginException):
    """Raised when a SubManPlugin derived class can not be imported"""
    def __init__(self, module_file, module_name, msg=None):
        self.module_file = module_file
        self.module_name = module_name
        self.msg = msg

    def __str__(self):
        repr = "Plugin \"%s\" can't be imported from file %s" % \
            (self.module_name, self.module_file)
        return self._add_message(repr)


class PluginImportApiVersionMissingException(PluginImportException):
    """Raised when a plugin module does not include a 'requires_api_version'"""
    def __str__(self):
        repr = """Plugin module "%s" in %s has no API version.
                'requires_api_version' should be set.""" % \
                (self.module_name, self.module_file)
        return self._add_message(repr)


class PluginImportApiVersionException(PluginImportException):
    """Raised when a plugin module's 'requires_api_version' can not be met"""
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
    """Raised when a PluginConfig fails to load or read a config file"""
    def __init__(self, plugin_name, msg=None):
        self.plugin_name = plugin_name
        self.msg = msg

    def __str__(self):
        repr = "Cannot load configuration for plugin \"%s\"" % (self.plugin_name)
        return self._add_message(repr)


# if code try's to run a hook for a slot_name that doesn't exist
class SlotNameException(Exception):
    """Raised when PluginManager.run() is called with a unknown slot_name"""
    def __init__(self, slot_name):
        self.slot_name = slot_name

    def __str__(self):
        return "slot name %s does not have a conduit to handle it" % self.slot_name


class BaseConduit(object):
    """An API entry point for rhsm plugins

    Conduit()'s are used to provide access to the data a SubManPlugin may need.
    Each 'slot_name' has a BaseConduit() subclass associated with it by PluginManager().
    Whenever a slot is reached, PluginManager will find all the SubManPlugin methods
    that handle the slot, as well as any Conduit() that is mapped to the slot.
    PluginManager.run(slot_name, kwargs) finds the proper Conduit for slot_name,
    then creates an instance, passing in the values of kwargs. Then PluginManager.run
    calls the SubManPlugin hook associated, passing it the Conduit().

    Conduits provide access to subscription-manager configuration, as well
    as a logger object.

    Conduit() subclasses can provide additional methods.

    Args:
        clazz: A SubManPlugin subclass that will use this Conduit()
        conf: A PluginConf for the class passed as clazz
    Attributes:
        slots: A list of slot_name strings this Conduit() will handle
        log: a logger handler
    """
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
    """Conduit for uses with plugins that handle product id functions"""
    slots = ['pre_product_id_install', 'post_product_id_install']

    def __init__(self, clazz, conf, product_list):
        """init for ProductConduit

        Args:
            product_list: A list of ProductCertificate objects
        """
        super(ProductConduit, self).__init__(clazz, conf)
        self.product_list = product_list

    def getProductList(self):
        """returns a list of ProductCertificate objects"""
        return self.product_list


class RegistrationConduit(BaseConduit):
    """Conduit for uses with registration"""
    slots = ['pre_register_consumer', 'post_register_consumer']

    def __init__(self, clazz, conf, name, facts):
        """init for RegistrationConduit

        Args:
            name: ??
            facts: a dictionary of system facts
        """
        super(RegistrationConduit, self).__init__(clazz, conf)
        self.name = name
        self.facts = facts

    def getName(self):
        return self.name

    def getFacts(self):
        return self.facts


class FactsConduit(BaseConduit):
    """Conduit for collecting facts"""
    slots = ['post_facts_collection']

    def __init__(self, clazz, conf, facts):
        """init for FactsConduit

        Args:
            facts: a dictionary of system facts
        """
        super(FactsConduit, self).__init__(clazz, conf)
        self.facts = facts

    def getFacts(self):
        return self.facts


class PluginConfig(object):
    """Represents configuation for each rhsm plugin

    Attributes:
        plugin_conf_path: where plugin config files are found
        plugin_key: a string identifier for plugins, For ex, 'facts.FactsPlugin'
                    Used to find the configuration file.
        conf_file: configuration file associated with plugin represented by plugin_key
        parser: a iniparser.SafeConfigParser for the config file
    """
    @classmethod
    def fromClass(cls, plugin_conf_path, plugin_clazz):
        """construct a PluginConfig from a conf path and a plugin class"""
        plugin_key = ".".join([plugin_clazz.__module__, plugin_clazz.__name__])
        return cls(plugin_conf_path, plugin_key)

    def __init__(self, plugin_conf_path,
                 plugin_key=None):
        """init for PluginConfig

        Args:
            plugin_conf_path: string file path to where plugin config files are found
            plugin_key: a string identifier for plugins
        Raises:
            PluginConfigException: error when finding or loading plugin config
        """
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
        """returns True if the plugin is enabled in it's config"""
        try:
            enabled = self.parser.getboolean('main', 'enabled')
        except Exception, e:
            raise PluginConfigException(self.plugin_key, e)

        if not enabled:
            log.debug("Not loading \"%s\" plugin as it is disabled" % self.plugin_key)
            return False
        return True


class SubscriptionConduit(BaseConduit):
    slots = ['pre_subscribe', 'post_subscribe']

    def __init__(self, clazz, conf, consumer_uuid):
        super(SubscriptionConduit, self).__init__(clazz, conf)
        self.consumer_uuid = consumer_uuid

    def getUuid(self):
        return self.consumer_uuid


#NOTE: need to be super paranoid here about existing of cfg variables
# BasePluginManager with our default config info
class BasePluginManager(object):
    """Finds, load, and provides acccess to subscription-manager plugins"""
    def __init__(self, search_path=None, plugin_conf_path=None):
        """init for BasePluginManager()

        attributes:
            conduits: BaseConduit subclasses that can register slots
            search_path: where to find plugin modules
            plugin_conf_path: where to find plugin config files
            _plugins: map of a plugin_key to a SubManPlugin instance
            _plugins_conf: map of a plugin_key to a PluginConfig instance
            _slot_to_funcs: map of a slotname to a list of plugin methods that handle it
            _slot_to_conduit: map of a slotname to a Conduit() that is passed to the slot
                              associated
        """
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

        # find our list of conduits
        self.conduits = self._get_conduits()

        # populate self._slot_to_conduit
        # and create keys for self._slot_to_func
        self._populate_slots()

        # populate self._plugins with
        self._import_plugins()
        log.debug("Calling PluginManager init")

    def _get_conduits(self):
        """Needs to be implemented in subclass
        Returns: A list of Conduit classes
        """
        return []

    def _populate_slots(self):
        for conduit_class in self.conduits:
            slots = conduit_class.slots
            for slot in slots:
                self._slot_to_conduit[slot] = conduit_class
                self._slot_to_funcs[slot] = []

    def _import_plugins(self):
        """Load all the plugins in the search path

        Raise:
            PluginException: plugin load fails
        """

        if not os.path.isdir(self.search_path):
            log.error("Could not find %s for plugin import" % self.search_path)
            # NOTE: if this is not found, we don't load any plugins
            # so self._plugins/_plugins_funcs are empty
            return

        mask = os.path.join(self.search_path, "*.py")
        for module_file in sorted(glob.glob(mask)):
            try:
                self._load_plugin_module(module_file)
            except PluginException, e:
                log.error(e)

        loaded_plugins = ", ".join(self._plugins)
        log.debug("Loaded plugins: %s" % loaded_plugins)

    def _load_plugin_module(self, module_file):
        """Loads SubManPlugin class from a module file

        Args:
            module_file: file path to a python module containing SubManPlugin based classes
        Raises:
            PluginImportException: module_file could not be imported
            PluginImportApiVersionMissingException: module_file has not api version requirement
            PluginImportApiVersionException: modules api version requirement can not be met
        """
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
            raise PluginImportApiVersionMissingException(module_file, module_name, "Plugin doesn't specify required API version")
        if not api_version_ok(API_VERSION, module.requires_api_version):
            raise PluginImportApiVersionException(module_file, module_name, module_ver=module.requires_api_version, api_ver=API_VERSION)

        self.add_plugins_from_module(module)

    def add_plugins_from_module(self, module):
        """add SubManPlugin based plugins from a module.

        Will also look for a PluginConfig() associated with the
        SubManPlugin classes. Config files should be in self.plugin_conf_path
        and named in the format "moduleName.plugin_class_name.conf"

        Args:
            module: a SubManPlugin derived classes. These
            classes will be found, and added to PluginManager()

        Raises:
            PluginException: multiple plugins with the same name


        """
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
        """Add a SubManPlugin and PluginConfig class to PluginManager

        Args:
            plugin_class: A SubManPlugin child class
            conf: A PluginConfig instance
        Raises:
            PluginException: multiple plugins with the same name
        """
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

    def run(self, slot_name, **kwargs):
        """For slot_name, run the registered hooks with kwargs.

        Args:
            slot_name: a string of the slot_name. Typically of form
                       'post_someplace_something'
            kwargs: kwargs dict of arguments to pass to the SubManPlugin
                    hook methods.These are will be passed to the Conduit
                    instance associated with 'slot_name'
        Returns:
            Nothing.
        Raises:
            SlotNameException: slot_name isn't found
            (Anything else is plugin and conduit specific)
        """
        log.debug("PluginManager.run called for %s with args: %s" % (slot_name, kwargs))
        # slot's called should always exist here, if not
        if slot_name not in self._slot_to_funcs:
            raise SlotNameException(slot_name)

        for func in self._slot_to_funcs[slot_name]:
            plugin_key = ".".join([func.im_class.__module__, func.im_class.__name__])
            log.debug("Running %s in %s" % (func.im_func.func_name, plugin_key))
            # resolve slot_name to conduit
            # FIXME: handle cases where we don't have a conduit for a slot_name
            #   (should be able to handle this since we map those at the same time)
            conduit = self._slot_to_conduit[slot_name]

            #FIXME: handle cases where we can't find the conf
            conf = self._plugins_conf[plugin_key]
            try:
                # create a Conduit
                # FIXME: handle cases where we can't create a Conduit()
                conduit_instance = conduit(func.im_class, conf, **kwargs)
            # TypeError tends to mean we provided the wrong kwargs for this
            # conduit
            except Exception, e:
                raise e

            # If we wanted to allow a plugin or conduit to provide 
            # exception handlers, this is probably where we would go.
            try:
                # invoke the method with the conduit
                func(conduit_instance)
            except Exception, e:
                raise e

    def get_plugin_conf(self, plugin_key):
        """return a PluginConfig object for plugin identifie by plugin_key

        Args:
            plugin_key: string identitifier for plugin class
        Returns:
            A PluginConfig object
        """
        return PluginConfig(self.plugin_conf_path, plugin_key)

    def _get_plugin_conf(self, plugin_clazz):
        """return a PluginConfig object for plugin class plugin_clazz"""
        return PluginConfig.fromClass(self.plugin_conf_path, plugin_clazz)


class PluginManager(BasePluginManager):
    """Finds, load, and provides acccess to subscription-manager plugins
    using subscription-manager default plugin search path and plugin
    conf path."""
    def __init__(self, search_path=None, plugin_conf_path=None):
        """init PluginManager

        Args:
            search_path: if not specified, use the configured 'pluginDir'
            plugin_conf_path: if not specified, use the configured 'pluginConfDir'
        """
        init_search_path = search_path or cfg.get("rhsm", "pluginDir")
        init_plugin_conf_path = plugin_conf_path or cfg.get("rhsm", "pluginConfDir")
        super(PluginManager, self).__init__(search_path=init_search_path,
                                            plugin_conf_path=init_plugin_conf_path)

    def _get_conduits(self):
        """can be overridden by subclasses to add Conduit()'s
        """
        if self.conduits:
            log.debug("already loaded conduits")
            return self.conduits
        # we should be able to collect this from the sub classes of BaseConduit
        return [BaseConduit, ProductConduit, RegistrationConduit,
                FactsConduit, SubscriptionConduit]

# we really only want one PluginManager instance, so share it
plugin_manager = None


def getPluginManager():
    """Create or retrieve a PluginManager()

    Use this instead of creating PluginManager() directly
    so we don't re import plugins

    Returns:
        A PluginManager object. If one has already been created, it
        is returned, otherwise a new one is created.
    """
    global plugin_manager
    log.debug("callling getPluginManager, plugin_manager is: %s" % plugin_manager)
    if plugin_manager:
        return plugin_manager
    plugin_manager = PluginManager()
    return plugin_manager


def parse_version(api_version):
    """parse an API version string into major and minor version strings"""
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
