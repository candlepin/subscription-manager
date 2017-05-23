from __future__ import print_function, division, absolute_import

#
# branding - default localizable strings that can be overridden for app branding
#
# Copyright (c) 2011 Red Hat, Inc.
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

"""
Overrideable i18n friendly module for branding specific strings. To override
values, drop a python module called <your name>_branding.py into this
directory. The module should contains a Branding class, whose instances have
attributes matching the names of those on DefaultBranding for any values you
want to override.
"""
import glob
import os
import sys

from subscription_manager.i18n import ugettext as _

__all__ = ["get_branding"]

_branding = None


def find_custom_branding():
    mod_path = os.path.dirname(__file__)
    mods = glob.glob(mod_path + "/*_branding.*")
    if len(mods) == 0:
        return None
    # we don't support multiple brandings
    branding_module = os.path.basename(mods[0]).split('.')[0]
    __import__(__name__ + "." + branding_module)
    mod = sys.modules[__name__ + "." + branding_module]
    return mod.Branding()


def get_branding():
    global _branding
    if _branding is None:
        custom_branding = find_custom_branding()
        _branding = Branding(custom_branding)
    return _branding


class Branding(object):

    def __init__(self, custom_branding=None):
        self._default = DefaultBranding()
        if custom_branding is None:
            custom_branding = EmptyBranding()
        self._custom = custom_branding

    def __getattr__(self, x):
        if hasattr(self._custom, x):
            return getattr(self._custom, x)
        else:
            return getattr(self._default, x)


class DefaultBranding(object):

    """
    Default branding. values are defined in init to help with i18n/l10n
    ordering.
    """

    def __init__(self):
        self.CLI_REGISTER = _("Register the system to the server")
        self.CLI_UNREGISTER = _("Unregister the system from the server")
        self.RHSMD_REGISTERED_TO_OTHER = \
                _("This system is registered to spacewalk")
        self.REGISTERED_TO_OTHER_WARNING = _("WARNING") + \
            "\n" + \
            _("You have already registered with spacewalk.")

        self.GUI_REGISTRATION_HEADER = \
                _("Please enter your account information:")
        self.GUI_FORGOT_LOGIN_TIP = \
                _("Contact your system administrator if you have forgotten your login or password")


class EmptyBranding(object):
    """
    Empty branding object to use in place of a custom branding
    (so we always fall back to the defaults.
    """
    pass
