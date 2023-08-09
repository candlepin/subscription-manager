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

from rhsm import connection
from rhsm.connection import ProxyException

from subscription_manager import syspurposelib
from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG
from subscription_manager.i18n import ungettext, ugettext as _
from subscription_manager.syspurposelib import get_syspurpose_valid_fields
from subscription_manager.utils import friendly_join

from syspurpose.files import SyncedStore, post_process_received_data

log = logging.getLogger(__name__)

SP_CONFLICT_MESSAGE = _(
    'Warning: A {attr} of "{download_value}" was recently set for this system '
    "by the entitlement server administrator.\n{advice}"
)
SP_ADVICE = _("If you'd like to overwrite the server side change please run: {command}")

# TRANSLATORS: this refers to a deprecated command
DEPRECATED_COMMAND_MESSAGE = _("Deprecated, see 'syspurpose'")


class AbstractSyspurposeCommand(CliCommand):
    """
    Abstract command for manipulating an attribute of system purpose.
    """

    def __init__(
        self,
        name,
        subparser,
        shortdesc=None,
        primary=False,
        attr=None,
        commands=("set", "unset", "show", "list"),
    ):
        # set 'subparser' before calling the parent constructor, as it will
        # (indirectly) call _create_argparser(), which our reimplementation uses
        self.subparser = subparser
        if self.subparser is None:
            # this syspurpose command is a deprecated top-level subcommand,
            # so change its description to be a deprecated text
            shortdesc = DEPRECATED_COMMAND_MESSAGE
        super(AbstractSyspurposeCommand, self).__init__(name, shortdesc=shortdesc, primary=primary)
        self.commands = commands
        self.attr = attr

        self.store = None

        if "set" in commands:
            self.parser.add_argument(
                "--set",
                dest="set",
                help=_("set {attr} of system purpose").format(attr=attr),
            )
        if "unset" in commands:
            self.parser.add_argument(
                "--unset",
                dest="unset",
                action="store_true",
                help=_("unset {attr} of system purpose").format(attr=attr),
            )
        if "add" in commands:
            self.parser.add_argument(
                "--add",
                dest="to_add",
                action="append",
                default=[],
                help=_("add an item to the list ({attr}).").format(attr=attr),
            )
        if "remove" in commands:
            self.parser.add_argument(
                "--remove",
                dest="to_remove",
                action="append",
                default=[],
                help=_("remove an item from the list ({attr}).").format(attr=attr),
            )
        if "show" in commands:
            self.parser.add_argument(
                "--show",
                dest="show",
                action="store_true",
                help=_("show this system's current {attr}").format(attr=attr),
            )
        if "list" in commands:
            self.parser.add_argument(
                "--list",
                dest="list",
                action="store_true",
                help=_("list all {attr} available").format(attr=attr),
            )

    def __getattr__(self, name):
        """
        This custom __getattr__() reimplementation is used to lookup attributes
        in the parent syspurpose command, if set; this is done in case the
        current command is a subcommand of 'syspurpose', so
        SyspurposeCommand._do_command() will set a reference to itself as
        'syspurpose_command' attribute.
        """
        syspurpose_command = self.__dict__.get("syspurpose_command", None)
        if syspurpose_command is not None:
            return getattr(syspurpose_command, name)
        raise AttributeError

    def _validate_options(self):
        to_set = getattr(self.options, "set", None)
        to_unset = getattr(self.options, "unset", None)
        to_add = getattr(self.options, "to_add", None)
        to_remove = getattr(self.options, "to_remove", None)
        to_show = getattr(self.options, "show", None)

        if to_set:
            self.options.set = self.options.set.strip()
        if to_add:
            self.options.to_add = [x.strip() for x in self.options.to_add if isinstance(x, str)]
        if to_remove:
            self.options.to_remove = [x.strip() for x in self.options.to_remove if isinstance(x, str)]
        if (to_set or to_add or to_remove) and to_unset:
            system_exit(os.EX_USAGE, _("--unset cannot be used with --set, --add, or --remove"))
        if to_add and to_remove:
            system_exit(os.EX_USAGE, _("--add cannot be used with --remove"))

        if not self.is_registered():
            if self.options.list:
                if self.options.token and not self.options.username:
                    pass
                elif self.options.token and self.options.username:
                    system_exit(os.EX_USAGE, _("Error: you can specify --username or --token not both"))
                elif not self.options.username or not self.options.password:
                    system_exit(
                        os.EX_USAGE,
                        _(
                            "Error: you must register or specify --username and --password to list {attr}"
                        ).format(attr=self.attr),
                    )
            elif to_unset or to_set or to_add or to_remove or to_show:
                pass
            else:
                system_exit(ERR_NOT_REGISTERED_CODE, ERR_NOT_REGISTERED_MSG)

        if self.is_registered() and (
            getattr(self.options, "username", None)
            or getattr(self.options, "password", None)
            or getattr(self.options, "token", None)
            or getattr(self.options, "org", None)
        ):
            system_exit(
                os.EX_USAGE,
                _(
                    "Error: --username, --password, --token and --org "
                    "can be used only on unregistered systems"
                ),
            )

    def _get_valid_fields(self):
        """
        Try to get valid fields from server
        :return: Dictionary with valid fields
        """
        valid_fields = {}
        if self.is_registered():
            # When system is registered, then try to get valid fields from cache file
            try:
                valid_fields = get_syspurpose_valid_fields(uep=self.cp, identity=self.identity)
            except ProxyException as exc:
                system_exit(os.EX_UNAVAILABLE, exc)
        elif self.options.username and self.options.password and self.cp is not None:
            # Try to get current organization key. It is property of OrgCommand.
            # Every Syspurpose command has to be subclass of OrgCommand too
            # must have used credentials in command if not registered to proceed
            try:
                org_key = self.org
                server_response = self.cp.getOwnerSyspurposeValidFields(org_key)
            except connection.RestlibException as rest_err:
                log.warning(
                    "Unable to get list of valid fields using REST API: {rest_err}".format(rest_err=rest_err)
                )
                system_exit(os.EX_SOFTWARE, rest_err)
            except ProxyException as exc:
                system_exit(os.EX_UNAVAILABLE, exc)
            else:
                if "systemPurposeAttributes" in server_response:
                    server_response = post_process_received_data(server_response)
                    valid_fields = server_response["systemPurposeAttributes"]
        return valid_fields

    def _is_provided_value_valid(self, value):
        """
        Try to validate provided value. Check if the value is included in valid fields.
        If the value is not provided in the valid fields and we can connect candlepin server,
        then print some warning.
        :param value: provided value on CLI
        :return: True if the value is valid; otherwise return False
        """
        invalid_values = self._are_provided_values_valid([value])
        return len(invalid_values) == 0

    def _are_provided_values_valid(self, values):
        """
        Try to validate the provided values. Check if all the values are included in valid fields.
        If any of the values is not provided in the valid fields and we can connect candlepin
        server, then print some warning.
        :param values: provided values on CLI
        :return: list of invalid values
        """

        # First check if the the value is in the valid_fields.  Comparison is case insensitive.
        invalid_values = []
        valid_fields = self._get_valid_fields()
        if self.attr in valid_fields:
            for value in values:
                if all([x.casefold() != value.casefold() for x in valid_fields[self.attr]]):
                    invalid_values.append(value)
        invalid_values_len = len(invalid_values)

        # When there are values not in the valid fields, then try to print some warning,
        # when the system is registered or username & password was provided as CLI option.
        # When the system is not registered and no username & password was provided, then
        # these values will be set silently.
        if invalid_values_len > 0:
            if (
                self.is_registered()
                or (self.options.username and self.options.password)
                or self.options.token
            ):
                if len(valid_fields.get(self.attr, [])) > 0:
                    # TRANSLATORS: this is used to quote a string
                    quoted_values = [_('"{value}"').format(value=value) for value in invalid_values]
                    printable_values = friendly_join(quoted_values)
                    print(
                        ungettext(
                            "Warning: Provided value {vals} is not included in the list of valid values",
                            "Warning: Provided values {vals} are not included in the list of valid values",
                            invalid_values_len,
                        ).format(vals=printable_values)
                    )
                    self._print_valid_values(valid_fields)
                else:
                    print(
                        _(
                            "Warning: This organization does not have any subscriptions that provide a "
                            'system purpose "{attr}".  This setting will not influence auto-attaching '
                            "subscriptions."
                        ).format(attr=self.attr)
                    )

        return invalid_values

    def set(self):
        """
        Try to set new syspurpose attribute
        """
        self._set(self.options.set)
        self._is_provided_value_valid(self.options.set)
        success_msg = _('{attr} set to "{val}".').format(attr=self.attr, val=self.options.set)
        self._check_result(
            expectation=lambda res: res.get(self.attr) == self.options.set,
            success_msg=success_msg,
            command='subscription-manager syspurpose {name} --set "{val}"'.format(
                name=self.name, val=self.options.set
            ),
            attr=self.attr,
        )

    def _set(self, to_set):
        if self.store:
            self.store.set(self.attr, to_set)
        else:
            log.debug("Not setting syspurpose attribute {attr} (store not set)".format(attr=self.attr))

    def unset(self):
        self._unset()
        success_msg = _("{attr} unset.").format(attr=self.attr)
        self._check_result(
            expectation=lambda res: res.get(self.attr) in ["", None, []],
            success_msg=success_msg,
            command="subscription-manager syspurpose {name} --unset".format(name=self.name),
            attr=self.attr,
        )

    def _unset(self):
        if self.store:
            self.store.unset(self.attr)
        else:
            log.debug("Not unsetting syspurpose attribute {attr} (store not set)".format(attr=self.attr))

    def add(self):
        self._add(self.options.to_add)
        self._are_provided_values_valid(self.options.to_add)
        success_msg = _("{attr} updated.").format(attr=self.name)
        # When there is several options to add, then format of command is following
        # subscription-manager command --add opt1 --add opt2
        options = ['"' + option + '"' for option in self.options.to_add]
        to_add = "--add " + " --add ".join(options)
        command = "subscription-manager syspurpose {name} ".format(name=self.name) + to_add
        self._check_result(
            expectation=lambda res: all(x in res.get("addons", []) for x in self.options.to_add),
            success_msg=success_msg,
            command=command,
            attr=self.attr,
        )

    def _add(self, to_add):
        if not isinstance(to_add, list):
            to_add = [to_add]

        if self.store:
            for item in to_add:
                self.store.add(self.attr, item)
        else:
            log.debug("Not adding syspurpose attribute {attr} (store not set)".format(attr=self.attr))

    def remove(self):
        self._remove(self.options.to_remove)
        success_msg = _("{attr} updated.").format(attr=self.name.capitalize())
        options = ['"' + option + '"' for option in self.options.to_remove]
        # When there is several options to remove, then format of command is following
        # subscription-manager syspurpose command --remove opt1 --remove opt2
        to_remove = "--remove " + " --remove ".join(options)
        command = "subscription-manager syspurpose {name} ".format(name=self.name) + to_remove
        self._check_result(
            expectation=lambda res: all(x not in res.get("addons", []) for x in self.options.to_remove),
            success_msg=success_msg,
            command=command,
            attr=self.attr,
        )

    def _remove(self, to_remove):
        if not isinstance(to_remove, list):
            to_remove = [to_remove]

        if self.store:
            for item in to_remove:
                self.store.remove(self.attr, item)
        else:
            log.debug("Not removing syspurpose attribute {attr} (store not set)".format(attr=self.attr))

    def show(self):
        if self.is_registered():
            syspurpose = self.sync().result
        else:
            syspurpose = syspurposelib.read_syspurpose()
        if syspurpose is not None and self.attr in syspurpose and syspurpose[self.attr]:
            val = syspurpose[self.attr]
            values = val if not isinstance(val, list) else ", ".join(val)
            print(_("Current {name}: {val}").format(name=self.name.capitalize(), val=values))
        else:
            print(_("{name} not set.").format(name=self.name.capitalize()))

    def _print_valid_values(self, valid_fields):
        """
        Print list of valid values for current syspurpose attribute
        :param valid_fields:
        :return: None
        """
        for valid_value in valid_fields[self.attr]:
            if len(valid_value) > 0:
                print(" - {value}".format(value=valid_value))

    def list(self):
        valid_fields = self._get_valid_fields()
        if self.attr in valid_fields:
            if len(valid_fields[self.attr]) > 0:
                line = "+-------------------------------------------+"
                print(line)
                translated_string = _("Available {syspurpose_attr}").format(syspurpose_attr=self.attr)
                # Print translated string (the length could be different) in the center of the line
                line_len = len(line)
                trans_str_len = len(translated_string)
                empty_space_len = int((line_len - trans_str_len) / 2)
                print(empty_space_len * " " + translated_string)
                print(line)
                # Print values
                self._print_valid_values(valid_fields)
            else:
                print(
                    _(
                        'There are no available values for the system purpose "{syspurpose_attr}" '
                        "from the available subscriptions in this "
                        "organization."
                    ).format(syspurpose_attr=self.attr)
                )
        else:
            print(
                _(
                    "Unable to get the list of valid values for the system purpose " '"{syspurpose_attr}".'
                ).format(syspurpose_attr=self.attr)
            )

    def sync(self):
        return syspurposelib.SyspurposeSyncActionCommand().perform(
            include_result=True, passthrough_gone=True
        )[1]

    def _do_command(self):
        self._validate_options()

        self.cp = None
        try:
            # If we have a username/password, we're going to use that, otherwise
            # we'll use the identity certificate. We already know one or the other
            # exists:
            if self.options.token:
                try:
                    self.cp = self.cp_provider.get_keycloak_auth_cp(self.options.token)
                except Exception as err:
                    log.error(
                        'unable to connect to candlepin server using token: "{token}", err: {err}'.format(
                            token=self.options.token, err=err
                        )
                    )
                    print(_("Unable to connect to server using token"))
            elif self.options.username and self.options.password:
                self.cp_provider.set_user_pass(self.options.username, self.options.password)
                self.cp = self.cp_provider.get_basic_auth_cp()
            else:
                # get an UEP as consumer
                if self.is_registered():
                    self.cp = self.cp_provider.get_consumer_auth_cp()
        except connection.RestlibException as err:
            log.exception(err)
            if getattr(self.options, "list", None):
                log.error(
                    "Error: Unable to retrieve {attr} from server: {err}".format(attr=self.attr, err=err)
                )
                system_exit(os.EX_SOFTWARE, err)
            else:
                log.debug(
                    "Error: Unable to retrieve {attr} from server: {err}".format(attr=self.attr, err=err)
                )
        except Exception as err:
            log.debug("Error: Unable to retrieve {attr} from server: {err}".format(attr=self.attr, err=err))

        self.store = SyncedStore(uep=self.cp, consumer_uuid=self.identity.uuid)

        if getattr(self.options, "unset", None):
            self.unset()
        elif getattr(self.options, "set", None):
            self.set()
        elif hasattr(self.options, "to_add") and len(self.options.to_add) > 0:
            self.add()
        elif hasattr(self.options, "to_remove") and len(self.options.to_remove) > 0:
            self.remove()
        elif getattr(self.options, "list", None):
            self.list()
        elif getattr(self.options, "show", None):
            self.show()
        else:
            self.show()

    def _create_argparser(self):
        if self.subparser is None:
            # Without a subparser, which means it is a standalone command
            return super(AbstractSyspurposeCommand, self)._create_argparser()

        # This string is similar to what _get_usage() returns; we cannot use
        # _get_usage() as it prints the subcommand name as well, and the created
        # ArgumentParser is a subparser (so there is a parent parser already
        # printing the subcommand).
        usage = _("%(prog)s [OPTIONS]")
        return self.subparser.add_parser(
            self.name, description=self.shortdesc, usage=usage, help=self.shortdesc
        )

    def check_syspurpose_support(self, attr):
        if self.is_registered() and not self.cp.has_capability("syspurpose"):
            print(
                _(
                    "Note: The currently configured entitlement server does "
                    "not support System Purpose {attr}."
                ).format(attr=attr)
            )

    def _check_result(self, expectation, success_msg, command, attr):
        if self.store:
            self.store.sync()
            result = self.store.get_cached_contents()
        else:
            result = {}
        if result and not expectation(result):
            advice = SP_ADVICE.format(command=command)
            value = result[attr]
            msg = SP_CONFLICT_MESSAGE.format(attr=attr, download_value=value, advice=advice)
            system_exit(os.EX_SOFTWARE, msg)
        else:
            print(success_msg)
