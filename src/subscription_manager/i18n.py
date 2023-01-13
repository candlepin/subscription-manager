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

# Localization domain:
from typing import Optional, Tuple

APP = "rhsm"
# Directory where translations are deployed:
DIR = "/usr/share/locale/"

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
    # Setup the localization framework
    try:
        locale.setlocale(category=locale.LC_ALL, locale="")
    except locale.Error:
        # We end up with a locale.Error when the language code that the user
        # used is not supported by the OS.  The language code might be valid
        # but the system hasn't been configured to use it, for example.  (You
        # can check which languages the system has been configured to use by
        # running `locale -a`)

        os.environ["LC_ALL"] = "C.UTF-8"
        locale.setlocale(category=locale.LC_ALL, locale="")

    # We used LC_ALL in the setup phase to set all the categories but here we
    # specifically retrieve the information for LC_MESSAGES.  LC_ALL returns
    # a string which is formatted to display all of the localization settings
    # but we only want the string which specifies the language code
    # to use for translations.
    lang = locale.setlocale(category=locale.LC_MESSAGES, locale=None)
    configure_gettext()
    Locale.set(lang)


def configure_gettext() -> None:
    """Configure gettext for all RHSM-related code.

    We needed to use the C-level bindings in locale to adjust the encoding
    when we used glade. We don't use glade anymore but
    bind_textdomain_codeset() should be a minor optimization (since the
    catalog and the output are both UTF-8, this avoids converting it
    unnecessarily) so we keep it for now.

    See https://docs.python.org/2/library/locale.html#access-to-message-catalogs
    """
    gettext.bindtextdomain(APP, DIR)
    gettext.textdomain(APP)
    locale.bind_textdomain_codeset(APP, "UTF-8")


def ugettext(*args, **kwargs) -> str:
    if hasattr(LOCALE, "lang") and LOCALE.lang is not None:
        return LOCALE.lang.gettext(*args, **kwargs)
    else:
        return TRANSLATION.gettext(*args, **kwargs)


def ungettext(*args, **kwargs) -> str:
    if hasattr(LOCALE, "lang") and LOCALE.lang is not None:
        return LOCALE.lang.ngettext(*args, **kwargs)
    else:
        return TRANSLATION.ngettext(*args, **kwargs)


class Locale:
    """
    Class used for changing languages on the fly
    """

    translations = {}

    @classmethod
    def is_locale_supported(cls, language: str) -> bool:
        """
        Is translation for given locale supported?
        :param language: String with locale code e.g. de_DE, de_DE.UTF-8
        """
        lang: Optional[gettext.GNUTranslations]
        try:
            lang = gettext.translation(APP, DIR, languages=[language])
        except IOError:
            lang, language = cls._find_lang_alternative(language)

        if lang is not None:
            return True
        else:
            return False

    @classmethod
    def _find_lang_alternative(cls, language: str) -> Tuple[gettext.GNUTranslations, Optional[str]]:
        """
        Try to find alternative for given language
        :param language: string with code of language e.g. de_LU
        :return: Instance of gettext.translation and code of new_language
        """
        lang: Optional[gettext.GNUTranslations] = None
        new_language: Optional[str] = None
        # For similar case: 'de'
        if "_" not in language:
            new_language = language + "_" + language.upper()
        # For similar cases: 'de_AT' (Austria), 'de_LU' (Luxembourg)
        elif language[0:2] != language[3:5]:
            new_language = language[0:2] + "_" + language[0:2].upper() + language[5:]
        if new_language is not None:
            try:
                lang = gettext.translation(APP, DIR, languages=[new_language])
            except IOError as err:
                log.info("Could not import locale either for %s: %s" % (new_language, err))
                new_language = None
            else:
                log.debug("Using new locale for language: %s" % new_language)
                cls.translations[language] = lang
        return lang, new_language

    @classmethod
    def set(cls, language: str) -> None:
        """
        Set language used by gettext and ungettext method. This method is
        intended for changing language on the fly, because rhsm service can
        be used by many users with different language preferences at the
        same time.
        :param language: String representing locale
                (e.g. de, de_DE, de_DE.utf-8, de_DE.UTF-8)
        """
        global LOCALE
        lang: gettext.GNUTranslations = None

        if language != "":
            if language in cls.translations.keys():
                log.debug("Reusing locale for language: %s" % language)
                lang = cls.translations[language]
            else:
                # Try to find given language
                try:
                    log.debug("Trying to use locale: %s" % language)
                    lang = gettext.translation(APP, DIR, languages=[language])
                except IOError as err:
                    log.info("Could not import locale for %s: %s" % (language, err))
                    # When original language was not found, then we will try another
                    # alternatives.
                    lang, language = cls._find_lang_alternative(language)
                else:
                    log.debug("Using new locale for language: %s" % language)
                    cls.translations[language] = lang

        LOCALE.language = language
        LOCALE.lang = lang
