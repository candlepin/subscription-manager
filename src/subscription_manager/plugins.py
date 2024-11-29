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

import glob
import inspect
import logging
import os
import importlib.util
from typing import Callable, Dict, Iterator, List, Optional, SupportsFloat, SupportsInt, Tuple, Type
from typing import TYPE_CHECKING

from iniparse import SafeConfigParser
from iniparse.compat import NoSectionError, NoOptionError

from rhsm.config import get_config_parser
from subscription_manager.base_plugin import SubManPlugin

if TYPE_CHECKING:
    from subscription_manager.content_action_client import ContentPluginActionReport
    from subscription_manager.model import EntitlementSource

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
API_VERSION = "1.1"

DEFAULT_SEARCH_PATH = "/usr/share/rhsm-plugins/"
DEFAULT_CONF_PATH = "/etc/rhsm/pluginconf.d/"

cfg = get_config_parser()

log = logging.getLogger(__name__)


class PluginException(Exception):
    """Base exception for rhsm plugins."""

    def _add_message(self, repr_msg: str) -> str:
        if hasattr(self, "msg") and self.msg:
            repr_msg = "\n".join([repr_msg, "Message: %s" % self.msg])
        return repr_msg


class PluginImportException(PluginException):
    """Raised when a SubManPlugin derived class can not be imported."""

    def __init__(self, module_file: str, module_name: str, msg: Optional[str] = None):
        self.module_file: str = module_file
        self.module_name: str = module_name
        self.msg: Optional[str] = msg

    def __str__(self):
        repr_msg = 'Plugin "%s" can\'t be imported from file %s' % (self.module_name, self.module_file)
        return self._add_message(repr_msg)


class PluginModuleImportException(PluginImportException):
    """Raise when a plugin module can not be imported."""


class PluginModuleImportApiVersionMissingException(PluginImportException):
    """Raised when a plugin module does not include a 'requires_api_version'."""

    def __str__(self):
        repr_msg = """Plugin module "%s" in %s has no API version.
                   'requires_api_version' should be set.""" % (
            self.module_name,
            self.module_file,
        )
        return self._add_message(repr_msg)


class PluginModuleImportApiVersionException(PluginImportException):
    """Raised when a plugin module's 'requires_api_version' can not be met."""

    def __init__(self, module_file, module_name, module_ver, api_ver, msg=None):
        self.module_file = module_file
        self.module_name = module_name
        self.module_ver = module_ver
        self.api_ver = api_ver
        self.msg = msg

    def __str__(self):
        repr_msg = 'Plugin "%s" requires API version %s. Supported API is %s' % (
            self.module_name,
            self.module_ver,
            self.api_ver,
        )
        return self._add_message(repr_msg)


class PluginConfigException(PluginException):
    """Raised when a PluginConfig fails to load or read a config file."""

    def __init__(self, plugin_name, msg=None):
        self.plugin_name = plugin_name
        self.msg = msg

    def __str__(self):
        repr_msg = 'Cannot load configuration for plugin "%s"' % (self.plugin_name)
        return self._add_message(repr_msg)


# if code try's to run a hook for a slot_name that doesn't exist
class SlotNameException(Exception):
    """Raised when PluginManager.run() is called with a unknown slot_name."""

    def __init__(self, slot_name):
        self.slot_name = slot_name

    def __str__(self):
        return "slot name %s does not have a conduit to handle it" % self.slot_name


class BaseConduit:
    """An API entry point for rhsm plugins.

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

    Note the conf instance is expected to be a PluginConfig, and/or
    have a 'parser' attribute that looks like a ConfigParser.SafeConfigParser.

    Args:
        clazz: A SubManPlugin subclass that will use this Conduit()
        conf: A PluginConf for the class passed as clazz
    Attributes:
        slots: A list of slot_name strings this Conduit() will handle
        log: a logger handler
    """

    slots = []

    # clazz is the class object for class instance of the object the hook method maps too
    def __init__(self, clazz: Type[SubManPlugin], conf: Optional["PluginConfig"] = None):
        if conf:
            self._conf = conf
        else:
            self._conf = clazz.conf

        # maybe useful to have a per conduit/per plugin logger space
        self.log = logging.getLogger(clazz.__name__)

    def conf_string(self, section: str, option: str, default: Optional[object] = None) -> Optional[str]:
        """get string from plugin config

        Args:
            section: config section name
            option: config option name
            default: if section or option are not found,
                     return default. None if not
                     specified.
        Returns:
            a string. In the case of error, default
            is returned. If default is not specified,
            None is returned.
        """
        try:
            return self._conf.parser.get(section, option)
        except (NoSectionError, NoOptionError):
            if default is None:
                return None
            return str(default)

    def conf_bool(self, section: str, option: str, default: Optional[bool] = None) -> bool:
        """get boolean value from plugin config

        Args:
            section: config section name
            option: config option name
            default: if section or option are not found,
                     return default.
        Raises:
            ValueError: value requested is not a boolean
        Returns:
            a python boolean. In the case of error, default
            is returned. If default is not specified and
            there is an error, a ValueError is raised.
        """
        try:
            return self._conf.parser.getboolean(section, option)
        except (NoSectionError, NoOptionError):
            if default is True:
                return True
            elif default is False:
                return False
            else:
                raise ValueError("Boolean value expected")

    def conf_int(self, section: str, option: str, default: Optional[SupportsInt] = None) -> int:
        """get integer value from plugin config

        Args:
            section: config section name
            option: config option name
            default: if section or option are not found,
                     return default.
        Raises:
            ValueError: value requested can not be made into an integer
        Returns:
            a python integer. In the case of error, default
            is returned. If default is not specified, a
            ValueError is raised.
        """
        try:
            return self._conf.parser.getint(section, option)
        except (NoSectionError, NoOptionError):
            try:
                val = int(default)
            except (ValueError, TypeError):
                raise ValueError("Integer value expected")
            return val

    def conf_float(self, section: str, option: str, default: Optional[SupportsFloat] = None) -> float:
        """get float value from plugin config

        Args:
            section: config section name
            option: config option name
            default: if section or option are not found,
                     return default.
        Raises:
            ValueError: value requested can not be made into
                        a float
        Returns:
            a python float. In the case of error, default
            is returned. If default is not specified, a
            ValueError is raised.
        """
        try:
            return self._conf.parser.getfloat(section, option)
        except (NoSectionError, NoOptionError):
            try:
                val = float(default)
            except (ValueError, TypeError):
                raise ValueError("Float value expected")
            return val


class RegistrationConduit(BaseConduit):
    """Conduit for uses with registration."""

    slots = ["pre_register_consumer"]

    def __init__(self, clazz: Type[SubManPlugin], name: str, facts: Dict[str, str]):
        """init for RegistrationConduit

        Args:
            name: ??
            facts: a dictionary of system facts
        """
        super(RegistrationConduit, self).__init__(clazz)
        self.name: str = name
        self.facts: Dict[str, str] = facts


class PostRegistrationConduit(BaseConduit):
    """Conduit for use with post registration."""

    slots = ["post_register_consumer"]

    def __init__(self, clazz: Type[SubManPlugin], consumer: dict, facts: Dict[str, str]):
        """init for PostRegistrationConduit

        Args:
            consumer: an object representing the
                    registered consumer
            facts: a dictionary of system facts
        """
        super(PostRegistrationConduit, self).__init__(clazz)
        self.consumer: dict = consumer
        self.facts: Dict[str, str] = facts


class ProductConduit(BaseConduit):
    """Conduit for use with plugins that handle product id functions."""

    slots = ["pre_product_id_install", "post_product_id_install"]

    def __init__(self, clazz: Type[SubManPlugin], product_list: List[dict]):
        """init for ProductConduit

        Args:
            product_list: A list of ProductCertificate objects
        """
        super(ProductConduit, self).__init__(clazz)
        self.product_list: List[dict] = product_list


class ProductUpdateConduit(BaseConduit):
    """Conduit for use with plugins that handle product id update functions."""

    slots = ["pre_product_id_update", "post_product_id_update"]

    def __init__(self, clazz: Type[SubManPlugin], product_list: List[dict]):
        """init for ProductUpdateConduit

        Args:
            product_list: A list of ProductCertificate objects
        """
        super(ProductUpdateConduit, self).__init__(clazz)
        self.product_list: List[dict] = product_list


class FactsConduit(BaseConduit):
    """Conduit for collecting facts."""

    slots = ["post_facts_collection"]

    def __init__(self, clazz: Type[SubManPlugin], facts: List[dict]):
        """init for FactsConduit

        Args:
            facts: a dictionary of system facts
        """
        super(FactsConduit, self).__init__(clazz)
        self.facts: List[dict] = facts


class UpdateContentConduit(BaseConduit):
    """Conduit for updating content."""

    slots = ["update_content"]

    def __init__(
        self, clazz: Type[SubManPlugin], reports: "ContentPluginActionReport", ent_source: "EntitlementSource"
    ):
        """init for UpdateContentConduit.

        Args:
            reports: a list of reports
            ent_source: a EntitlementSource instance
        """
        super(UpdateContentConduit, self).__init__(clazz)
        self.reports: ContentPluginActionReport = reports
        self.ent_source: EntitlementSource = ent_source


class SubscriptionConduit(BaseConduit):
    """Conduit for subscription info."""

    slots = ["pre_subscribe"]

    def __init__(self, clazz: Type[SubManPlugin], consumer_uuid: str, pool_id: str, quantity: int):
        """init for SubscriptionConduit

        Args:
            consumer_uuid: the UUID of the consumer being subscribed
            pool_id: the id of the pool the subscription will come from (None if 'auto' is False)
            quantity: the quantity to consume from the pool (None if 'auto' is False).
        """
        super(SubscriptionConduit, self).__init__(clazz)
        self.consumer_uuid: str = consumer_uuid
        self.pool_id: str = pool_id
        self.quantity: int = quantity


class PostSubscriptionConduit(BaseConduit):
    slots = ["post_subscribe"]

    def __init__(self, clazz: Type[SubManPlugin], consumer_uuid: str, entitlement_data: Dict):
        """init for PostSubscriptionConduit

        Args:
            consumer_uuid: the UUID of the consumer subscribed
            entitlement_data: the data returned by the server
        """
        super(PostSubscriptionConduit, self).__init__(clazz)
        self.consumer_uuid: str = consumer_uuid
        self.entitlement_data: Dict = entitlement_data


class PluginConfig:
    """Represents configuation for each rhsm plugin.

    Attributes:
        plugin_conf_path: where plugin config files are found
        plugin_key: a string identifier for plugins, For ex, 'facts.FactsPlugin'
                    Used to find the configuration file.
    """

    plugin_key: str = None

    def __init__(self, plugin_key: str, plugin_conf_path: str = None):
        """init for PluginConfig.

        Args:
            plugin_key: string id for class
            plugin_conf_path: string file path to where plugin config files are found
        Raises:
            PluginConfigException: error when finding or loading plugin config
        """
        self.plugin_conf_path: str = plugin_conf_path
        self.plugin_key: str = plugin_key
        self.conf_files: List[str] = []

        self.parser = SafeConfigParser()

        # no plugin_conf_path uses the default empty list of conf files
        if self.plugin_conf_path:
            self._get_config_file_path()

        try:
            self.parser.read(self.conf_files)
        except Exception as e:
            raise PluginConfigException(self.plugin_key, e)

    def _get_config_file_path(self):
        conf_file: str = os.path.join(self.plugin_conf_path, self.plugin_key + ".conf")
        if not os.access(conf_file, os.R_OK):
            raise PluginConfigException(self.plugin_key, "Unable to find configuration file")
        # iniparse can handle a list of files, inc an empty list
        # reading an empty list is basically the None constructor
        self.conf_files.append(conf_file)

    def is_plugin_enabled(self) -> bool:
        """returns True if the plugin is enabled in its config."""
        try:
            enabled: bool = self.parser.getboolean("main", "enabled")
        except Exception as e:
            raise PluginConfigException(self.plugin_key, e)

        if not enabled:
            log.debug('Not loading "%s" plugin as it is disabled' % self.plugin_key)
            return False
        return True

    def __str__(self) -> str:
        buf = "plugin_key: %s\n" % (self.plugin_key)
        for conf_file in self.conf_files:
            buf = buf + "config file: %s\n" % conf_file
        # config file entries
        buf = buf + str(self.parser.data)
        return buf


class PluginHookRunner:
    """Encapsulates a Conduit() instance and a bound plugin method.

    PluginManager.runiter() returns an iterable that will yield
    a PluginHookRunner for each plugin hook to be triggered.
    """

    def __init__(self, conduit: BaseConduit, func: Callable):
        self.conduit: BaseConduit = conduit
        self.func: Callable = func

    def run(self) -> None:
        try:
            self.func(self.conduit)
        except Exception as e:
            log.exception(e)
            raise


# NOTE: need to be super paranoid here about existing of cfg variables
# BasePluginManager with our default config info
class BasePluginManager:
    """Finds, load, and provides access to subscription-manager plugins."""

    def __init__(self, search_path: Optional[str] = None, plugin_conf_path: Optional[str] = None):
        """init for BasePluginManager().

        attributes:
            conduits: BaseConduit subclasses that can register slots
            search_path: where to find plugin modules
            plugin_conf_path: where to find plugin config files
            _plugins: map of a plugin_key to a SubManPlugin instance
            _plugin_classes: list of plugin classes found
            _slot_to_funcs: map of a slotname to a list of plugin methods that handle it
            _slot_to_conduit: map of a slotname to a Conduit() that is passed to the slot
                              associated
        """
        self.search_path = search_path
        self.plugin_conf_path = plugin_conf_path

        # list of modules to load plugins from
        self.modules: List = self._get_modules()
        # we track which modules we try to load plugins from
        self._modules: Dict = {}

        # self._plugins is mostly for bookkeeping, it's a dict
        # that maps 'plugin_key':instance
        #     'plugin_key', aka plugin_module.plugin_class
        #      instance is the instantiated plugin class
        self._plugins: Dict[str, object] = {}

        # all found plugin classes, including classes that
        # are disable, and will not be instantiated
        self._plugin_classes: Dict[str, Type[SubManPlugin]] = {}

        self.conduits: List[BaseConduit] = []

        # maps a slot_name to a list of methods from a plugin class
        self._slot_to_funcs: Dict[str, List[Callable]] = {}
        self._slot_to_conduit: Dict[str, BaseConduit] = {}

        # find our list of conduits
        self.conduits = self._get_conduits()

        # populate self._slot_to_conduit
        # and create keys for self._slot_to_func
        self._populate_slots()

        # populate self._plugins with plugins in modules in self.modules
        self._import_plugins()

    def _get_conduits(self) -> List[BaseConduit]:
        """Needs to be implemented in subclass.

        Returns:
             A list of Conduit classes
        """
        return []

    def _get_modules(self) -> List:
        """Needs to be implemented in subclass.

        Returns:
            A list of modules to load plugins classes from
        """
        return []

    def _import_plugins(self) -> None:
        """Needs to be implemented in subclass.

        This loads plugin modules, checks them, and loads plugins
        from them with self.add_plugins_from_module
        """
        # by default, we create PluginConfig's as needed, so no need for
        # plugin_to_config_map to be passed in
        self.add_plugins_from_modules(self.modules)
        log.debug("loaded plugin modules: %s" % self.modules)
        log.debug("loaded plugins: %s" % self._plugins)

    def _populate_slots(self) -> None:
        for conduit_class in self.conduits:
            slots = conduit_class.slots
            for slot in slots:
                self._slot_to_conduit[slot] = conduit_class
                self._slot_to_funcs[slot] = []

    def add_plugins_from_modules(
        self, modules: List[type], plugin_to_config_map: Dict[str, PluginConfig] = None
    ) -> None:
        """Add SubMan plugins from a list of modules

        Args:
            modules: a list of python module objects
            plugin_to_config_map: a dict mapping a plugin_key to a PluginConfig
                                  object. If a plugin finds it's config in here,
                                  that is used instead of creating a new PluginConfig()
                                  (which needs an actual file in plugin_conf_dir)
        Side effects:
            whatever add_plugins_from_module does to self
        """
        for module in modules:
            try:
                self.add_plugins_from_module(module, plugin_to_config_map=plugin_to_config_map)
            except PluginException as e:
                log.exception(e)
                log.error(e)

    def add_plugins_from_module(
        self, module: List[type], plugin_to_config_map: Dict[str, PluginConfig] = None
    ):
        """add SubManPlugin based plugins from a module.

        Will also look for a PluginConfig() associated with the
        SubManPlugin classes. Config files should be in self.plugin_conf_path
        and named in the format "moduleName.plugin_class_name.conf"

        Args:
            module: an import python module object, that contains
                    SubManPlugin subclasses.
            plugin_to_config_map: a dict mapping a plugin_key to a PluginConfig
                                  object.If a plugin finds it's config in here,
                                  that is used instead of creating a new PluginConfig()
        Side Effects:
            self._modules is populated
            whatever add_plugin_class does
        Raises:
            PluginException: multiple plugins with the same name
        """
        # track the modules we try to load plugins from
        # we'll add plugin classes if we find them
        self._modules[module] = []

        # verify we are a class, and in particular, a subclass
        # of SubManPlugin
        def is_plugin(c) -> bool:
            return inspect.isclass(c) and c.__module__ == module.__name__ and issubclass(c, SubManPlugin)

        # note we sort the list of plugin classes, since that potentially
        # alters order hooks are mapped to slots
        plugin_classes: List[Tuple[str, SubManPlugin]] = sorted(inspect.getmembers(module, is_plugin))

        # find all the plugin classes with valid configs first
        # then add them, so we skip the module if a class has a bad config
        found_plugin_classes = []
        for _name, clazz in sorted(plugin_classes):
            # We could have the module conf here, and check in that
            # instead of a per class config. We would not be able to
            # override a disable module per class, but that's probably okay

            found_plugin_classes.append(clazz)

        for plugin_class in found_plugin_classes:
            # NOTE: we currently do not catch plugin init exceptions
            # here, and let them bubble. But we could...? that would
            # let some classes from a module fail
            self.add_plugin_class(plugin_class, plugin_to_config_map=plugin_to_config_map)

    def add_plugin_class(
        self, plugin_clazz: Type[SubManPlugin], plugin_to_config_map: Dict[str, PluginConfig] = None
    ) -> None:
        """Add a SubManPlugin and PluginConfig class to PluginManager.

        Args:
            plugin_clazz: A SubManPlugin child class, with a
                          .conf PluginConfig() class
            plugin_to_config_map: a dict mapping a plugin_key to a PluginConfig
                                  object.If a plugin finds it's config in here,
                                  that is used instead of creating a new PluginConfig()
        Side effects:
            self._plugin_classes is populated with all found plugin classes
            self._modules is populated with plugin classes per plugin module
            self._plugins is populated with valid and enabled plugin instances
        Raises:
            PluginException: multiple plugins with the same name
        """
        # either look up what we were passed, or create a new PluginConfig
        # default is to create a PluginConfig
        plugin_conf = self._get_plugin_config(plugin_clazz, plugin_to_config_map=plugin_to_config_map)

        # associate config with plugin class
        # NOTE: the plugin_class has a PluginConfig instance for it's conf
        plugin_clazz.conf = plugin_conf

        plugin_key = plugin_clazz.conf.plugin_key

        # if plugin is not enabled, it doesnt get added, but
        # we do track it as a plugin_class we looked at
        if not plugin_clazz.conf.is_plugin_enabled():
            self._plugin_classes[plugin_key] = plugin_clazz
            log.debug("%s was disabled via it's config: %s" % (plugin_clazz, plugin_clazz.conf))
            return

        # this is an enabled plugin, so track it's module as well
        # if we havent already
        self._track_plugin_class_to_modules(plugin_clazz)

        # if we fail to init any plugin classes, the exceptions are not
        # caught
        instance = plugin_clazz()

        # track it's instance
        if plugin_key not in self._plugins:
            self._plugins[plugin_key] = instance
        else:
            # This shouldn't ever happen
            raise PluginException(
                'Two or more plugins with the name "%s" exist '
                "in the plugin search path" % plugin_clazz.__name__
            )

        # this is a valid plugin, with config, that instantiates, and is not a  dupe
        self._plugin_classes[plugin_key] = plugin_clazz

        # look for any plugin class methods that match the name
        # format of slot_name_hook
        # only look for func's that match slot's we have in our conduits
        class_is_used = False

        for slot in list(self._slot_to_funcs.keys()):
            func_name = slot + "_hook"
            if instance.all_slots or hasattr(instance, func_name):
                # FIXME: document that all_hooks could result in calls to
                # plugin class for methods that map to slots that it may
                # not have known about. aka, all_hooks is complicated

                # verify the hook is a callable
                if callable(getattr(instance, func_name)):
                    self._slot_to_funcs[slot].append(getattr(instance, func_name))
                    class_is_used = True
                else:
                    # found the attribute, but it is not callable
                    # note we let AttributeErrors bubble up
                    log.debug("%s plugin does not have a callable() method %s" % (plugin_key, func_name))

        # if we don't find any place to use this class, note that on the plugin class
        if class_is_used:
            plugin_clazz.found_slots_for_hooks = True

    def _track_plugin_class_to_modules(self, plugin_clazz: Type[SubManPlugin]) -> None:
        """Keep a map of plugin classes loaded from each plugin module."""
        if plugin_clazz.__module__ not in self._modules:
            self._modules[plugin_clazz.__module__] = []
        self._modules[plugin_clazz.__module__].append(plugin_clazz)

    def run(self, slot_name: str, **kwargs) -> None:
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
        for runner in self.runiter(slot_name, **kwargs):
            runner.run()

    def runiter(self, slot_name: str, **kwargs) -> Iterator[PluginHookRunner]:
        """Return an iterable of PluginHookRunner objects.

        The iterable will return a PluginHookRunner object
        for each plugin hook mapped to slot_name. Multiple plugins
        with hooks for the same slot will result in multiple
        PluginHookRunners in the iterable.

        See run() docs for what to expect from PluginHookRunner.run().
        """
        # slot's called should always exist here, if not
        if slot_name not in self._slot_to_funcs:
            raise SlotNameException(slot_name)

        func: Callable
        for func in self._slot_to_funcs[slot_name]:
            module = inspect.getmodule(func)
            func_module_name: str = getattr(func, "__module__")
            if not func_module_name:
                if module:
                    func_module_name = module.__name__
                else:
                    func_module_name = "unknown_module"
            func_class_name: str = func.__self__.__class__.__name__
            plugin_key: str = ".".join([func_module_name, func_class_name])
            log.debug("Running %s in %s" % (func.__name__, plugin_key))
            # resolve slot_name to conduit
            # FIXME: handle cases where we don't have a conduit for a slot_name
            #   (should be able to handle this since we map those at the same time)
            conduit = self._slot_to_conduit[slot_name]

            try:
                # create a Conduit
                # FIXME: handle cases where we can't create a Conduit()
                conduit_instance = conduit(func.__self__.__class__, **kwargs)
            # TypeError tends to mean we provided the wrong kwargs for this
            # conduit
            # if we get an Exception above, should we exit early, or
            # continue onto other hooks. A conduit could fail for
            # something specific to func.__class__, but unlikely
            except Exception as e:
                log.exception(e)
                raise

            runner = PluginHookRunner(conduit_instance, func)
            yield runner

    def _get_plugin_config(self, plugin_clazz: Type[SubManPlugin], plugin_to_config_map=None) -> PluginConfig:
        """Get a PluginConfig for plugin_class, creating it if need be.

        If we have an entry in plugin_to_config_map for plugin_class,
        return that PluginConfig. Otherwise, we create a PluginConfig()

        Mote that PluginConfig() will expect to find a config file in
        self.plugin_conf_path, and will fail if that is not the case.

        Args:
            plugin_clazz: A SubManPlugin subclass
            plugin_to_config_map: A map of plugin_key to PluginConfig objects
        Returns:
            A PluginConfig() object
        """
        if plugin_to_config_map:
            if plugin_clazz.get_plugin_key() in plugin_to_config_map:
                return plugin_to_config_map[plugin_clazz.get_plugin_key()]

        return PluginConfig(plugin_clazz.get_plugin_key(), self.plugin_conf_path)

    def get_plugins(self) -> Dict[str, Type[SubManPlugin]]:
        """list of plugins."""
        return self._plugin_classes

    def get_slots(self) -> List[str]:
        """list of slots

        Ordered by conduit name, for presentation.
        """
        # I'm sure a clever list comprehension could replace this with one line
        #
        # The default sort of slots is pure lexical, so all the pre's come
        # first, which is weird. So this just sorts the slots by conduit name,
        # then by slot name
        conduit_to_slots = {}
        for slot, conduit in list(self._slot_to_conduit.items()):
            # sigh, no defaultdict on 2.4
            if conduit not in conduit_to_slots:
                conduit_to_slots[conduit] = []
            conduit_to_slots[conduit].append(slot)
        sorted_slots = []
        for conduit in sorted(conduit_to_slots.keys(), key=lambda c: str(c)):
            for slot in sorted(conduit_to_slots[conduit]):
                sorted_slots.append(slot)
        return sorted_slots


class PluginManager(BasePluginManager):
    """Finds, load, and provides acccess to subscription-manager plugins
    using subscription-manager default plugin search path and plugin
    conf path.
    """

    default_search_path = DEFAULT_SEARCH_PATH
    default_conf_path = DEFAULT_CONF_PATH

    def __init__(self, search_path: Optional[str] = None, plugin_conf_path: Optional[str] = None):
        """init PluginManager

        Args:
            search_path: if not specified, use the configured 'pluginDir'
            plugin_conf_path: if not specified, use the configured 'pluginConfDir'
        """
        cfg_search_path = None
        cfg_conf_path = None

        try:
            cfg_search_path = cfg.get("rhsm", "pluginDir")
            cfg_conf_path = cfg.get("rhsm", "pluginConfDir")
        except NoOptionError:
            log.warning("no config options found for plugin paths, using defaults")
            cfg_search_path = None
            cfg_conf_path = None

        init_search_path = search_path or cfg_search_path or self.default_search_path
        init_plugin_conf_path = plugin_conf_path or cfg_conf_path or self.default_conf_path

        super(PluginManager, self).__init__(
            search_path=init_search_path, plugin_conf_path=init_plugin_conf_path
        )

    def _get_conduits(self) -> List[type(BaseConduit)]:
        """get subscription-manager specific plugin conduits."""
        # we should be able to collect this from the sub classes of BaseConduit
        return [
            BaseConduit,
            ProductConduit,
            ProductUpdateConduit,
            RegistrationConduit,
            PostRegistrationConduit,
            FactsConduit,
            SubscriptionConduit,
            UpdateContentConduit,
            PostSubscriptionConduit,
        ]

    def _get_modules(self):
        module_files: List[str] = self._find_plugin_module_files(self.search_path)
        plugin_modules: List = self._load_plugin_module_files(module_files)
        return plugin_modules

    # subman specific module/plugin loading
    def _find_plugin_module_files(self, search_path) -> List[Type[SubManPlugin]]:
        """Load all the plugins in the search path.

        Raise:
            PluginException: plugin load fails
        """
        module_files = []
        if not os.path.isdir(search_path):
            log.error("Could not find %s for plugin import" % search_path)
            # NOTE: if this is not found, we don't load any plugins
            # so self._plugins/_plugins_funcs are empty
            return []
        mask = os.path.join(search_path, "*.py")
        for module_file in sorted(glob.glob(mask)):
            module_files.append(module_file)

        # for consistency
        module_files.sort()
        return module_files

    def _load_plugin_module_files(self, module_files: List[str]) -> List[Type[SubManPlugin]]:
        modules: List[Type[SubManPlugin]] = []
        for module_file in module_files:
            try:
                modules.append(self._load_plugin_module_file(module_file))
            except PluginException as e:
                log.error(e)

        return modules

    def _load_plugin_module_file(self, module_file: str) -> Type[SubManPlugin]:
        """Loads SubManPlugin class from a module file.

        Args:
            module_file: file path to a python module containing SubManPlugin based classes
        Raises:
            PluginImportException: module_file could not be imported
            PluginImportApiVersionMissingException: module_file has not api version requirement
            PluginImportApiVersionException: modules api version requirement can not be met
        """
        dir_path, module_name = os.path.split(module_file)
        module_name = module_name.split(".py")[0]

        try:
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            loaded_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loaded_module)
        # we could catch BaseException too for system exit
        except Exception as e:
            log.exception(e)
            raise PluginModuleImportException(module_file, module_name)

        # FIXME: look up module conf, so we can enable entire plugin modules
        if not hasattr(loaded_module, "requires_api_version"):
            raise PluginModuleImportApiVersionMissingException(
                module_file, module_name, "Plugin doesn't specify required API version"
            )
        if not api_version_ok(API_VERSION, loaded_module.requires_api_version):
            raise PluginModuleImportApiVersionException(
                module_file, module_name, module_ver=loaded_module.requires_api_version, api_ver=API_VERSION
            )

        return loaded_module


def parse_version(api_version: str) -> Tuple[int, int]:
    """parse an API version string into major and minor version strings."""
    maj_ver, min_ver = api_version.split(".")
    return int(maj_ver), int(min_ver)


def api_version_ok(a: str, b: str) -> bool:
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
