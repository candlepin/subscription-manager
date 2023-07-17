# Copyright (c) 2016 Red Hat, Inc.
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
from typing import TYPE_CHECKING, Union

import dbus
import logging
from iniparse import ini

import rhsm
import rhsm.logutil

from subscription_manager.i18n import Locale

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.config import Config
from rhsmlib.file_monitor import CONFIG_WATCHER
from rhsmlib.dbus.server import Server

from dbus import DBusException

if TYPE_CHECKING:
    from rhsm.config import RhsmConfigParser

log = logging.getLogger(__name__)


class ConfigDBusImplementation(base_object.BaseImplementation):
    def __init__(self, parser: "RhsmConfigParser"):
        self.config = Config(parser)

    def set(self, section_and_key: str, value: str) -> None:
        """Set one value.

        :param section_and_key: Specific configuration in 'section.key' format.
        :param value: New value.
        :raises DBusException: Only section has been specified.
        """
        section, _, key = section_and_key.partition(".")
        if not key:
            raise DBusException("Setting an entire section is not supported. Use 'section.property' format.")

        self.config[section][key] = value

        logging_changed: bool = section == "logging"

        # Temporarily disable directory watcher, because 'self.config.persist()' writes down the file.
        # It would trigger file system monitor callback and saved values would be read again. It may cause
        # race conditions, when 'Set()' is called multiple times.
        Server.temporary_disable_dir_watchers({CONFIG_WATCHER})

        self.config.persist()

        if logging_changed:
            parser = rhsm.config.get_config_parser()
            self.config = Config(parser)

            # Iniparse is not thread-safe and race conditions can cause unexpected exceptions.
            # This is very rare. For this reason we try to catch all exceptions, because it is not critical.
            # See BZs 2076948, 2093883
            try:
                rhsm.logutil.init_logger(parser)
            except Exception as exc:
                log.warning(f"Re-initialization of logger failed: {exc}")

        # Enable watchers after the logger has been updated
        Server.enable_dir_watchers({CONFIG_WATCHER})

    def set_all(self, configuration: dict) -> None:
        """Set multiple values.

        :param configuration: Mapping of 'section.key' formats to their 'value's.
        """
        log.debug(f"Setting new configuration values: {configuration}")

        logging_changed: bool = False
        for section_and_key, value in configuration.items():
            section, _, key = section_and_key.partition(".")
            if not key:
                raise DBusException(
                    "Setting an entire section is not supported. Use 'section.property' format."
                )

            self.config[section][key] = value
            if section == "logging":
                logging_changed = True

        # Temporarily disable directory watcher, because 'self.config.persist()' writes down the file.
        # It would trigger file system monitor callback and saved values would be read again. It may cause
        # race conditions, when 'Set()' is called multiple times.
        Server.temporary_disable_dir_watchers({CONFIG_WATCHER})

        self.config.persist()

        if logging_changed:
            parser = rhsm.config.get_config_parser()
            self.config = Config(parser)

            # Iniparse is not thread-safe and race conditions can cause unexpected exceptions.
            # This is very rare. For this reason we try to catch all exceptions, because it is not critical.
            # See BZs 2076948, 2093883
            try:
                rhsm.logutil.init_logger(parser)
            except Exception as exc:
                log.warning(f"Re-initialization of logger failed: {exc}")

        # Enable watchers after the logger has been updated
        Server.enable_dir_watchers({CONFIG_WATCHER})

    def get_all(self) -> dict:
        """Get all values."""
        return dict(self.config)

    def get(self, section_maybe_key: str) -> Union[str, dict]:
        """Get configuration section or specific value.

        :param: Section or specific configuration in 'section.key' format.
        """
        section, _, key = section_maybe_key.partition(".")
        if key:
            return self.config[section][key]
        else:
            return dict(self.config[section])

    def reload(self):
        """
        When some change of rhsm.conf is detected (via i-notify or periodical polling),
        it is reloaded so new values can be used.
        """
        parser = rhsm.config.get_config_parser()

        # We are going to read configuration file again, but we have to clean all data in parser object
        # this way, because iniparse module doesn't provide better method to do that.
        parser.data = ini.INIConfig(None, optionxformsource=parser)

        # We have to read parser again to get fresh data from the file
        files_read = parser.read()

        if len(files_read) > 0:
            log.debug("files read: %s" % str(files_read))
            self.config = Config(parser)
            rhsm.logutil.init_logger(parser)
            log.debug("Configuration file: %s reloaded: %s" % (parser.config_file, str(self.config)))
        else:
            log.warning("Unable to read configuration file: %s" % parser.config_file)


class ConfigDBusObject(base_object.BaseObject):
    default_dbus_path = constants.CONFIG_DBUS_PATH
    interface_name = constants.CONFIG_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None, parser: "RhsmConfigParser" = None):
        super().__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.impl = ConfigDBusImplementation(parser)

    @util.dbus_service_signal(
        constants.CONFIG_INTERFACE,
        signature="",
    )
    @util.dbus_handle_exceptions
    def ConfigChanged(self):
        """
        Signal fired, when config is created/deleted/changed
        :return: None
        """
        log.debug("D-Bus signal %s emitted" % constants.CONFIG_INTERFACE)
        return None

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature="svs",
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def Set(self, property_name, new_value, locale, sender=None):
        """
        Method used for setting only one value. When more than one value is going to be set, then it is
        strongly recommended to use method SetAll(), because configuration is saved to the configuration
        file at the end of method Set()
        :param property_name: string with property e.g. server.hostname
        :param new_value: string with new value
        :param locale: string with locale
        :param sender: not used
        :return: None
        """
        property_name = dbus_utils.dbus_to_python(property_name, expected_type=str)
        new_value = dbus_utils.dbus_to_python(new_value, expected_type=str)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        self.impl.set(property_name, new_value)

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature="a{sv}s",
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def SetAll(self, configuration, locale, sender=None):
        """
        Method for setting multiple configuration options. Of course all of them could be set.
        :param configuration: d-bus dictionary with configuration. Keys have to include section. e.g.
                              server.hostname. Configuration file is saved to the file at the end of method.
        :param locale: string with locale
        :param sender: not used
        :return: None
        """
        configuration = dbus_utils.dbus_to_python(configuration, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        self.impl.set_all(configuration)

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature="s",
        out_signature="a{sv}",
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def GetAll(self, locale, sender=None):
        """
        Method for getting whole configuration
        :param locale: string with locale
        :param sender: not used
        :return: D-bus dictionary with configuration
        """
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        d = dbus.Dictionary({}, signature="sv")
        for k, v in self.impl.get_all().items():
            d[k] = dbus.Dictionary({}, signature="ss")
            for kk, vv in v.items():
                d[k][kk] = vv

        return d

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature="ss",
        out_signature="v",
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def Get(self, property_name, locale, sender=None):
        """
        D-Bus method for getting one configuration property or one section
        :param property_name: string with name of property e.g. server.hostname or section e.g. server
        :param locale: string with locale
        :param sender: not used
        :return: string with value of property or dictionary with dictionary of one section
        """
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        result: Union[str, dict] = self.impl.get(property_name)

        if type(result) is dict:
            result = dbus.Dictionary(result, signature="sv")

        return result
