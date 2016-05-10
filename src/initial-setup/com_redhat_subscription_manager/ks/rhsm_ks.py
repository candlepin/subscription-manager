#
# Copyright (C) 2015  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
"""Module with the RHSM initial-setup class."""

import logging
import sys

from pyanaconda.addons import AddonData

log = logging.getLogger(__name__)

# Likely needs to be removed after relocation to site-packages
RHSM_PATH = "/usr/share/rhsm"
sys.path.append(RHSM_PATH)

# export RHSMAddonData class to prevent Anaconda's collect method from taking
# AddonData class instead of the RHSMAddonData class
# @see: pyanaconda.kickstart.AnacondaKSHandler.__init__
__all__ = ["RHSMAddonData"]


"""
# Sample ks file ideas

# all on the header
%addon com_redhat_subscription_manager --serverUrl=https://grimlock.usersys.redhat.com/candlepin --activationkey=SOMEKEY

%end

%addon com_redhat_subscription_manager
    # only one
    server-url = https://grimlock.usersys.redhat.com:8443/candlepin

    # can have many act keys. Does order matter?
    activation-key = SOMEKEY-1
    activation-key = SOMEKEY-2

    # If we should attempt to auto-attach
%end

NOTES:
# Add a version 'cli' so I can change the format later
%addon com_redhat_subscription_manager --ksversion=1.0

"""

# To test
# utf8 streams
# inlined base64 blobs (ie, cert pems)
# inline yum.repo
# if anything needs to match a value from a cert,
#  need to verify the encodings all work


class KickstartRhsmData(object):
    # A holder of rhsm info, that is not a gobject...
    def __init__(self):
        # TODO: make this a data class

        # Server config related
        self.serverurl = None
        # self.ca_certs = []
        # self.baseurl = []
        # self.proxy
        #    - proxy url
        #    - proxy auth
        #       - username
        #       - password, etc

        # identifying info
        self.username = None
        # Unsure if we should support this at all
        self.password = None

        self.org = None

        # Register behaviour
        self.auto_attach = True
        # self.force = False
        # self.type   # consumer type

        # Register options
        self.servicelevel = None
        self.activationkeys = []
        # self.environment
        # self.consumerid
        # self.name  (the consumer name, ie hostname)


class RHSMAddonData(AddonData):
    """This is a common parent class for loading and storing
       3rd party data to kickstart. It is instantiated by
       kickstart parser and stored as ksdata.addons.<name>
       to be used in the user interfaces.

       The mandatory method handle_line receives all lines
       from the corresponding addon section in kickstart and
       the mandatory __str__ implementation is responsible for
       returning the proper kickstart text (to be placed into
       the %addon section) back.

       There is also a mandatory method execute, which should
       make all the described changes to the installed system.
    """

    def __init__(self, name):
        AddonData.__init__(self, name)

        self.name = name
        self.content = ""
        self.header_args = ""

        self.rhsm_data = KickstartRhsmData()

        # TODO: make this a data class
        self.serverurl = None
        self.activationkeys = []
        self.auto_attach = True
        self.username = None
        # Unsure if we should support this at all
        self.password = None
        self.org = None
        self.servicelevel = []
        self.force = False

        self.arg_names = {}
        self.line_handlers = {'serverurl': self._parse_serverurl,
                              'activationkey': self._parse_activationkey,
                              'auto-attach': self._parse_auto_attach,
                              'username': self._parse_username,
                              'password': self._parse_password,
                              'servicelevel': self._parse_servicelevel,
                              'force': self._parse_force,
                              'org': self._parse_org}

    def __str__(self):
        return "%%addon %s %s\n%s%%end\n" % (self.name, self.header_args, self.content)

    def setup(self, storage, ksdata, instclass):
        """Make the changes to the install system.

           This method is called before the installation
           is started and directly from spokes. It must be possible
           to call it multiple times without breaking the environment."""
        AddonData.setup(self, storage, ksdata, instclass)

    def execute(self, storage, ksdata, instClass, users):

        """Make the changes to the underlying system.

           This method is called only once in the post-install
           setup phase.
        """
        log.debug("Read RHSM ks info, but non gui ks is currently not implemented.")

    def handle_header(self, lineno, args):
        """Process additional arguments to the %addon line.

           This function receives any arguments on the %addon line after the
           addon ID. For example, for the line:

               %addon com_example_foo --argument='example'

           This function would be called with args=["--argument='example'"].

           By default AddonData.handle_header just preserves the passed
           arguments by storing them and adding them to the __str__ output.

        """

        if args:
            self.header_args += " ".join(args)

    # TODO: verify this is consistent with other kickstart bool option handling
    def _bool(self, value):
        if value == 'true':
            return True
        return False

    # TODO
    # FIXME: move these to KickstartRhsmData

    def _parse_activationkey(self, value):
        self.activationkeys.append(value)

    # Allow multiple SLAs in order of preference
    def _parse_servicelevel(self, value):
        self.servicelevel.append(value)

    def _parse_auto_attach(self, value):
        self.auto_attach = self._bool(value)

    def _parse_force(self, value):
        self.force = self._bool(value)

    # TODO: these could all use a generic setter
    def _parse_org(self, value):
        self.org = value

    def _parse_username(self, value):
        self.username = value

    def _parse_password(self, value):
        self.password = value

    def _parse_serverurl(self, value):
        self.serverurl = value

    def handle_line(self, line):
        """Process one kickstart line."""
        self.content += line

        line = line.strip()
        (lhs, sep, rhs) = line.partition('=')
        lhs = lhs.strip()
        sep = sep.strip()
        # could trailing space be valid for a value?
        # raw_rhs = rhs[:]
        rhs = rhs.strip()
        rhs = rhs.strip('"')

        if lhs[0] == '#':
            return

        try:
            self.line_handlers[lhs](rhs)
        except KeyError:
            log.debug("Parse error, unknown RHSM addon ks cmd %s", lhs)

    def finalize(self):
        """No additional data will come.

           Addon should check if all mandatory attributes were populated.
        """
        pass
