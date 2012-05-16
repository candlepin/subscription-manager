import unittest

from subscription_manager.i18n import configure_i18n


class TestI18N(unittest.TestCase):
    def test_configure_i18n_without_glade(self):
        configure_i18n()

    def test_configure_i18n_with_glade(self):
        configure_i18n(with_glade=True)
