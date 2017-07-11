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
import socket
import threading
import dbus.service

from rhsmlib.dbus import constants, exceptions, dbus_utils, base_object, server, util
from subscription_manager import managerlib
from subscription_manager import injection as inj
from subscription_manager.i18n import ugettext as _

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
        in_signature='',
        out_signature='s')
    @util.dbus_handle_exceptions
    def Start(self, sender=None):
        with self.lock:
            if self.server:
                return self.server.address

            log.debug('Attempting to create new domain socket server')
            self.server = server.DomainSocketServer(
                object_classes=[DomainSocketRegisterDBusObject],
            )
            address = self.server.run()
            log.debug('DomainSocketServer created and listening on "%s"', address)
            return address

    @util.dbus_service_method(
        constants.REGISTER_INTERFACE,
        in_signature='',
        out_signature='b')
    @util.dbus_handle_exceptions
    def Stop(self, sender=None):
        with self.lock:
            if self.server:
                self.server.shutdown()
                self.server = None
                log.debug("Stopped DomainSocketServer")
                return True
            else:
                raise exceptions.Failed("No domain socket server is running")


class DomainSocketRegisterDBusObject(base_object.BaseObject):
    interface_name = constants.PRIVATE_REGISTER_INTERFACE
    default_dbus_path = constants.PRIVATE_REGISTER_DBUS_PATH

    def __init__(self, conn=None, object_path=None, bus_name=None):
        # On our DomainSocket DBus server since a private connection is not a "bus", we have to treat
        # it slightly differently. In particular there are no names, no discovery and so on.
        super(DomainSocketRegisterDBusObject, self).__init__(
            conn=conn,
            object_path=object_path,
            bus_name=bus_name
        )
        self.installed_mgr = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.facts = inj.require(inj.FACTS)

    @dbus.service.method(
        dbus_interface=constants.PRIVATE_REGISTER_INTERFACE,
        in_signature='sssa{sv}',
        out_signature='a{sv}'
    )
    def Register(self, org, username, password, options):
        """
        This method registers the system using basic auth
        (username and password for a given org).
        For any option that is required but not included the default will be
        used.

        Options is a dict of strings that modify the outcome of this method.

        Note this method is registration ONLY.  Auto-attach is a separate process.
        """
        options = dbus_utils.dbus_to_python(options)
        options['username'] = dbus_utils.dbus_to_python(username)
        options['password'] = dbus_utils.dbus_to_python(password)
        org = dbus_utils.dbus_to_python(org)

        resp = self._register(org, options)
        consumer = json.loads(resp['content'], object_hook=dbus_utils._decode_dict)
        managerlib.persist_consumer_cert(consumer)
        resp['content'] = json.dumps(self._remove_key(consumer))

        return dbus_utils.dict_to_variant_dict(resp)

    @dbus.service.method(dbus_interface=constants.PRIVATE_REGISTER_INTERFACE,
        in_signature='sasa{sv}',
        out_signature='a{sv}')
    def RegisterWithActivationKeys(self, org, activation_keys, options):
        """
        Note this method is registration ONLY.  Auto-attach is a separate process.
        """
        options = dbus_utils.dbus_to_python(options)
        options['activation_keys'] = dbus_utils.dbus_to_python(activation_keys)
        org = dbus_utils.dbus_to_python(org)

        resp = self._register(org, options)
        consumer = json.loads(resp['content'], object_hook=dbus_utils._decode_dict)
        managerlib.persist_consumer_cert(consumer)
        resp['content'] = json.dumps(self._remove_key(consumer))

        return dbus_utils.dict_to_variant_dict(resp)

    def _register(self, org, options):
        options = dbus_utils.dbus_to_python(options)
        options = self.validate_options(options)

        environment = options.get('environment')
        facts_dict = self.facts.get_facts()
        consumer_name = options['name']

        self.plugin_manager.run("pre_register_consumer", name=consumer_name, facts=facts_dict)

        cp = self.build_uep(options)
        resp = cp.registerConsumer(
            name=consumer_name,
            facts=facts_dict,
            owner=org,
            environment=environment,
            keys=options.get('activation_keys', None),
            installed_products=self.installed_mgr.format_for_server(),
            content_tags=self.installed_mgr.tags
        )
        self.installed_mgr.write_cache()
        self.plugin_manager.run("post_register_consumer", consumer=resp['content'], facts=facts_dict)
        return resp

    def _remove_key(self, consumer):
        if 'idCert' in consumer:
            del consumer['idCert']

        return consumer

    def validate_options(self, options):
        # TODO: Rewrite the error messages to be more dbus specific
        error_msg = None
        if self.is_registered() and not options.get('force', False):
            error_msg = _("This system is already registered. Add force to options to override.")
        elif options.get('name') == '':
            error_msg = _("Error: system name can not be empty.")
        elif 'consumerid' in options and 'force' in options:
            error_msg = _("Error: Can not force registration while attempting to recover registration with consumerid. Please use --force without --consumerid to re-register or use the clean command and try again without --force.")

        # If 'activation_keys' already exists in the dictionary, leave it.  Otherwise, set to None.
        if options.get('activation_keys', None):
            # 746259: Don't allow the user to pass in an empty string as an activation key
            if '' == options['activation_keys']:
                error_msg = _("Error: Must specify an activation key")
            elif 'username' in options:
                error_msg = _("Error: Activation keys do not require user credentials.")
            elif 'consumerid' in options:
                error_msg = _("Error: Activation keys can not be used with previously registered IDs.")
            elif 'environment' in options:
                error_msg = _("Error: Activation keys do not allow environments to be specified.")
        else:
            if 'username' not in options or 'password' not in options:
                error_msg = _("Error: Missing username or password.")

        if error_msg:
            raise exceptions.Failed(msg=error_msg)

        if 'name' not in options:
            options['name'] = socket.gethostname()

        return options
