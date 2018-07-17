from __future__ import print_function, division, absolute_import

# Copyright (c) 2018 Red Hat, Inc.
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
import gettext
import locale
from threading import local

import six

# Localization domain:
APP = 'syspurpose'
# Directory where translations are deployed:
DIR = '/usr/share/locale/'

TRANSLATION = gettext.translation(APP, fallback=True)

# Save current language using thread safe approach
LOCALE = local()
LOCALE.language = None
LOCALE.lang = None


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
    gettext.bindtextdomain(APP, DIR)
    gettext.textdomain(APP)
    gettext.bind_textdomain_codeset(APP, 'UTF-8')
    locale.bind_textdomain_codeset(APP, 'UTF-8')


def ugettext(*args, **kwargs):
    if six.PY2:
        if hasattr(LOCALE, 'lang') and LOCALE.lang is not None:
            return LOCALE.lang.ugettext(*args, **kwargs)
        else:
            return TRANSLATION.ugettext(*args, **kwargs)
    else:
        if hasattr(LOCALE, 'lang') and LOCALE.lang is not None:
            return LOCALE.lang.gettext(*args, **kwargs)
        else:
            return TRANSLATION.gettext(*args, **kwargs)


def ungettext(*args, **kwargs):
    if six.PY2:
        if hasattr(LOCALE, 'lang') and LOCALE.lang is not None:
            return LOCALE.lang.ungettext(*args, **kwargs)
        else:
            return TRANSLATION.ungettext(*args, **kwargs)
    else:
        if hasattr(LOCALE, 'lang') and LOCALE.lang is not None:
            return LOCALE.lang.ngettext(*args, **kwargs)
        else:
            return TRANSLATION.ngettext(*args, **kwargs)
