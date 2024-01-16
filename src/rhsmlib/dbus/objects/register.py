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
import json
import logging
import threading
import dbus
import dbus.service
import subscription_manager.injection as inj

from rhsmlib.dbus import constants, exceptions, dbus_utils, base_object, server, util
from rhsmlib.services.register import RegisterService
from rhsmlib.client_info import DBusSender
from rhsmlib.services.unregister import UnregisterService
from rhsmlib.services.attach import AttachService
from rhsmlib.services.entitlement import EntitlementService

from subscription_manager.i18n import Locale
from subscription_manager.i18n import ugettext as _
from subscription_manager.entcertlib import EntCertActionInvoker

log = logging.getLogger(__name__)


class RegisterDBusObject(base_object.BaseObject):
    default_dbus_path = constants.REGISTER_DBUS_PATH
    interface_name = constants.REGISTER_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(RegisterDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.started_event = threading.Event()
        self.stopped_event = threading.Event()
        self.server = None
        self.lock = threading.Lock()

    @util.dbus_service_method(
        constants.REGISTER_INTERFACE,
        in_signature='s',
        out_signature='s')
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def Start(self, locale, sender=None):
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        with self.lock:
            # When some other application already started domain socket listener, then
            # write log message and return existing address
            if self.server is not None:
                log.debug(f"Domain socket listener already running, started by: {self.server.sender}")
                # Add sender to the list of senders using server
                log.debug(f"Adding another sender {sender} to the set of senders")
                self.server.add_sender(sender)
                return self.server.address

            log.debug('Attempting to create new domain socket server')
            cmd_line = DBusSender.get_cmd_line(sender)
            self.server = server.DomainSocketServer(
                object_classes=[DomainSocketRegisterDBusObject],
                sender=sender,
                cmd_line=cmd_line
            )
            address = self.server.run()
            log.debug('DomainSocketServer for sender %s created and listening on "%s"' % (sender, address))
            return address

    @util.dbus_service_method(
        constants.REGISTER_INTERFACE,
        in_signature='s',
        out_signature='b')
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def Stop(self, locale, sender=None):
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)
        with self.lock:
            if self.server is None:
                raise exceptions.Failed("No domain socket server is running")

            # Remove current sender and check if other senders are still running.
            # If there is at least one sender using this server still running, then
            # only return False
            self.server.remove_sender(sender)
            if self.server.are_other_senders_still_running() is True:
                log.debug("Not stopping domain socket server, because some senders still uses it.")
                return False

            self.server.shutdown()
            self.server = None
            log.debug("Domain socket server stopped.")
            return True


class OrgNotSpecifiedException(dbus.DBusException):
    """
    This exception is intended for signaling that user is member of more
    organizations and no organization was specified
    """
    _dbus_error_name = "%s.Error" % constants.REGISTER_INTERFACE
    include_traceback = False
    severity = "info"

    def __init__(self, username):
        self.username = username

    def __str__(self):
        return _("User %s is member of more organizations, but no organization was selected") % self.username


class NoOrganizationException(dbus.DBusException):
    """
    This exception is intended for signaling that user is not member of any
    organization and such user cannot register to candlepin server.
    """
    _dbus_error_name = "%s.Error" % constants.REGISTER_INTERFACE
    include_traceback = False

    def __init__(self, username):
        self.username = username

    def __str__(self):
        return _("User %s is not member of any organization") % self.username


class DomainSocketRegisterDBusObject(base_object.BaseObject):
    interface_name = constants.PRIVATE_REGISTER_INTERFACE
    default_dbus_path = constants.PRIVATE_REGISTER_DBUS_PATH

    def __init__(self, conn=None, object_path=None, bus_name=None, sender=None, cmd_line=None):
        # On our DomainSocket DBus server since a private connection is not a "bus", we have to treat
        # it slightly differently. In particular there are no names, no discovery and so on.
        super(DomainSocketRegisterDBusObject, self).__init__(
            conn=conn,
            object_path=object_path,
            bus_name=bus_name
        )
        self.sender = sender
        self.cmd_line = cmd_line

    @dbus.service.method(
        dbus_interface=constants.PRIVATE_REGISTER_INTERFACE,
        in_signature='ssa{sv}s',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def GetOrgs(self, username, password, connection_options, locale):
        """
        This method tries to return list of organization user belongs to. This method also uses
        basic authentication method (using username and password).

        :param username: string with username used for connection to candlepin server
        :param password: string with password
        :param connection_options: dictionary with connection options
        :param locale: string with locale
        :return: string with json returned by candlepin server
        """
        connection_options = dbus_utils.dbus_to_python(connection_options, expected_type=dict)
        connection_options['username'] = dbus_utils.dbus_to_python(username, expected_type=str)
        connection_options['password'] = dbus_utils.dbus_to_python(password, expected_type=str)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        with DBusSender() as dbus_sender:
            dbus_sender.set_cmd_line(sender=self.sender, cmd_line=self.cmd_line)
            Locale.set(locale)
            cp = self.build_uep(connection_options, basic_auth_method=True)
            owners = cp.getOwnerList(connection_options['username'])
            dbus_sender.reset_cmd_line()

        return json.dumps(owners)

    @util.dbus_service_signal(
        constants.PRIVATE_REGISTER_INTERFACE,
        signature='s'
    )
    @util.dbus_handle_exceptions
    def UserMemberOfOrgs(self, orgs):
        """
        Signal triggered, when user tries to register, no organization is specified, but
        user is member of more than one organization and it will be necessary to select
        one organization in client application consuming this D-Bus API
        :param orgs: string with json.dump of org dictionary (key: org_id, value: org_name)
        :return: None
        """
        log.debug("D-Bus signal UserMemberOfOrgs emitted on the interface %s with arg: %s" %
                  (constants.PRIVATE_REGISTER_INTERFACE, orgs))
        return None

    def _no_owner_cb(self, username):
        """
        Callback method that is triggered, when given user is not member of any organization.
        In this case exception is raised.
        :return: None
        """
        raise NoOrganizationException(username=username)

    def _get_owner_cb(self, owners):
        """
        When there is necessary to select one organization by user, then signal is triggered.
        :param owners: The list of owner objects
        :return: None
        """
        # We use string of json.dumped dictionary, because D-Bus API does not work
        # properly with dictionaries
        orgs = json.dumps(owners)

        # NOTE: use only position argument. Do not change it to keyed argument, because
        # D-Bus wrapper does NOT work with keyed argument
        self.UserMemberOfOrgs(orgs)

        # We return None here, because we cannot know what will be selected by user
        return None

    @staticmethod
    def _enable_content(cp, consumer: dict) -> None:
        """
        Try to enable content. Try to do auto-attach in non-SCA mode or try to do refresh SCA mode.
        :param cp: Object representing connection to candlepin server
        :param consumer: Dictionary representing consumer
        :return: None
        """
        content_access_mode = consumer['owner']['contentAccessMode']
        enabled_content = None

        if content_access_mode == 'entitlement':
            log.debug('Auto-attaching due to enable_content option')
            attach_service = AttachService(cp)
            enabled_content = attach_service.attach_auto()
            if len(enabled_content) > 0:
                log.debug("Updating entitlement certificates")
                # FIXME: The enabled_content contains all data necessary for generating entitlement
                # certificate and private key. Thus we could save few REST API calls, when the data was used.
                EntCertActionInvoker().update()
            else:
                log.debug("Skipping updating entitlement certificates, because no content was enabled")
        elif content_access_mode == 'org_environment':
            log.debug('Refreshing due to enabled_content option and simple content access mode')
            entitlement_service = EntitlementService(cp)
            # TODO: try get anything useful from refresh result. It is not possible atm.
            entitlement_service.refresh(remove_cache=False, force=False)
        else:
            log.error(f"Unable to enable content due to unsupported content access mode: "
                      f"{content_access_mode}")

        # When it was possible to enable content, then extend consumer
        # with information about enabled content
        if enabled_content is not None:
            consumer['enabledContent'] = enabled_content

    @staticmethod
    def _remove_enable_content_option(options: dict) -> bool:
        """
        Try to remove enable_content option from options used in Register() and
        RegisterWithActivationKeys() methods
        :param options: dictionary with options
        :return: Value of enable_options
        """
        if 'enable_content' in options:
            log.debug(
                f"Value and type of enable_content: '{options['enable_content']}' "
                f"({type(options['enable_content'])})"
            )
            enable_content = bool(options.pop('enable_content'))
            log.debug(f"Value of converted enable_content: {enable_content}")
        else:
            enable_content = False
        return enable_content

    def _unregister(self, connection_options: dict) -> None:
        """
        Unregisters a system that is currently registered and
        cleans the cp_provider to handle authorization after un-registering.
        :param connection_options: dictionary with connection options
        :return: None
        """
        self.ensure_registered()
        log.info("This system is already registered, attempting to un-register...")

        cp_provider = inj.require(inj.CP_PROVIDER)

        cp = self.build_uep(connection_options)
        UnregisterService(cp).unregister()

        # The CPProvider object must be cleaned and the cp object must
        # be re-initialized to handle authorization after un-registration.
        cp_provider.clean()

    @dbus.service.method(
        dbus_interface=constants.PRIVATE_REGISTER_INTERFACE,
        in_signature='sssa{sv}a{sv}s',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def Register(self, org, username, password, options, connection_options, locale):
        """
        This method registers the system using basic auth
        (username and password for a given org).
        For any option that is required but not included the default will be
        used.

        Options is a dict of strings that modify the outcome of this method.

        Note this method is registration ONLY.  Auto-attach is a separate process.
        """

        org = dbus_utils.dbus_to_python(org, expected_type=str)
        connection_options = dbus_utils.dbus_to_python(connection_options, expected_type=dict)
        connection_options['username'] = dbus_utils.dbus_to_python(username, expected_type=str)
        connection_options['password'] = dbus_utils.dbus_to_python(password, expected_type=str)
        options = dbus_utils.dbus_to_python(options, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        force_registration: bool = options.get("force", False)
        system_is_registered: bool = self.is_registered()
        if system_is_registered and not force_registration:
            raise dbus.DBusException("This system is already registered.")

        with DBusSender() as dbus_sender:
            dbus_sender.set_cmd_line(sender=self.sender, cmd_line=self.cmd_line)
            Locale.set(locale)

            # If the system is registered and the 'force' option is specified,
            # Unregister the system and register the system again.
            if system_is_registered and force_registration:
                self._unregister(connection_options)
            cp = self.build_uep(connection_options)

            register_service = RegisterService(cp)

            # Try to get organization from the list available organizations, when the list contains
            # only one item, then register_service.determine_owner_key will return this organization
            if not org:
                org = register_service.determine_owner_key(
                    username=connection_options['username'],
                    get_owner_cb=self._get_owner_cb,
                    no_owner_cb=self._no_owner_cb
                )

            # When there is more organizations, then signal was triggered in callback method
            # _get_owner_cb, but some exception has to be raised here to not try registration process
            if not org:
                raise OrgNotSpecifiedException(username=connection_options['username'])

            # Remove 'enable_content' option, because it will not be proceed in register service
            enable_content = self._remove_enable_content_option(options)

            consumer = register_service.register(org, **options)

            # When consumer is created, then we can try to enabled content, when it was
            # requested in options.
            if enable_content is True:
                self._enable_content(cp, consumer)

            dbus_sender.reset_cmd_line()

        return json.dumps(consumer)

    @dbus.service.method(
        dbus_interface=constants.PRIVATE_REGISTER_INTERFACE,
        in_signature='sasa{sv}a{sv}s',
        out_signature='s')
    @util.dbus_handle_exceptions
    def RegisterWithActivationKeys(self, org, activation_keys, options, connection_options, locale):
        """
        Note this method is registration ONLY.  Auto-attach is a separate process.
        """
        connection_options = dbus_utils.dbus_to_python(connection_options, expected_type=dict)
        options = dbus_utils.dbus_to_python(options, expected_type=dict)
        options['activation_keys'] = dbus_utils.dbus_to_python(activation_keys, expected_type=list)
        org = dbus_utils.dbus_to_python(org, expected_type=str)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        force_registration: bool = options.get("force", False)
        system_is_registered: bool = self.is_registered()
        if system_is_registered and not force_registration:
            raise dbus.DBusException("This system is already registered.")

        with DBusSender() as dbus_sender:
            dbus_sender.set_cmd_line(sender=self.sender, cmd_line=self.cmd_line)
            Locale.set(locale)

            # If the system is registered and the 'force' option is specified,
            # Unregister the system and register the system again.
            if system_is_registered and force_registration:
                self._unregister(connection_options)
            cp = self.build_uep(connection_options)

            register_service = RegisterService(cp)
            consumer = register_service.register(org, **options)

            log.debug("System registered, updating entitlements if needed")
            entcertlib = EntCertActionInvoker()
            entcertlib.update()
            dbus_sender.reset_cmd_line()

        return json.dumps(consumer)
