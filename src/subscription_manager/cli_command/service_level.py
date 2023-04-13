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

import rhsm.connection as connection
import subscription_manager.injection as inj

from rhsm.connection import UnauthorizedException, ProxyException

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.abstract_syspurpose import AbstractSyspurposeCommand
from subscription_manager.cli_command.cli import (
    ERR_NOT_REGISTERED_CODE,
    ERR_NOT_REGISTERED_MSG,
    handle_exception,
)
from subscription_manager.cli_command.org import OrgCommand
from subscription_manager.i18n import ugettext as _

from syspurpose.files import SyncedStore

log = logging.getLogger(__name__)


class ServiceLevelCommand(AbstractSyspurposeCommand, OrgCommand):
    def __init__(self, subparser=None):
        shortdesc = _("Show or modify the system purpose service-level setting")
        super(ServiceLevelCommand, self).__init__(
            "service-level",
            subparser,
            shortdesc,
            False,
            attr="service_level_agreement",
            commands=["set", "unset", "show", "list"],
        )
        self._add_url_options()

        self.identity = inj.require(inj.IDENTITY)

    def _validate_options(self):
        if self.options.set:
            self.options.set = self.options.set.strip()

        # Assume --show if run with no args:
        if (
            not self.options.list
            and not self.options.show
            and not self.options.set
            and not self.options.set == ""
            and not self.options.unset
        ):
            self.options.show = True

        if self.options.org and not self.options.list and not self.options.set:
            system_exit(os.EX_USAGE, _("Error: --org is only supported with the --list or --set option"))

        if not self.is_registered():
            if self.options.list:
                if not (self.options.username and self.options.password) and not self.options.token:
                    system_exit(
                        os.EX_USAGE,
                        _(
                            "Error: you must register or specify --username "
                            "and --password to list service levels"
                        ),
                    )
            elif self.options.unset or self.options.set:
                pass  # RHBZ 1632248 : User should be able to set/unset while not registered.
            elif self.options.show:
                pass  # When system is not registered, then user should have ability to display current value
            else:
                system_exit(ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG)

        if self.is_registered() and (
            getattr(self.options, "username", None)
            or getattr(self.options, "password", None)
            or getattr(self.options, "token", None)
            or getattr(self.options, "org", None)
            or getattr(self.options, "server_url", None)
        ):
            system_exit(
                os.EX_USAGE,
                _(
                    "Error: --username, --password, --token, --org and --serverurl "
                    "can be used only on unregistered systems"
                ),
            )

    def _do_command(self):
        self._validate_options()
        try:
            # If we have a username/password, we're going to use that, otherwise
            # we'll use the identity certificate. We already know one or the other
            # exists:
            if self.options.token:
                self.cp = self.cp_provider.get_keycloak_auth_cp(self.options.token)
            elif self.options.username and self.options.password:
                self.cp_provider.set_user_pass(self.username, self.password)
                self.cp = self.cp_provider.get_basic_auth_cp()
            elif not self.is_registered() and self.options.show:
                pass
            else:
                # get an UEP as consumer
                self.cp = self.cp_provider.get_consumer_auth_cp()
        except connection.RestlibException as re:
            log.exception(re)
            log.error("Error: Unable to retrieve service levels: {re}".format(re=re))

            system_exit(os.EX_SOFTWARE, re)
        except Exception as e:
            handle_exception(_("Error: Unable to retrieve service levels."), e)
        else:
            try:
                if self.options.unset:
                    self.unset()
                elif self.options.set is not None:
                    self.set()
                elif self.options.list:
                    self.list_service_levels()
                elif self.options.show:
                    self.show()
                else:
                    self.show()
            except UnauthorizedException as uex:
                handle_exception(_(str(uex)), uex)
            except connection.GoneException as ge:
                raise ge
            except connection.RestlibException as re_err:
                log.exception(re_err)
                log.error("Error: Unable to retrieve service levels: {err}".format(err=re_err))

                system_exit(os.EX_SOFTWARE, re_err)
            except ProxyException as exc:
                system_exit(os.EX_UNAVAILABLE, exc)

    def set(self):
        if self.cp.has_capability("syspurpose"):
            self.store = SyncedStore(uep=self.cp, consumer_uuid=self.identity.uuid)
            super(ServiceLevelCommand, self).set()
        else:
            self.update_service_level(self.options.set)
            print(_('Service level set to: "{val}".').format(val=self.options.set))

    def unset(self):
        if self.cp.has_capability("syspurpose"):
            self.store = SyncedStore(uep=self.cp, consumer_uuid=self.identity.uuid)
            super(ServiceLevelCommand, self).unset()
        else:
            self.update_service_level("")
            print(_("Service level preference has been unset"))

    def update_service_level(self, service_level):
        consumer = self.cp.getConsumer(self.identity.uuid)
        if "serviceLevel" not in consumer:
            system_exit(
                os.EX_UNAVAILABLE,
                _("Error: The service-level command is not supported by the server."),
            )
        self.cp.updateConsumer(self.identity.uuid, service_level=service_level)

    def show(self):
        if self.cp.has_capability("syspurpose"):
            self.store = SyncedStore(uep=self.cp, consumer_uuid=self.identity.uuid)
            super(ServiceLevelCommand, self).show()
        else:
            self.show_service_level()

    def show_service_level(self):
        consumer = self.cp.getConsumer(self.identity.uuid)
        if "serviceLevel" not in consumer:
            system_exit(
                os.EX_UNAVAILABLE,
                _("Error: The service-level command is not supported by the server."),
            )
        service_level = consumer["serviceLevel"] or ""
        if service_level:
            print(_("Current service level: {level}").format(level=service_level))
        else:
            print(_("Service level preference not set"))

    def list_service_levels(self):
        if self.is_registered():
            org_key = self.cp.getOwner(self.identity.uuid)["key"]
        else:
            org_key = self.org

        try:
            slas = self.cp.getServiceLevelList(org_key)
            if len(slas):
                print("+-------------------------------------------+")
                print("           {label}".format(label=_("Available Service Levels")))
                print("+-------------------------------------------+")
                for sla in slas:
                    print(sla)
            else:
                print(
                    _(
                        'There are no available values for the system purpose "{syspurpose_attr}" '
                        "from the available subscriptions in this "
                        "organization."
                    ).format(syspurpose_attr="service_level")
                )
        except UnauthorizedException as e:
            raise e
        except connection.RemoteServerException:
            system_exit(
                os.EX_UNAVAILABLE, _("Error: The service-level command is not supported by the server.")
            )
        except connection.GoneException as ge:
            raise ge
        except connection.RestlibException as e:
            if e.code == 404 and e.msg.find("/servicelevels") > 0:
                system_exit(
                    os.EX_UNAVAILABLE, _("Error: The service-level command is not supported by the server.")
                )
            elif e.code == 404:
                system_exit(os.EX_DATAERR, e)
            else:
                raise e
