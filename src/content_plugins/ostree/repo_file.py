
from rhsm import config


class RepoFileConfigParser(config.RhsmConfigParser):
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
            super_result = super(RepoFileConfigParser, self).options(section)
            for key in super_result:
                result[key] = self.get(section, key)
        return result.items()

    def has_default(self, section, prop):
        return False


class RepoFile(object):
    config_parser_class = RepoFileConfigParser

    def __init__(self, filename=None):
        self.filename = filename
        self.config_parser = self._get_config_parser()

    def _get_config_parser(self):
        return self.config_parser_class(config_file=self.filename)

    def remote_sections(self):
        # flatten to comprehension
        remotes = []
        for section in self.config_parser.sections():
            print section
            if self.section_is_remote(section):
                remotes.append(section)
        return remotes

    def section_is_remote(self, section):
        if section.startswith("remote"):
            return True


