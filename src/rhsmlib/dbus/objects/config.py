from __future__ import print_function, division, absolute_import

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
import dbus
import logging
import six
from iniparse import ini

import rhsm
import rhsm.config
import rhsm.logutil

from subscription_manager.i18n import Locale

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.config import Config
from rhsmlib.file_monitor import CONFIG_WATCHER
from rhsmlib.dbus.server import Server

from dbus import DBusException
log = logging.getLogger(__name__)


class ConfigDBusObject(base_object.BaseObject):
    default_dbus_path = constants.CONFIG_DBUS_PATH
    interface_name = constants.CONFIG_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None, parser=None):
        self.config = Config(parser)
        super(ConfigDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_signal(
        constants.CONFIG_INTERFACE,
        signature=''
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
        in_signature='svs')
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def Set(self, property_name, new_value, locale, sender=None):
        """
        Method used for setting only one value. When more than one value is going to be set, then it is
        strongly recomended to use method SetAll(), because configuration is saved to the configuration
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

        section, _dot, property_name = property_name.partition('.')

        if not property_name:
            raise DBusException("Setting an entire section is not supported.  Use 'section.property' format.")

        self.config[section][property_name] = new_value

        if section == 'logging':
            logging_changed = True
        else:
            logging_changed = False

        # Try to temporary disable dir watcher, because 'self.config.persist()' writes configuration
        # file and it would trigger file system monitor callback function and saved values would be
        # read again. It can cause race conditions, when Set() is called multiple times
        temporary_disable_dir_watcher()

        # Write new config value to configuration file
        self.config.persist()

        # When anything in logging section was just chnaged, then we have to re-initialize logger
        if logging_changed is True:
            parser = rhsm.config.get_config_parser()
            self.config = Config(parser)
            rhsm.logutil.init_logger(parser)

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature='a{sv}s')
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

        log.debug('Setting new configuration values: %s' % str(configuration))

        logging_changed = False

        for property_name, new_value in configuration.items():
            section_name, _dot, property_name = property_name.partition('.')

            if not property_name:
                raise DBusException("Setting an entire section is not supported.  Use 'section.property' format.")

            self.config[section_name][property_name] = new_value

            if section_name == 'logging':
                logging_changed = True

        # Try to temporary disable dir watcher, because 'self.config.persist()' writes configuration
        # file and it would trigger file system monitor callback function and saved values would be
        # read again. It can cause race conditions, when SetAll() is called multiple times
        temporary_disable_dir_watcher()

        # Write new config value to configuration file
        self.config.persist()

        # When anything in logging section was just chnaged, then we have to re-initialize logger
        if logging_changed is True:
            parser = rhsm.config.get_config_parser()
            self.config = Config(parser)
            rhsm.logutil.init_logger(parser)

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature='s',
        out_signature='a{sv}')
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

        d = dbus.Dictionary({}, signature='sv')
        for k, v in six.iteritems(self.config):
            d[k] = dbus.Dictionary({}, signature='ss')
            for kk, vv in six.iteritems(v):
                d[k][kk] = vv

        return d

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature='ss',
        out_signature='v')
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

        section, _dot, property_name = property_name.partition('.')

        if property_name:
            return self.config[section][property_name]
        else:
            return dbus.Dictionary(self.config[section], signature='sv')

    def reload(self):
        """
        This callback method is called, when i-notify or periodical directory polling detects
        any change of rhsm.conf file. Thus configuration file is reloaded and new values are used.
        """
        parser = rhsm.config.get_config_parser()

        # We are going to read configuration file again, but we have to clean all data in parser object
        # this way, because iniparse module doesn't provide better method to do that.
        parser.data = ini.INIConfig(None, optionxformsource=parser)

        # We have to read parser again to get fresh data from the file
        files_read = parser.read()

        if len(files_read) > 0:
            log.debug('files read: %s' % str(files_read))
            self.config = Config(parser)
            rhsm.logutil.init_logger(parser)
            log.debug("Configuration file: %s reloaded: %s" % (parser.config_file, str(self.config)))
        else:
            log.warning("Unable to read configuration file: %s" % parser.config_file)


def temporary_disable_dir_watcher():
    """
    This method temporary disables file system directory watcher for rhsm.conf
    """

    if Server.INSTANCE is not None:
        server = Server.INSTANCE
        dir_watcher = server.filesystem_watcher.dir_watches[CONFIG_WATCHER]
        dir_watcher.temporary_disable()
