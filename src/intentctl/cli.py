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
from intentctl.intentfiles import IntentStore, USER_INTENT
from intentctl.utils import in_container
import json


def add_command(args, intentstore):
    """
    Uses the intentstore to add one or more values to a particular property.
    :param args: The parsed args from argparse, expected attributes are:
        prop_name: the string name of the property to add to
        values: A list of the values to add to the given property (could be anything json-serializable)
    :param intentstore: An IntentStore object to manipulate
    :return: None
    """
    for value in args.values:
        intentstore.add(args.prop_name, value)
    print("Added {} to {}".format(args.values, args.prop_name))


def remove_command(args, intentstore):
    """
    Uses the intentstore to remove one or more values from a particular property.
    :param args: The parsed args from argparse, expected attributes are:
        prop_name: the string name of the property to add to
        values: A list of the values to remove from the given property (could be anything json-serializable)
    :param intentstore: An IntentStore object to manipulate
    :return: None
    """
    for value in args.values:
        intentstore.remove(args.prop_name, value)
    print("Removed {} from {}".format(args.values, args.prop_name))


def set_command(args, intentstore):
    """
    Uses the intentstore to set the prop_name to value.
    :param args: The parsed args from argparse, expected attributes are:
        prop_name: the string name of the property to set
        value: An object to set the property to (could be anything json-serializable)
    :param intentstore: An IntentStore object to manipulate
    :return: None
    """
    intentstore.set(args.prop_name, args.value)
    print("{} set to {}".format(args.prop_name, args.value))


def unset_command(args, intentstore):
    """
    Uses the intentstore to unset (clear entirely) the prop_name.
    :param args: The parsed args from argparse, expected attributes are:
        prop_name: the string name of the property to unset (clear)
    :param intentstore: An IntentStore object to manipulate
    :return: None
    """
    intentstore.unset(args.prop_name)
    print("{} unset.".format(args.prop_name))


def show_contents(args, intentstore):
    """
    :param args:
    :param intentstore:
    :return:
    """

    contents = intentstore.contents
    print(json.dumps(contents, indent=2))


def setup_arg_parser():
    """
    Sets up argument parsing for the intentctl tool.
    :return: An argparse.ArgumentParser ready to use to parse_args
    """
    parser = argparse.ArgumentParser(prog="intentctl", description="System Intent Management Tool")
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
        help="Sets the value for the given property")

    generic_set_parser.add_argument("prop_name",
        metavar="property",
        help="The name of the property to set/update",
        action="store")

    generic_set_parser.add_argument("value",
        help="The value to set",
        action="store")

    generic_set_parser.set_defaults(func=set_command, requires_write=True)

    # Unset ##############
    generic_unset_parser = subparsers.add_parser("unset",
        help="Unsets (clears) the value for the given property",
        parents=[unset_options])

    generic_unset_parser.add_argument("prop_name",
        metavar="property",
        help="The name of the property to set/update",
        action="store")

    # Add ################
    generic_add_parser = subparsers.add_parser("add",
        help="Adds the value(s) to the given property")

    generic_add_parser.add_argument("prop_name",
        metavar="property",
        help="The name of the property to update",
        action="store")

    generic_add_parser.add_argument("values",
        help="The value(s) to add",
        action="store",
        nargs="+")

    generic_add_parser.set_defaults(func=add_command, requires_write=True)

    # Remove #############
    generic_remove_parser = subparsers.add_parser("remove",
        help="Removes the value(s) from the given property")

    generic_remove_parser.add_argument("prop_name",
        metavar="property",
        help="The name of the property to update",
        action="store")

    generic_remove_parser.add_argument("values",
        help="The value(s) to remove",
        action="store",
        nargs="+")

    generic_remove_parser.set_defaults(func=remove_command, requires_write=True)

    # Targeted commands
    # Offerings ##########
    add_offering_parser = subparsers.add_parser("add-offerings",
                                                help="Add one or more offerings to the system intent.",
                                                parents=[add_options])
    # TODO: Set prop_name from schema file
    add_offering_parser.set_defaults(prop_name="offering_name")

    remove_offering_parser = subparsers.add_parser("remove-offerings",
                                                   help="Remove one or more offerings.",
                                                   parents=[remove_options])
    remove_offering_parser.set_defaults(prop_name="offering_name")

    unset_offering_parser = subparsers.add_parser("unset-offerings",
                                                  help="Unset all offerings.",
                                                  parents=[unset_options])
    unset_offering_parser.set_defaults(prop_name="offering_name")

    # SLA ################
    set_sla_parser = subparsers.add_parser("set-sla",
                                           help="Set the system sla",
                                           parents=[set_options])
    set_sla_parser.set_defaults(prop_name="service_level_agreement")

    unset_sla_parser = subparsers.add_parser("unset-sla",
                                             help="Clear set sla",
                                             parents=[unset_options])
    unset_sla_parser.set_defaults(prop_name="service_level_agreement")

    # USAGE ##############
    set_usage_parser = subparsers.add_parser("set-usage",
                                           help="Set the system usage",
                                           parents=[set_options])

    set_usage_parser.set_defaults(prop_name="usage_type")

    unset_usage_parser = subparsers.add_parser("unset-usage",
                                             help="Clear set usage/",
                                             parents=[unset_options])
    unset_usage_parser.set_defaults(prop_name="usage_type")

    # Pretty Print Json contents of default intent file
    show_parser = subparsers.add_parser("show",
                                        help="Show the current system intent")
    show_parser.set_defaults(func=show_contents, requires_write=False)

    return parser


def main():
    """
    Run the cli (Do the intentctl tool thing!!)
    :return: 0
    """
    parser = setup_arg_parser()
    args = parser.parse_args()

    # Intent is not intended to be used in containers for the time being (could change later).
    if in_container():
        print("WARNING: Setting intent in containers has no effect. Please run intentctl on the host.\n")

    intentstore = IntentStore.read(USER_INTENT)

    if args.func is not None:
        args.func(args, intentstore)
    else:
        parser.print_usage()

    if args.requires_write:
        intentstore.write()
    return 0
