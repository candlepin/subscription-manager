from __future__ import print_function, division, absolute_import

from nose.plugins.attrib import attr
from mock import patch

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import codecs
import glob
import os

from subscription_manager.i18n import configure_i18n
from subscription_manager.unicode_width import textual_width


class TestI18N(unittest.TestCase):
    def test_configure_i18n(self):
        configure_i18n()

    # Long running test, requires python-kitchen to run
    # determines if python-kitchen replacement gives the
    # same result
    @attr('functional')
    def test_text_width(self):
        from kitchen.text.display import textual_width as kitchen_textual_width
        for po_file in glob.glob('po/*.po'):
            with codecs.open(po_file, 'r', encoding='utf-8') as translation_file:
                for number, line in enumerate(translation_file.readlines(), 1):
                    expected = kitchen_textual_width(line)
                    actual = textual_width(line)
                    self.assertEqual(actual, expected, msg='mismatch on line {} of file {}, {} vs. {}'.format(
                         number, po_file, expected, actual
                    ))

    @patch('subscription_manager.i18n.Locale')
    def test_configure_i18n_lang(self, locale):
        """
        Ensure the method i18n does not pass a None from the environment to Locale
        :return:
        """
        new_lang = 'en-US.UTF-8'

        with patch.dict(os.environ, {'LANG': new_lang}):
            try:
                configure_i18n()
            except:
                self.fail()

        locale.set.assert_called_with(new_lang)

    @patch('subscription_manager.i18n.Locale')
    def test_configure_i18n_lang_none(self, locale):
        """
        Ensure the method i18n does not pass a None from the environment to Locale
        :return:
        """
        with patch.dict(os.environ, clear=True):
            try:
                configure_i18n()
            except:
                self.fail()

        locale.set.assert_not_called()
