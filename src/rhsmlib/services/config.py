from __future__ import print_function, division, absolute_import

# Copyright (c) 2016 Red Hat, Inc.
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
import rhsm.config
import collections
import six


class Config(collections.MutableMapping):
    def __init__(self, parser=None, auto_persist=False):
        if parser:
            self._parser = parser
        else:
            self._parser = rhsm.config.initConfig()

        self.auto_persist = auto_persist

        self._sections = {}
        for s in self._parser.sections():
            self._sections[s] = ConfigSection(self, self._parser, s, self.auto_persist)
        super(Config, self).__init__()

    def persist(self):
        self._parser.save()

    def defaults(self):
        return self._parser.defaults()

    def __getitem__(self, name):
        if name in self:
            return self._sections[name]
        raise KeyError("No configuration section '%s' exists" % name)

    def __setitem__(self, key, value):
        try:
            six.iteritems(value)
        except Exception:
            raise

        if key in self:
            # Similar to __delitem__ but with no persistence
            self._parser.remove_section(key)
            # Be aware that RhsmConfigParser is very diligent about keeping
            # default values in the configuration.  Deleting the section will result
            # in all the section's values being reset to the defaults.
            del self._sections[key]

        self._parser.add_section(key)
        self._sections[key] = ConfigSection(self, self._parser, key, self.auto_persist)

        for k, v in six.iteritems(value):
            self._sections[key][k] = v

        if self.auto_persist:
            self.persist()

    def __delitem__(self, key):
        self._parser.remove_section(key)
        del self._sections[key]
        if self.auto_persist:
            self.persist()

    def __contains__(self, key):
        return key in self._sections

    def __iter__(self):
        return iter(self._parser.sections())

    def iter_sections(self):
        """An iterator that yields the actual ConfigSection objects instead of just
        the names of the sections."""
        for s in self._parser.sections():
            yield self[s]

    def __len__(self):
        return len(self._parser.sections())

    def __repr__(self):
        result = {}
        for name, s in list(self._sections.items()):
            result[name] = repr(s)
        return "%s" % result


class ConfigSection(collections.MutableMapping):
    def __init__(self, wrapper, parser, section, auto_persist=False):
        self._wrapper = wrapper
        self._parser = parser
        self._section = section
        self.auto_persist = auto_persist

    def __iter__(self):
        return iter(self._parser.options(self._section))

    def __getitem__(self, key):
        if key in self:
            return self._parser.get(self._section, key)
        raise KeyError("Property '%s' does not exist in section '%s'" % (key, self._section))

    def __setitem__(self, key, value):
        self._parser.set(self._section, key, value)
        if self.auto_persist:
            self._wrapper.persist()

    def __delitem__(self, key):
        if key in self:
            self._parser.remove_option(self._section, key)
            if self.auto_persist:
                self._persist()
        else:
            raise KeyError("Property '%s' does not exist in section '%s'" % (key, self._section))

    def __contains__(self, key):
        return self._parser.has_option(self._section, key)

    def __len__(self):
        return len(self._parser.options(self._section))

    def _persist(self):
        self._wrapper.persist()

    def __repr__(self):
        return "%s" % self._parser.items(self._section)

    def get_int(self, key):
        return self._parser.get_int(self._section, key)

    def get_default(self, key):
        return self._parser.get_default(self._section, key)

    def has_default(self, key):
        return self._parser.has_default(self._section, key)
