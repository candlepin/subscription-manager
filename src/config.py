#
# This module has been originally modified and enhanced from Red Hat Update Agent's config module.
#
# Copyright (c) 2010 Red Hat, Inc.
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
import sys

import gettext
_ = gettext.gettext


DEFAULT_CONFIG_DIR = "/etc/rhsm"
DEFAULT_CONFIG_PATH = "%s/rhsm.conf" % DEFAULT_CONFIG_DIR


class ConfigFile:
    "class for handling persistent config options for the client"

    def __init__(self, filename=None):
        self.dict = {}
        self.fileName = filename
        if self.fileName:
            self.load()

    def load(self, filename=None):
        if filename:
            self.fileName = filename
        if self.fileName == None:
            return
        if not os.access(self.fileName, os.R_OK):
#            print "warning: can't access %s" % self.fileName
            return

        f = open(self.fileName, "r")

        for line in f.readlines():
            # strip comments
            if '#' in line:
                line = line[:line.find('#')]
            line = line.strip()
            if not line:
                continue

            split = line.split('=', 1)
            if len(split) != 2:
                # not in 'a = b' format. we should log this
                # or maybe error.
                continue
            key = split[0].strip()
            value = split[1].strip()

            # decode a comment line
            comment = None
            pos = key.find("#")
            if pos != -1:
                key = key[:pos]
                comment = value
                value = None

            # figure out if we need to parse the value further
            if value:
                # possibly split value into a list
                values = value.split(";")
                if len(values) == 1:
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                elif values[0] == "":
                    value = []
                else:
                    value = values[:-1]

            # now insert the (comment, value) in the dictionary
            newval = (comment, value)
            if self.dict.has_key(key): # do we need to update
                newval = self.dict[key]
                if comment is not None: # override comment
                    newval = (comment, newval[1])
                if value is not None: # override value
                    newval = (newval[0], value)
            self.dict[key] = newval
        f.close()

    def save(self):
        if self.fileName == None:
            return

        if not os.access(self.fileName, os.R_OK):
            if not os.access(os.path.dirname(self.fileName), os.R_OK):
                print _("%s was not found" % os.path.dirname(self.fileName))
                return

        f = open(self.fileName, "w")
        os.chmod(self.fileName, 0600)

        f.write("# Red Hat Subscription Manager Configuration File")
        f.write("# Contents of this file will be overwritten on registration.")
        f.write("")
        for key in self.dict.keys():
            val = self.dict[key]
            f.write("%s[comment]=%s\n" % (key, val[0]))
            if type(val[1]) == type([]):
                f.write("%s=%s;\n" % (key, ';'.join(map(str, val[1]))))
            else:
                f.write("%s=%s\n" % (key, val[1]))
            f.write("\n")
        f.close()

    # dictionary interface
    def has_key(self, name):
        return self.dict.has_key(name)

    def keys(self):
        return self.dict.keys()

    def values(self):
        return map(lambda a: a[1], self.dict.values())

    def update(self, dict):
        self.dict.update(dict)

    def __getitem__(self, name):
        # we return None when we reference an invalid key instead of
        # raising an exception
        if self.dict.has_key(name):
            return self.dict[name][1]
        return None

    def __setitem__(self, name, value):
        if self.dict.has_key(name):
            val = self.dict[name]
        else:
            val = (None, None)
        self.dict[name] = (val[0], value)

    # we might need to expose the comments...
    def info(self, name):
        if self.dict.has_key(name):
            return self.dict[name][0]
        return ""


class Config:
    """
    a superclass for the ConfigFile that also handles runtime-only
    config values
    """

    def __init__(self, filename=None):
        self.stored = ConfigFile()
        #self.stored.update(Defaults)
        if filename:
            self.stored.load(filename)
        self.runtime = {}

    # classic dictionary interface: we prefer values from the runtime
    # dictionary over the ones from the stored config

    def has_key(self, name):
        if self.runtime.has_key(name):
            return True
        if self.stored.has_key(name):
            return True
        return False

    def keys(self):
        ret = self.runtime.keys()
        for k in self.stored.keys():
            if k not in ret:
                ret.append(k)
        return ret

    def values(self):
        ret = []
        for k in self.keys():
            ret.append(self.__getitem__(k))
        return ret

    def items(self):
        ret = []
        for k in self.keys():
            ret.append((k, self.__getitem__(k)))
        return ret

    def __len__(self):
        return len(self.keys())

    def __setitem__(self, name, value):
        self.runtime[name] = value

    # we return None when nothing is found instead of raising and exception
    def __getitem__(self, name):
        if self.runtime.has_key(name):
            return self.runtime[name]
        if self.stored.has_key(name):
            return self.stored[name]
        return None

    # These function expose access to the peristent storage for
    # updates and saves

    def info(self, name): # retrieve comments
        return self.stored.info(name)

    def save(self):
        self.stored.save()

    def load(self, filename):
        self.stored.load(filename)
        # make sure the runtime cache is not polluted
        for k in self.stored.keys():
            if not self.runtime.has_key(k):
                continue
            # allow this one to pass through
            del self.runtime[k]

    # save straight in the persistent storage
    def set(self, name, value):
        self.stored[name] = value
        # clean up the runtime cache
        if self.runtime.has_key(name):
            del self.runtime[name]


def initConfig(cfg_file=DEFAULT_CONFIG_PATH):
    global cfg
    try:
        cfg = cfg
    except NameError:
        cfg = None
    if cfg == None:
        cfg = Config(cfg_file)
    return cfg
