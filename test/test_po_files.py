import os
import glob
import unittest
import sys

import locale
import gettext
_ = gettext.gettext

#locale.setlocale(locale.LC_ALL, '')

from stubs import MockStderr
from stubs import MockStdout
from subscription_manager import managercli

# Localization domain:
APP = "rhsm"
# Directory where translations are deployed:
DIR = '/usr/share/locale/'
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)

po_files = glob.glob("po/*.po")
langs = []
for po_file in po_files:
    langs.append(po_file[:-3])


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

    def _setupLang(self, lang):
        os.environ['LANG'] = lang
        locale.setlocale(locale.LC_ALL, '')
        gettext.bindtextdomain(APP, DIR)


class TestUnicodeGettext(TestLocale):
    def setUp(self):
        self._setupLang("ja_JP.UTF-8")
        sys.stderr = MockStderr()
        sys.stdout = MockStdout()

    def tearDown(self):
        self._setupLang("en_US")
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def test_ja_not_serial(self):
        msg = _("'%s' is not a valid serial number") % "123123"
        unicode(managercli.to_unicode_or_bust(msg)).encode("UTF-8") + '\n'

    def test_system_exit(self):
        try:
            managercli.system_exit(1, _("'%s' is not a valid serial number") % "123123")
        except SystemExit:
            # tis okay, we are looking for unicode errors on the string encode
            pass
