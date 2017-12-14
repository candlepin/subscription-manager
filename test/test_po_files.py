from __future__ import print_function, division, absolute_import

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from . import fixture
import six

from subscription_manager import managercli
from subscription_manager.printing_utils import to_unicode_or_bust

import gettext
from subscription_manager import i18n
_ = gettext.translation(i18n.APP, fallback=True).ugettext


class TestLocale(unittest.TestCase):

    # see http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
    # http://docs.redhat.com/docs/en-US/Red_Hat_Enterprise_Linux/5/html/International_Language_Support_Guide/Red_Hat_Enterprise_Linux_International_Language_Support_Guide-Installing_and_supporting_languages.html
    test_locales = [
        # as_IN is kind of busted in RHEL6, and seemingly
        # very busted in 14
        #"as_IN",   # Assamese
        "bn_IN",  # Bengali
        "de_DE",  # German
        "es_ES",  # Spanish
        "en_US",  # english us
        "fr_FR",  # French
        "gu_IN",  # Gujarati
        "hi_IN",  # Hindi
        "it_IT",  # Italian
        "ja_JP",  # Japanese
        "kn_IN",  # Kannada
        "ml_IN",  # Malayalam
        "mr_IN",  # Marathi
        "or_IN",  # Oriya
        "pa_IN",  # Punjabi
        # "ne_IN",  # Nepali
        #"se_IN", # Sinhala
        #"br_IN", # Maithili
        "pt_BR",  # Portugese
        "ru_RU",  # Russian
        #"si_LK",   # Sri Lankan
        "ta_IN",  # Tamil
        "te_IN",  # telgu
        "zh_CN",  # Chinese Simplified
        "zh_TW",  # Chinese Traditional
        "ko_KR"]  # korean

    def test_pos(self):
        for lang in self.test_locales:
            l = "%s.utf8" % lang
            with fixture.locale_context(l):
                '%s' % _("Unable to find available subscriptions for all your installed products.")


class TestUnicodeGettext(TestLocale):
    def test_ja_not_serial(self):
        with fixture.locale_context('ja_JP.UTF-8'):
            msg = _("'%s' is not a valid serial number") % "123123"
            six.text_type(to_unicode_or_bust(msg)) + u'\n'

    def test_system_exit(self):
        with fixture.locale_context('ja_JP.UTF-8'):
            try:
                with fixture.Capture(silent=True):
                    managercli.system_exit(1, _("'%s' is not a valid serial number") % "123123")
            except SystemExit:
                # tis okay, we are looking for unicode errors on the string encode
                pass
