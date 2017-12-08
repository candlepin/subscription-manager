# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import six

from subscription_manager import i18n_optparse


class TestWrappedIndentedHelpFormatter(unittest.TestCase):
    def setUp(self):
        self.hf = i18n_optparse.WrappedIndentedHelpFormatter(width=50)
        self.parser = i18n_optparse.OptionParser(description=u"test", formatter=self.hf)
        self.parser.add_option(u"-t", u"--test", dest=u"test",
                               default=None,
                               help=u"このシステム用に権利があるレポジトリの一覧表示このシステム用に権利があるレポジトリの一覧表示")

    def test_format_option(self):
        # use the new formatter, check for a result that we can decode to utf
        fh = self.parser.format_option_help(self.hf)
        self.assertIsInstance(fh, six.text_type)

    def test_format_usage(self):
        # optparses default format_usage uses lower cases
        # usage on 2.4, upper case on 2.6. We include our
        # own for consistency
        fu = self.hf.format_usage("%%prog [OPTIONS]")
        self.assertEqual(fu[:6], "Usage:")
