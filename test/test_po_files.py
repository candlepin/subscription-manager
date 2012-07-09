import os
import glob
import unittest
import datetime
import sys
import time

# easy_install polib http://polib.readthedocs.org/
import polib

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


class PotFile:
    def __init__(self):

        self.msgids = []
        PO_PATH = "po/"
        pot_file = "%s/keys.pot" % PO_PATH
        po = polib.pofile(pot_file)
        for entry in po:
            self.msgids.append(entry.msgid)

        self.msgids.sort()


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
        "si_LK",   # Sri Lankan
        "ta_IN",  # Tamil
        "te_IN",  # telgu
        "zh_CN",  # Chinese Simplified
        "zh_TW",  # Chinese Traditional
        "ko_KR"]  # korean

    def _setupLang(self, lang):
        os.environ['LANG'] = lang
        locale.setlocale(locale.LC_ALL, '')
        gettext.bindtextdomain(APP, DIR)


class TestLocaleDate(TestLocale):

    def tearDown(self):
        self._setupLang("en_US")

    # FIXME
    # we work around this dynamicaly in managergui.py, but this
    # is here to see if we get anything new, or if the known
    # busted start working

    def test_strftime_1_1_2012(self):
        # yeah, this is weird. parsing the localized date format
        # for ja_JP and ko_KR fails in double digit months (10,11,12) even
        # though it seems to use a zero padded month field.
        # wibbly wobbly timey wimey
        self.known_busted = ["or_IN.UTF-8"]
        self.__test_strftime(datetime.date(2012, 1, 1))

    def test_strftime_10_30_2011(self):
        # zh_CN filed as https://bugzilla.redhat.com/show_bug.cgi?id=838647
        self.known_busted = ["zh_CN.UTF-8", "or_IN.UTF-8", "ja_JP.UTF-8", "ko_KR.UTF-8"]
        self.__test_strftime(datetime.date(2011, 10, 30))

    def __test_strftime(self, dt):
        for test_locale in self.test_locales:
            lc = "%s.UTF-8" % test_locale
            self._setupLang(lc)
            try:
                time.strptime(dt.strftime("%x"), "%x")
            except ValueError:
                if lc not in self.known_busted:
                    raise
                continue
# The above fails on f17/rhel6.3, but not f16, so don't
# worry about the "no longer busted" test for now. We should
# probably dump '%x' stuff anyway and just use iso8601 date
#           if lc in self.known_busted:
#               self.fail("%s used to be busted, but works now" % test_locale)


# These are meant to catch bugs like bz #744536
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

    def test_systemExit(self):
        try:
            managercli.systemExit(1, _("'%s' is not a valid serial number") % "123123")
        except SystemExit:
            # tis okay, we are looking for unicode errors on the string encode
            pass

    def test_all_strings_all_langs(self):
        pot = PotFile()
        msgids = pot.msgids

        for lang in self.test_locales:
            self._setupLang(lang)
            for msgid in msgids:
                "%s" % gettext.gettext(msgid)


if __name__ == "__main__":
    po = PotFile()
