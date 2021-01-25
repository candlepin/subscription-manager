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
            type=None, role=None, addons=None, service_level=None, usage=None, jwt_token=None, **kwargs):
        # We accept a kwargs argument so that the DBus object can pass the options dictionary it
        # receives transparently to the service via dictionary unpacking.  This strategy allows the
        # DBus object to be more independent of the service implementation.

        # If there are any values in kwargs that don't map to keyword arguments defined in the message
        # signature we want to consider that an error.
        if kwargs:
            raise exceptions.ValidationError(_("Unknown arguments: %s") % kwargs.keys())

        syspurpose = syspurposelib.read_syspurpose()

        save_syspurpose = False

        # First set new syspurpose values, if there is any
        if role is not None:
            syspurpose['role'] = role
            save_syspurpose = True
        if addons is not None:
            syspurpose['addons'] = addons
            save_syspurpose = True
        if service_level is not None:
            syspurpose['service_level_agreement'] = service_level
            save_syspurpose = True
        if usage is not None:
            syspurpose['usage'] = usage
            save_syspurpose = True

        # Then try to get all syspurpose values
        role = syspurpose.get('role', '')
        addons = syspurpose.get('addons', [])
        usage = syspurpose.get('usage', '')
        service_level = syspurpose.get('service_level_agreement', '')

        type = type or "system"

        options = {
            'activation_keys': activation_keys,
            'environment': environment,
            'force': force,
            'name': name,
            'consumerid': consumerid,
            'type': type,
            'jwt_token': jwt_token
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
                usage=usage,
                jwt_token=jwt_token
            )
        self.installed_mgr.write_cache()
        self.plugin_manager.run("post_register_consumer", consumer=consumer, facts=facts_dict)
        managerlib.persist_consumer_cert(consumer)

        # Now that we are registered, load the new identity
        self.identity.reload()

        # If new syspurpose values were given as arguments, then save these values to syspurpose.json now
        if save_syspurpose is True:
            syspurposelib.write_syspurpose(syspurpose)

        syspurpose_dict = {
            'service_level_agreement': consumer['serviceLevel'] if 'serviceLevel' in list(consumer.keys()) else '',
            'role': consumer['role'] if 'role' in list(consumer.keys()) else '',
            'usage': consumer['usage'] if 'usage' in list(consumer.keys()) else '',
            'addons': consumer['addOns'] if 'addOns' in list(consumer.keys()) else []
        }

        # Try to do three-way merge and then save result to syspurpose.json file
        local_result = syspurposelib.merge_syspurpose_values(remote=syspurpose_dict, base={})
        syspurposelib.write_syspurpose(local_result)

        # Save syspurpose attributes from consumer to cache file
        syspurposelib.write_syspurpose_cache(syspurpose_dict)

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
        elif options.get('jwt_token') is not None:
            # TODO: add more checks here
            pass
        elif not getattr(self.cp, 'username', None) or not getattr(self.cp, 'password', None):
            if not getattr(self.cp, 'token', None):
                raise exceptions.ValidationError(_("Error: Missing username or password."))

    def determine_owner_key(self, username, get_owner_cb, no_owner_cb):
        """
        Method used for specification of owner key during registration. When there is more than
        one owners and it is necessary to specify one, then get_owner_cb is called with the list
        of owners as the argument. When user is not member of any group, then no_owner_cb is called.
        :param username: Username
        :param get_owner_cb: Callback method called, when it is necessary determine wanted owner (org)
        :param no_owner_cb: Callback method called, when user is not member of any owner (org)
        :return: Owner key (organization)
        """

        owners = self.cp.getOwnerList(username)

        # When there is no organization, then call callback method for this case
        if len(owners) == 0:
            no_owner_cb(username)

        # When there is only one owner, then return key of the owner
        if len(owners) == 1:
            return owners[0]['key']

        # When there is more owner, then call callback method for this case
        owner_key = get_owner_cb(owners)

        return owner_key
