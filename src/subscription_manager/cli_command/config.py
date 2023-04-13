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
import os

import rhsm.config

from subscription_manager.cli import system_exit
from subscription_manager.cli_command.cli import CliCommand, conf
from subscription_manager.i18n import ugettext as _


class ConfigCommand(CliCommand):
    def __init__(self):
        shortdesc = _("List, set, or remove the configuration parameters in use by this system")
        super(ConfigCommand, self).__init__("config", shortdesc, False)

        self.parser.add_argument(
            "--list", action="store_true", help=_("list the configuration for this system")
        )
        self.parser.add_argument(
            "--remove", dest="remove", action="append", help=_("remove configuration entry by section.name")
        )
        for s in list(conf.keys()):
            section = conf[s]
            for name, _value in list(section.items()):
                # Allow adding CLI options only for sections and names listed in defaults
                if s in rhsm.config.DEFAULTS and name in rhsm.config.DEFAULTS[s]:
                    self.parser.add_argument(
                        "--" + s + "." + name,
                        dest=(s + "." + name),
                        help=_("Section: {s}, Name: {name}").format(s=s, name=name),
                    )

    def _validate_options(self):
        if self.options.list:
            too_many = False
            if self.options.remove:
                too_many = True
            else:
                for s in list(conf.keys()):
                    section = conf[s]
                    for name, _value in list(section.items()):
                        # Ignore sections and names that are not supported by subscription-manager
                        if hasattr(self.options, s + "." + name):
                            if getattr(self.options, s + "." + name):
                                too_many = True
                                break
                        else:
                            pass
            if too_many:
                system_exit(
                    os.EX_USAGE,
                    _(
                        "Error: --list should not be used with any other "
                        "options for setting or removing configurations."
                    ),
                )

        if not (self.options.list or self.options.remove):
            has = False
            for s in list(conf.keys()):
                section = conf[s]
                for name, _value in list(section.items()):
                    if hasattr(self.options, s + "." + name):
                        test = "{value}".format(value=getattr(self.options, s + "." + name))
                    else:
                        test = "None"
                    has = has or (test != "None")
            if not has:
                # if no options are given, default to --list
                self.options.list = True

        if self.options.remove:
            for r in self.options.remove:
                if "." not in r:
                    system_exit(
                        os.EX_USAGE,
                        _(
                            "Error: configuration entry designation for "
                            "removal must be of format [section.name]"
                        ),
                    )

                section = r.split(".")[0]
                name = r.split(".")[1]
                found = False
                if section in list(conf.keys()):
                    for key, _value in list(conf[section].items()):
                        if name == key:
                            found = True
                if not found:
                    system_exit(
                        os.EX_CONFIG,
                        _("Error: Section {section} and name {name} does not exist.").format(
                            section=section, name=name
                        ),
                    )

    def _do_command(self):
        self._validate_options()

        if self.options.list:
            for s in list(conf.keys()):
                section = conf[s]
                print("[{s}]".format(s=s))
                source_list = sorted(section.items())
                for name, value in source_list:
                    indicator1 = ""
                    indicator2 = ""
                    if value == section.get_default(name):
                        indicator1 = "["
                        indicator2 = "]"
                    print(
                        "   {name} = {indicator1}{value}{indicator2}".format(
                            name=name, indicator1=indicator1, value=value, indicator2=indicator2
                        )
                    )
                print()
            print(_("[] - Default value in use"))
            print("\n")
        elif self.options.remove:
            for r in self.options.remove:
                section = r.split(".")[0]
                name = r.split(".")[1]
                try:
                    if not conf[section].has_default(name):
                        conf[section][name] = ""
                        print(
                            _("You have removed the value for section {section} and name {name}.").format(
                                section=section, name=name
                            )
                        )
                    else:
                        conf[section][name] = conf[section].get_default(name)
                        print(
                            _("You have removed the value for section {section} and name {name}.").format(
                                section=section, name=name
                            )
                        )
                        print(_("The default value for {name} will now be used.").format(name=name))
                except Exception:
                    print(
                        _("Section {section} and name {name} cannot be removed.").format(
                            section=section, name=name
                        )
                    )
            conf.persist()
        else:
            for s in list(conf.keys()):
                section = conf[s]
                for name, value in list(section.items()):
                    if hasattr(self.options, s + "." + name):
                        value = "{name}".format(name=getattr(self.options, s + "." + name))
                        if not value == "None":
                            section[name] = value
            conf.persist()

    def require_connection(self):
        return False
