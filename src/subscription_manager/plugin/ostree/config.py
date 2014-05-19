#
# Copyright (c) 2014 Red Hat, Inc.
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
import re

from rhsm import config

log = logging.getLogger("rhsm-app." + __name__)

"""Ostree has two config files, both based on the freedesktop.org
Desktop Entry spec. This defines a file format based on "ini" style
config files. Ostree refers to these as "key files".

One config file is the "repo" config, that defines some
core config options, and the ostree "remotes".

The other is an "origin" file that includes a refspec
for a given ostree sha.

We base the config parser on rhsm.config.RhsmConfigParser,
except with "defaults" support removed.

We has a KeyFileConfigParser, and two subclasses of it
for RepoFileConfigParser and OriginFileConfigParser.

There is also a OstreeConfigFile, and two subsclasses of
it for RepoFile, and OriginFile. These add some file type
specific helper functions.

OriginFile has a OriginFileConfigParser.
RepoFile has a RepoFileConfigParser, but adds methods for
dealing with all of the remote sections.
"""


# KeyFile is the desktop.org name for ini files, more or less
class KeyFileConfigParser(config.RhsmConfigParser):
    """A ini/ConfigParser subclass based on RhsmConfigParser.

    This impl removes the RhsmConfigParser support for rhsm.config.DEFAULTS.
    We don't neeed them.
    """

    # TODO: split RhsmConfigParser into a base version with useful stuff
    #       like save(), but without the rhsm specific DEFAULTS

    # neuter the rhsm.config module level DEFAULTS
    # If we don't override defaults, sections, items, and has_default
    # the class returns the module level DEFAULTS. We don't want that,
    # but we also don't want to monkeypatch our config module.
    #
    # why? useful convience methods on RhsmConfigParser
    # why not pyxdg xdg.IniFile? woudl still have to add type casts
    # why noy pyxdg xdg.DesktopEntry?  the repo configs are not actually
    #    desktop files, just that format, so that class throws exceptions
    #    in that case.
    def defaults(self):
        return {}

    def sections(self):
        # we want to by pass the parent class, and use the base class
        # section, but that's super weird, and it's just this, so c&p. sigh
        return list(self.data)

    def items(self, section):
        result = {}
        if self.has_section(section):
            super_result = super(KeyFileConfigParser, self).options(section)
            for key in super_result:
                result[key] = self.get(section, key)
        return result.items()

    def has_default(self, section, prop):
        return False

    def save(self, config_file=None):
        self.log_contents()
        log.debug("KeyFile.save %s" % self.config_file)
        super(KeyFileConfigParser, self).save()

    def log_contents(self):
        for section in self.sections():
            log.debug("section: %s" % section)
            for key, value in self.items(section):
                log.debug("     %s: %s" % (key, value))


def replace_refspec_remote(refspec, new_remote):
    """
    Replaces the 'remote' portion of an ostree origin file refspec.
    """
    refspec_regex = "(.*):(.*)"
    m = re.search(refspec_regex, refspec)
    if not m:
        raise Exception("Unable to parse refspec: %s" % refspec)
    return "%s:%s" % (new_remote, m.group(2))


class BaseOstreeConfigFile(object):
    config_parser_class = KeyFileConfigParser

    def __init__(self, filename=None):
        self.filename = filename
        self.config_parser = self._get_config_parser()

    def _get_config_parser(self):
        return self.config_parser_class(config_file=self.filename)

    def save(self):
        log.debug("OstreeConfigFile.save")
        self.config_parser.save()


class RepoFile(BaseOstreeConfigFile):
    """Ostree repo config file specific OstreeConfigFile implementation.

    Knows how to get the list of 'remote' sections, and how to determine
    if a config parser section is a remote.
    """
    config_parser_class = KeyFileConfigParser

    def remote_sections(self):
        """Return all the config sections for "remotes".

        Note: this returns a list of section name strings, not
              OstreeRemotes
        """
        # flatten to comprehension
        remotes = []
        for section in self.config_parser.sections():
            if self.section_is_remote(section):
                remotes.append(section)
        return remotes

    def section_is_remote(self, section):
        """Determine if a config section represents a ostree remote.

        For example, the section named 'remote "awesomeos-ostree-1"' is a remote.
        """
        if section.startswith("remote"):
            return True

    def clear_remotes(self):
        """Remove all the config sections for remotes."""

        # Not sure why, but saving config files we munge introduces
        # unneeded whitespace changes, I suspect it's related to this.
        for remote in self.remote_sections():
            # do we need to delete options and section or just section?
            for key, value in self.config_parser.items(remote):
                self.config_parser.remove_option(remote, key)
            self.config_parser.remove_section(remote)

    def set(self, section, key, value):
        return self.config_parser.set(section, key, value)

    # TODO: this is really just serializing OstreeRemote
    def set_remote(self, ostree_remote):
        """Add a remote section to config file based on a OstreeRemote."""
        # format section name
        # remote attribute -> section key
        section_name = 'remote ' + '"%s"' % ostree_remote.name
        self.set(section_name, 'url', ostree_remote.url)
        #self.set(section_name, 'gpg_verify', ostree_remote.gpg_verify)
        # add gpg_verify and other things

    # TODO: make a serializer of OstreeCore
    def set_core(self, ostree_core):
        # FIXME: shouldn't care about particular values unless we
        # know we have to munge them

        # Assuming we don't need to check validy of any [core] values
        # update the core section with the current values
        for key in ostree_core:
            self.set('core', key, ostree_core.get(key))

    def get_core(self):
        return self.config_parser.items('core')


class OriginFile(object):
    config_parser_class = KeyFileConfigParser
