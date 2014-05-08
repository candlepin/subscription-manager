
from rhsm import config

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


class RepoFileConfigParser(KeyFileConfigParser):
    pass


class OriginFileConfigParser(KeyFileConfigParser):
    pass


class OstreeConfigFile(object):
    config_parser_class = KeyFileConfigParser

    def __init__(self, filename=None):
        self.filename = filename
        self.config_parser = self._get_config_parser()

    def _get_config_parser(self):
        return self.config_parser_class(config_file=self.filename)


class RepoFile(OstreeConfigFile):
    config_parser_class = RepoFileConfigParser

    def remote_sections(self):
        """Return all the config sections for "remotes"."""
        # flatten to comprehension
        remotes = []
        for section in self.config_parser.sections():
            if self.section_is_remote(section):
                remotes.append(section)
        return remotes

    def section_is_remote(self, section):
        if section.startswith("remote"):
            return True


class OriginFile(object):
    config_parser_class = OriginFileConfigParser
