from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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
import logging
import socket

from rhsmlib.services import exceptions

from subscription_manager import injection as inj
from subscription_manager import managerlib
from subscription_manager import syspurposelib
from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)


class RegisterService(object):
    def __init__(self, cp):
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.installed_mgr = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)
        self.facts = inj.require(inj.FACTS)
        self.identity = inj.require(inj.IDENTITY)
        self.cp = cp

    def register(self, org, activation_keys=None, environment=None, force=None, name=None, consumerid=None,
            type=None, role=None, addons=None, service_level=None, usage=None, **kwargs):
        # We accept a kwargs argument so that the DBus object can pass the options dictionary it
        # receives transparently to the service via dictionary unpacking.  This strategy allows the
        # DBus object to be more independent of the service implementation.

        # If there are any values in kwargs that don't map to keyword arguments defined in the message
        # signature we want to consider that an error.
        if kwargs:
            raise exceptions.ValidationError(_("Unknown arguments: %s") % kwargs.keys())

        syspurpose = syspurposelib.read_syspurpose()
        role = role or syspurpose.get('role', '')
        addons = addons or syspurpose.get('addons', [])
        usage = usage or syspurpose.get('usage', '')
        service_level = service_level or syspurpose.get('service_level_agreement', '')

        type = type or "system"

        options = {
            'activation_keys': activation_keys,
            'environment': environment,
            'force': force,
            'name': name,
            'consumerid': consumerid,
            'type': type
        }
        self.validate_options(options)

        environment = options['environment']
        facts_dict = self.facts.get_facts()

        # Default to the hostname if no name is given
        consumer_name = options['name'] or socket.gethostname()

        self.plugin_manager.run("pre_register_consumer", name=consumer_name, facts=facts_dict)

        if consumerid:
            consumer = self.cp.getConsumer(consumerid)
            if consumer.get('type', {}).get('manifest', {}):
                raise exceptions.ServiceError(
                    "Registration attempted with a consumer ID that is not of type 'system'")
        else:
            consumer = self.cp.registerConsumer(
                name=consumer_name,
                facts=facts_dict,
                owner=org,
                environment=environment,
                keys=options.get('activation_keys'),
                installed_products=self.installed_mgr.format_for_server(),
                content_tags=self.installed_mgr.tags,
                type=type,
                role=role,
                addons=addons,
                service_level=service_level,
                usage=usage
            )
        self.installed_mgr.write_cache()
        self.plugin_manager.run("post_register_consumer", consumer=consumer, facts=facts_dict)
        managerlib.persist_consumer_cert(consumer)

        # Now that we are registered, load the new identity
        self.identity.reload()
        # We want a new SyncedStore every time as we otherwise can hold onto bad state in
        # long-lived services in dbus
        uep = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()
        store = syspurposelib.SyncedStore(uep, consumer_uuid=self.identity.uuid)
        if store:
            store.sync()
        return consumer

    def validate_options(self, options):
        if self.identity.is_valid() and options['force'] is not True:
            raise exceptions.ValidationError(_("This system is already registered. Add force to options to "
                "override."))
        elif options.get('name') == '':
            raise exceptions.ValidationError(_("Error: system name can not be empty."))
        elif options['consumerid'] and options['force'] is True:
            raise exceptions.ValidationError(_("Error: Can not force registration while attempting to "
                "recover registration with consumerid. Please use --force without --consumerid to re-register"
                " or use the clean command and try again without --force."))

        # If 'activation_keys' already exists in the dictionary, leave it.  Otherwise, set to None.
        if options['activation_keys']:
            # 746259: Don't allow the user to pass in an empty string as an activation key
            if '' == options['activation_keys']:
                raise exceptions.ValidationError(_("Error: Must specify an activation key"))
            elif getattr(self.cp, 'username', None) or getattr(self.cp, 'password', None):
                raise exceptions.ValidationError(_("Error: Activation keys do not require user credentials."))
            elif options['consumerid']:
                raise exceptions.ValidationError(_("Error: Activation keys can not be used with previously"
                    " registered IDs."))
            elif options['environment']:
                raise exceptions.ValidationError(_("Error: Activation keys do not allow environments to be"
                    " specified."))
        elif not getattr(self.cp, 'username', None) or not getattr(self.cp, 'password', None):
            raise exceptions.ValidationError(_("Error: Missing username or password."))
