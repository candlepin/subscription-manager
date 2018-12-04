# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import
#
# Copyright (c) 2018 Red Hat, Inc.
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

import argparse
from syspurpose.files import SyncedStore
from syspurpose.utils import in_container, make_utf8
from syspurpose.i18n import ugettext as _
import json


def add_command(args, syspurposestore):
    """
    Uses the syspurposestore to add one or more values to a particular property.
    :param args: The parsed args from argparse, expected attributes are:
        prop_name: the string name of the property to add to
        values: A list of the values to add to the given property (could be anything json-serializable)
    :param syspurposestore: An SyspurposeStore object to manipulate
    :return: None
    """
    for value in args.values:
        if syspurposestore.add(args.prop_name, value):
            print(_("Added {} to {}.").format(make_utf8(value), make_utf8(args.prop_name)))
        else:
            print(_("Not adding value {} to {}; it already exists.").format(make_utf8(value), make_utf8(args.prop_name)))

def remove_command(args, syspurposestore):
    """
    Uses the syspurposestore to remove one or more values from a particular property.
    :param args: The parsed args from argparse, expected attributes are:
        prop_name: the string name of the property to add to
        values: A list of the values to remove from the given property (could be anything json-serializable)
    :param syspurposestore: An SyspurposeStore object to manipulate
    :return: None
    """
    for value in args.values:
        if syspurposestore.remove(args.prop_name, value):
            print(_("Removed {} from {}.").format(make_utf8(value), make_utf8(args.prop_name)))
        else:
            print(_("Not removing value {} from {}; it was not there.").format(make_utf8(value), make_utf8(args.prop_name)))

def set_command(args, syspurposestore):
    """
    Uses the syspurposestore to set the prop_name to value.
    :param args: The parsed args from argparse, expected attributes are:
        prop_name: the string name of the property to set
        value: An object to set the property to (could be anything json-serializable)
    :param syspurposestore: An SyspurposeStore object to manipulate
    :return: None
    """
    syspurposestore.set(args.prop_name, args.value)
    print(_("{} set to {}").format(make_utf8(args.prop_name), make_utf8(args.value)))


def unset_command(args, syspurposestore):
    """
    Uses the syspurposestore to unset (clear entirely) the prop_name.
    :param args: The parsed args from argparse, expected attributes are:
        prop_name: the string name of the property to unset (clear)
    :param syspurposestore: An SyspurposeStore object to manipulate
    :return: None
    """
    syspurposestore.unset(args.prop_name)
    print(_("{} unset").format(make_utf8(args.prop_name)))


def show_contents(args, syspurposestore):
    """
    :param args:
    :param syspurposestore:
    :return:
    """

    contents = syspurposestore.sync().result
    print(json.dumps(contents, indent=2, ensure_ascii=False))


def setup_arg_parser():
    """
    Sets up argument parsing for the syspurpose tool.
    :return: An argparse.ArgumentParser ready to use to parse_args
    """
    parser = argparse.ArgumentParser(prog="syspurpose", description="System Syspurpose Management Tool")
    parser.set_defaults(func=None, requires_write=False)

    subparsers = parser.add_subparsers(help="sub-command help")

    # Arguments shared by subcommands
    add_options = argparse.ArgumentParser(add_help=False)
    add_options.add_argument("values", help="The value(s) to add", nargs='+')
    add_options.set_defaults(func=add_command, requires_write=True)

    remove_options = argparse.ArgumentParser(add_help=False)
    remove_options.add_argument("values", help="The value(s) to remove", nargs='+')
    remove_options.set_defaults(func=remove_command, requires_write=True)

    set_options = argparse.ArgumentParser(add_help=False)
    set_options.add_argument("value", help="The value to set", action="store")
    set_options.set_defaults(func=set_command, requires_write=True)

    unset_options = argparse.ArgumentParser(add_help=False)
    unset_options.set_defaults(func=unset_command, requires_write=True)

    # Generic assignments
    # Set ################
    generic_set_parser = subparsers.add_parser("set",
        help=_("Sets the value for the given property"))

    generic_set_parser.add_argument("prop_name",
        metavar="property",
        help=_("The name of the property to set/update"),
        action="store")

    generic_set_parser.add_argument("value",
        help=_("The value to set"),
        action="store")

    generic_set_parser.set_defaults(func=set_command, requires_write=True)

    # Unset ##############
    generic_unset_parser = subparsers.add_parser("unset",
        help=_("Unsets (clears) the value for the given property"),
        parents=[unset_options])

    generic_unset_parser.add_argument("prop_name",
        metavar="property",
        help=_("The name of the property to set/update"),
        action="store")

    # Add ################
    generic_add_parser = subparsers.add_parser("add",
        help=_("Adds the value(s) to the given property"))

    generic_add_parser.add_argument("prop_name",
        metavar="property",
        help=_("The name of the property to update"),
        action="store")

    generic_add_parser.add_argument("values",
        help=_("The value(s) to add"),
        action="store",
        nargs="+")

    generic_add_parser.set_defaults(func=add_command, requires_write=True)

    # Remove #############
    generic_remove_parser = subparsers.add_parser("remove",
        help=_("Removes the value(s) from the given property"))

    generic_remove_parser.add_argument("prop_name",
        metavar="property",
        help=_("The name of the property to update"),
        action="store")

    generic_remove_parser.add_argument("values",
        help=_("The value(s) to remove"),
        action="store",
        nargs="+")

    generic_remove_parser.set_defaults(func=remove_command, requires_write=True)

    # Targeted commands
    # Roles ##########
    set_role_parser = subparsers.add_parser("set-role",
        help=_("Set the system role to the system syspurpose"),
        parents=[set_options])
    # TODO: Set prop_name from schema file
    set_role_parser.set_defaults(prop_name="role")

    unset_role_parser = subparsers.add_parser("unset-role",
        help=_("Clear set role"),
        parents=[unset_options])
    unset_role_parser.set_defaults(prop_name="role")

    # ADDONS #############
    add_addons_parser = subparsers.add_parser("add-addons",
        help=_("Add addons to the system syspurpose"),
        parents=[add_options])
    # TODO: Set prop_name from schema file
    add_addons_parser.set_defaults(prop_name="addons")

    remove_addons_parser = subparsers.add_parser("remove-addons",
        help=_("Remove addons from the system syspurpose"),
        parents=[remove_options])
    remove_addons_parser.set_defaults(prop_name="addons")

    unset_role_parser = subparsers.add_parser("unset-addons",
        help=_("Clear set addons"),
        parents=[unset_options])
    unset_role_parser.set_defaults(prop_name="addons")


    # SLA ################
    set_sla_parser = subparsers.add_parser("set-sla",
        help=_("Set the system sla"),
        parents=[set_options])
    set_sla_parser.set_defaults(prop_name="service_level_agreement")

    unset_sla_parser = subparsers.add_parser("unset-sla",
        help=_("Clear set sla"),
        parents=[unset_options])
    unset_sla_parser.set_defaults(prop_name="service_level_agreement")

    # USAGE ##############
    set_usage_parser = subparsers.add_parser("set-usage",
       help=_("Set the system usage"),
       parents=[set_options])

    set_usage_parser.set_defaults(prop_name="usage")

    unset_usage_parser = subparsers.add_parser("unset-usage",
        help=_("Clear set usage"),
        parents=[unset_options])
    unset_usage_parser.set_defaults(prop_name="usage")

    # Pretty Print Json contents of default syspurpose file
    show_parser = subparsers.add_parser("show",
        help=_("Show the current system syspurpose"))
    show_parser.set_defaults(func=show_contents, requires_write=False)

    return parser


def main():
    """
    Run the cli (Do the syspurpose tool thing!!)
    :return: 0
    """
    parser = setup_arg_parser()
    args = parser.parse_args()

    # Syspurpose is not intended to be used in containers for the time being (could change later).
    if in_container():
        print(_("WARNING: Setting syspurpose in containers has no effect."
              "Please run syspurpose on the host.\n"))

    try:
        from subscription_manager.identity import Identity
        from subscription_manager.cp_provider import CPProvider
        identity = Identity()
        uuid = identity.uuid
        uep = CPProvider().get_consumer_auth_cp()
    except ImportError:
        uuid = None
        uep = None
        print(_("Warning: Unable to sync system purpose with subscription management server:"
                " subscription_manager module is not available."))

    syspurposestore = SyncedStore(uep=uep, consumer_uuid=uuid)
    if args.func is not None:
        args.func(args, syspurposestore)
    else:
        parser.print_help()
        return 0
    result = syspurposestore.sync()
    if result:
        if result.remote_changed:
            print(_("System purpose successfully sent to subscription management server."))
        else:
            print(_("Unable to send system purpose to subscription management server"))

    return 0
