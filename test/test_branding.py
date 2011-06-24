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


import unittest

from subscription_manager.branding import Branding
#from subscription_manager.managerlib import configure_i18n


class TestBranding(object):

    def __init__(self):
        self.CLI_REGISTER = "register with awesomeness"


class BrandingTests(unittest.TestCase):

    def test_default_branding(self):
        branding = Branding()

        self.assertEquals("Register the machine to the server",
                branding.CLI_REGISTER)

    # XXX this test requires the mo files installed
#    def test_default_branding_with_i18n(self):
#        os.environ['LANG'] = "de_DE"
#        configure_i18n()
#        branding = Branding()
#
#        self.assertEquals("Client bei RHN registrieren",
#            branding.CLI_REGISTER)
#
#        os.environ['LANG'] = ""
#        configure_i18n()

    def test_override_defaults(self):
        custom_branding = TestBranding()
        branding = Branding(custom_branding)

        self.assertEquals("register with awesomeness", branding.CLI_REGISTER)

    def test_override_missing_key_falls_back(self):
        custom_branding = TestBranding()
        branding = Branding(custom_branding)

        self.assertEquals("Unregister the machine from the server",
                branding.CLI_UNREGISTER)
