# -*- coding: utf-8 -*-

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
import logging
from threading import local

import os

import six

# Localization domain:
APP = 'rhsm'
# Directory where translations are deployed:
DIR = '/usr/share/locale/'

TRANSLATION = gettext.translation(APP, fallback=True)

# Save current language using thread safe approach
LOCALE = local()
LOCALE.language = None
LOCALE.lang = None

log = logging.getLogger(__name__)


def configure_i18n():
    """
    Configure internationalization for the application. Should only be
    called once per invocation. (once for CLI, once for GUI)
    """
    import locale
    current_locale = None
    try:
        current_locale = locale.setlocale(category=locale.LC_ALL, locale='')
    except locale.Error:
        # Following message could be little bit confusing. Why? When environment variable
        # LANG is set to e.g. es_ES.UTF-8, then we can show localized message for this language,
        # but this language could not be fully supported by the system. It means that en_ES is not
        # listed in the list of 'locale -a'
        _locale = None
        if 'LANG' in os.environ:
            _locale = os.environ['LANG']
        elif 'LC_ALL' in os.environ:
            _locale = os.environ['LC_ALL']
        if _locale is not None and Locale.is_locale_supported(_locale):
            print('You are attempting to use a locale: "%s" that is not fully supported by this system.' % _locale)
        os.environ['LC_ALL'] = 'C.UTF-8'
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')

    configure_gettext()
    # RHBZ 1642271  Don't set a None lang
    lang = os.environ.get("LANG")
    if lang is not None:
        Locale.set(lang)


def configure_gettext():
    """Configure gettext for all RHSM-related code.

    Since Glade internally uses gettext, we need to use the C-level bindings in locale to adjust the encoding.

    See https://docs.python.org/2/library/locale.html#access-to-message-catalogs
    """
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


class Locale(object):
    """
    Class used for changing languages on the fly
    """

    translations = {}

    @classmethod
    def is_locale_supported(cls, language):
        """
        Is translation for given locale supported?
        :param language: String with locale code e.g. de_DE, de_DE.UTF-8
        :return: True if the locale is supported by rhsm. Otherwise return False
        """
        try:
            lang = gettext.translation(APP, DIR, languages=[language])
        except IOError:
            lang, language = cls._find_lang_alternative(language)

        if lang is not None:
            return True
        else:
            return False

    @classmethod
    def _find_lang_alternative(cls, language):
        """
        Try to find alternative for given language
        :param language: string with code of language e.g. de_LU
        :return: Instance of gettext.translation and code of new_language
        """
        lang = None
        new_language = None
        # For similar case: 'de'
        if '_' not in language:
            new_language = language + '_' + language.upper()
        # For similar cases: 'de_AT' (Austria), 'de_LU' (Luxembourg)
        elif language[0:2] != language[3:5]:
            new_language = language[0:2] + '_' + language[0:2].upper() + language[5:]
        if new_language is not None:
            try:
                lang = gettext.translation(APP, DIR, languages=[new_language])
            except IOError as err:
                log.info('Could not import locale either for %s: %s' % (new_language, err))
                new_language = None
            else:
                log.debug('Using new locale for language: %s' % new_language)
                cls.translations[language] = lang
        return lang, new_language

    @classmethod
    def set(cls, language):
        """
        Set language used by gettext and ungettext method. This method is
        intended for changing language on the fly, because rhsm service can
        be used by many users with different language preferences at the
        same time.
        :param language: String representing locale
                (e.g. de, de_DE, de_DE.utf-8, de_DE.UTF-8)
        """
        global LOCALE
        lang = None

        if language != '':
            if language in cls.translations.keys():
                log.debug('Reusing locale for language: %s' % language)
                lang = cls.translations[language]
            else:
                # Try to find given language
                try:
                    log.debug('Trying to use locale: %s' % language)
                    lang = gettext.translation(APP, DIR, languages=[language])
                except IOError as err:
                    log.info('Could not import locale for %s: %s' % (language, err))
                    # When original language was not found, then we will try another
                    # alternatives.
                    lang, language = cls._find_lang_alternative(language)
                else:
                    log.debug('Using new locale for language: %s' % language)
                    cls.translations[language] = lang

        LOCALE.language = language
        LOCALE.lang = lang
