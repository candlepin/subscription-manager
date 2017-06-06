from __future__ import print_function, division, absolute_import

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
import gettext
import locale

import six

# Localization domain:
APP = 'rhsm'
# Directory where translations are deployed:
DIR = '/usr/share/locale/'


def configure_i18n():
    """
    Configure internationalization for the application. Should only be
    called once per invocation. (once for CLI, once for GUI)
    """
    import locale
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, 'C')
    configure_gettext()


def configure_gettext():
    """Configure gettext for all RHSM-related code.

    Since Glade internally uses gettext, we need to use the C-level bindings in locale to adjust the encoding.

    See https://docs.python.org/2/library/locale.html#access-to-message-catalogs

    Exposed as its own function so that it can be called safely in the initial-setup case.
    """
    gettext.bindtextdomain(APP, DIR)
    gettext.textdomain(APP)
    gettext.bind_textdomain_codeset(APP, 'UTF-8')
    locale.bind_textdomain_codeset(APP, 'UTF-8')

translation = gettext.translation(APP, fallback=True)
if six.PY3:  # gettext returns unicode in Python 3
    ugettext = translation.gettext
    ungettext = translation.ngettext
else:
    ugettext = translation.ugettext
    ungettext = translation.ungettext
