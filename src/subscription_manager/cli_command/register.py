#
# Subscription manager command line utility.
#
# Copyright (c) 2021 Red Hat, Inc.
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
import logging
import os
import readline
import six.moves

import rhsm.connection as connection
import subscription_manager.injection as inj

from optparse import SUPPRESS_HELP

from rhsm.connection import RemoteServerException
from rhsm.https import ssl

from rhsmlib.facts.hwprobe import ClassicCheck
from rhsmlib.services import attach, unregister, register, exceptions

from subscription_manager import identity
from subscription_manager.branding import get_branding
from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import handle_exception, conf
from subscription_manager.cli_command.list import show_autosubscribe_output
from subscription_manager.cli_command.user_pass import UserPassCommand
from subscription_manager.entcertlib import CONTENT_ACCESS_CERT_CAPABILITY
from subscription_manager.i18n import ugettext as _
from subscription_manager.utils import restart_virt_who, print_error, get_supported_resources

log = logging.getLogger(__name__)


class RegisterCommand(UserPassCommand):
    def __init__(self):
        shortdesc = get_branding().CLI_REGISTER

        super(RegisterCommand, self).__init__("register", shortdesc, True)

        self._add_url_options()
        self.parser.add_option("--baseurl", dest="base_url",
                               default=None, help=_("base URL for content in form of https://hostname:port/prefix"))
        self.parser.add_option("--type", dest="consumertype", default="system", metavar="UNITTYPE",
                               help=SUPPRESS_HELP)
        self.parser.add_option("--name", dest="consumername", metavar="SYSTEMNAME",
                               help=_("name of the system to register, defaults to the hostname"))
        self.parser.add_option("--consumerid", dest="consumerid", metavar="SYSTEMID",
                               help=_("the existing system data is pulled from the server"))
        self.parser.add_option("--org", dest="org", metavar="ORG_KEY",
                               help=_(
                                   "register with one of multiple organizations for the user, using organization key"))
        self.parser.add_option("--environment", dest="environment",
                               help=_("register with a specific environment in the destination org"))
        self.parser.add_option("--release", dest="release",
                               help=_("set a release version"))
        self.parser.add_option("--autosubscribe", action='store_true',
                               help=_("Deprecated, see --auto-attach"))
        self.parser.add_option("--auto-attach", action='store_true', dest="autoattach",
                               help=_("automatically attach compatible subscriptions to this system"))
        self.parser.add_option("--force", action='store_true',
                               help=_("register the system even if it is already registered"))
        self.parser.add_option("--activationkey", action='append', dest="activation_keys",
                               help=_("activation key to use for registration (can be specified more than once)"))
        self.parser.add_option("--servicelevel", dest="service_level",
                               help=_("system preference used when subscribing automatically, requires --auto-attach"))

    def _validate_options(self):
        self.autoattach = self.options.autosubscribe or self.options.autoattach
        if self.is_registered() and not self.options.force:
            system_exit(os.EX_USAGE, _("This system is already registered. Use --force to override"))
        elif self.options.consumername == '':
            system_exit(os.EX_USAGE, _("Error: system name can not be empty."))
        elif (self.options.username or self.options.token) and self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Activation keys do not require user credentials."))
        elif self.options.consumerid and self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Activation keys can not be used with previously registered IDs."))
        elif self.options.environment and self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Activation keys do not allow environments to be specified."))
        elif self.autoattach and self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Activation keys cannot be used with --auto-attach."))
        # 746259: Don't allow the user to pass in an empty string as an activation key
        elif self.options.activation_keys and '' in self.options.activation_keys:
            system_exit(os.EX_USAGE, _("Error: Must specify an activation key"))
        elif self.options.service_level and not self.autoattach:
            system_exit(os.EX_USAGE, _("Error: Must use --auto-attach with --servicelevel."))
        elif self.options.activation_keys and not self.options.org:
            system_exit(os.EX_USAGE, _("Error: Must provide --org with activation keys."))
        elif self.options.force and self.options.consumerid:
            system_exit(
                os.EX_USAGE,
                _("Error: Can not force registration while attempting to recover registration with consumerid. "
                  "Please use --force without --consumerid to re-register or use the clean command and "
                  "try again without --force."))
        # 1485008: allow registration, when --type=RHUI (many of KBase articles describe using RHUI not rhui)
        elif self.options.consumertype and not \
                (self.options.consumertype.lower() == 'rhui' or self.options.consumertype == 'system'):
            system_exit(os.EX_USAGE, _("Error: The --type option has been deprecated and may not be used."))

    def persist_server_options(self):
        """
        If the user provides a --serverurl or --baseurl, we want to persist it
        to the config file so that future commands will use the value.
        """
        return True

    def _do_command(self):
        """
        Executes the command.
        """

        self.log_client_version()

        # Always warn the user if registered to old RHN/Spacewalk
        if ClassicCheck().is_registered_with_classic():
            print(get_branding().REGISTERED_TO_OTHER_WARNING)

        self._validate_options()

        # gather installed products info
        self.installed_mgr = inj.require(inj.INSTALLED_PRODUCTS_MANAGER)

        previously_registered = False
        if self.is_registered() and self.options.force:
            previously_registered = True
            # First let's try to un-register previous consumer; if this fails
            # we'll let the error bubble up, so that we don't blindly re-register.
            # managerlib.unregister handles the special case that the consumer has already been removed.
            old_uuid = self.identity.uuid

            print(_("Unregistering from: {hostname}:{port}{prefix}").format(
                  hostname=conf["server"]["hostname"], port=conf["server"]["port"], prefix=conf["server"]["prefix"]))
            try:
                unregister.UnregisterService(self.cp).unregister()
                self.entitlement_dir.__init__()
                self.product_dir.__init__()
                log.info("--force specified, unregistered old consumer: {old_uuid}".format(old_uuid=old_uuid))
                print(_("The system with UUID {old_uuid} has been unregistered").format(old_uuid=old_uuid))
            except ssl.SSLError as e:
                # since the user can override serverurl for register, a common use case is to try to switch servers
                # using register --force... However, this normally cannot successfully unregister since the servers
                # are different.
                handle_exception("Unregister failed: {e}".format(e=e), e)
            except Exception as e:
                handle_exception("Unregister failed", e)

        self.cp_provider.clean()
        if previously_registered:
            print(_("All local data removed"))

        # Proceed with new registration:
        try:
            if self.options.token:
                admin_cp = self.cp_provider.get_keycloak_auth_cp(self.options.token)
            elif not self.options.activation_keys:
                hostname = conf["server"]["hostname"]
                if ":" in hostname:
                    normalized_hostname = "[{hostname}]".format(hostname=hostname)
                else:
                    normalized_hostname = hostname
                print(_("Registering to: {hostname}:{port}{prefix}").format(
                      hostname=normalized_hostname, port=conf["server"]["port"], prefix=conf["server"]["prefix"]))
                self.cp_provider.set_user_pass(self.username, self.password)
                admin_cp = self.cp_provider.get_basic_auth_cp()
            else:
                admin_cp = self.cp_provider.get_no_auth_cp()

            # This is blocking and not async, which aside from blocking here, also
            # means things like following name owner changes gets weird.
            service = register.RegisterService(admin_cp)

            if self.options.consumerid:
                log.debug("Registering as existing consumer: {id}".format(id=self.options.consumerid))
                consumer = service.register(None, consumerid=self.options.consumerid)
            else:
                if self.options.org:
                    owner_key = self.options.org
                else:
                    owner_key = service.determine_owner_key(
                        username=self.username,
                        get_owner_cb=self._get_owner_cb,
                        no_owner_cb=self._no_owner_cb
                    )
                environment_id = self._get_environment_id(admin_cp, owner_key, self.options.environment)
                consumer = service.register(
                    owner_key,
                    activation_keys=self.options.activation_keys,
                    environment=environment_id,
                    force=self.options.force,
                    name=self.options.consumername,
                    type=self.options.consumertype,
                    service_level=self.options.service_level,
                )
        except (connection.RestlibException, exceptions.ServiceError) as re:
            log.exception(re)
            system_exit(os.EX_SOFTWARE, re)
        except Exception as e:
            handle_exception(_("Error during registration: {e}").format(e=e), e)
        else:
            consumer_info = identity.ConsumerIdentity(consumer['idCert']['key'], consumer['idCert']['cert'])
            print(_("The system has been registered with ID: {id}").format(id=consumer_info.getConsumerId()))
            print(_("The registered system name is: {name}").format(name=consumer_info.getConsumerName()))
            if self.options.service_level:
                print(_("Service level set to: {level}").format(level=self.options.service_level))

        # We have new credentials, restart virt-who
        restart_virt_who()

        # get a new UEP as the consumer
        self.cp = self.cp_provider.get_consumer_auth_cp()

        # log the version of the server we registered to
        self.log_server_version()

        facts = inj.require(inj.FACTS)

        # FIXME: can these cases be replaced with invoking
        # FactsLib (or a FactsManager?)
        # Must update facts to clear out the old ones:
        if self.options.consumerid:
            log.debug("Updating facts")
            #
            # FIXME: Need a ConsumerFacts.sync or update or something
            # TODO: We register, with facts, then update facts again...?
            #       Are we trying to sync potential new or dynamic facts?
            facts.update_check(self.cp, consumer['uuid'], force=True)

        # Facts and installed products went out with the registration request,
        # manually write caches to disk:
        # facts service job now(soon)
        facts.write_cache()
        self.installed_mgr.update_check(self.cp, consumer['uuid'])

        if self.options.release:
            # TODO: grab the list of valid options, and check
            self.cp.updateConsumer(consumer['uuid'], release=self.options.release)

        if self.autoattach:
            if 'serviceLevel' not in consumer and self.options.service_level:
                system_exit(os.EX_UNAVAILABLE, _("Error: The --servicelevel option is not supported "
                                                 "by the server. Did not complete your request."))
            try:
                # We don't call auto_attach with self.option.service_level, because it has been already
                # set during service.register() call
                attach.AttachService(self.cp).attach_auto(service_level=None)
            except connection.RestlibException as rest_lib_err:
                print_error(str(rest_lib_err))
            except Exception:
                log.exception("Auto-attach failed")
                raise

        if self.options.consumerid or \
                self.options.activation_keys or \
                self.autoattach or \
                self.cp.has_capability(CONTENT_ACCESS_CERT_CAPABILITY):
            log.debug("System registered, updating entitlements if needed")
            # update certs, repos, and caches.
            # FIXME: aside from the overhead, should this be cert_action_client.update?
            self.entcertlib.update()

        try:
            profile_mgr = inj.require(inj.PROFILE_MANAGER)
            # 767265: always force an upload of the packages when registering
            profile_mgr.update_check(self.cp, consumer['uuid'], True)
        except RemoteServerException as err:
            # When it is not possible to upload profile ATM, then print only error about this
            # to rhsm.log. The rhsmcertd will try to upload it next time.
            log.error("Unable to upload profile: {err}".format(err=str(err)))

        subscribed = 0
        if self.options.activation_keys or self.autoattach:
            # update with latest cert info
            self.sorter = inj.require(inj.CERT_SORTER)
            self.sorter.force_cert_check()
            subscribed = show_autosubscribe_output(self.cp, self.identity)

        self._request_validity_check()
        return subscribed

    def _prompt_for_environment(self):
        """
        By breaking this code out, we can write cleaner tests
        """
        environment = six.moves.input(_("Environment: ")).strip()
        readline.clear_history()
        return environment or self._prompt_for_environment()

    def _get_environment_id(self, cp, owner_key, environment_name):
        # If none specified on CLI and the server doesn't support environments,
        # return None, the registration method will skip environment specification.

        # Activation keys may not be used with environment for registration.
        # We use a no-auth cp, so we cannot look up environment ids by name
        if self.options.activation_keys:
            return None

        supported_resources = get_supported_resources()
        supports_environments = 'environments' in supported_resources
        if not environment_name:
            if supports_environments:
                env_list = cp.getEnvironmentList(owner_key)

                # If there aren't any environments, don't prompt for one
                if not env_list:
                    return environment_name

                # If the envronment list is len 1, pick that environment
                if len(env_list) == 1:
                    log.debug("Using the only available environment: \"{name}\"".format(name=env_list[0]["name"]))
                    return env_list[0]['id']

                env_name_list = [env['name'] for env in env_list]
                print(_('Hint: Organization "{key}" contains following environments: {list}').format(
                      key=owner_key, list=", ".join(env_name_list)))

                environment_name = self._prompt_for_environment()

                # Should only ever be len 0 or 1
                env_matches = [env['id'] for env in env_list if env['name'] == environment_name]
                if env_matches:
                    return env_matches[0]
                system_exit(os.EX_DATAERR, _("No such environment: {name}").format(name=environment_name))

            # Server doesn't support environments
            return environment_name

        if not supports_environments:
            system_exit(os.EX_UNAVAILABLE, _("Error: Server does not support environments."))

        env = cp.getEnvironment(owner_key=owner_key, name=environment_name)
        if not env:
            system_exit(os.EX_DATAERR, _("No such environment: {name}").format(name=environment_name))
        return env['id']

    @staticmethod
    def _no_owner_cb(username):
        """
        Method called, when there it no owner in the list of owners for given user
        :return: None
        """
        system_exit(1, _("{name} cannot register with any organizations.").format(name=username))

    def _get_owner_cb(self, owners):
        """
        Callback method used, when it is necessary to specify owner (organization)
        during registration
        :param owners: list of owners (organizations)
        :return:
        """
        # Print list of owners to the console
        org_keys = [owner['key'] for owner in owners]
        print(_('Hint: User "{name}" is member of following organizations: {orgs}').format(
              name=self.username, orgs=', '.join(org_keys)))

        # Read the owner key from stdin
        owner_key = None
        while not owner_key:
            owner_key = six.moves.input(_("Organization: "))
            readline.clear_history()
        return owner_key
