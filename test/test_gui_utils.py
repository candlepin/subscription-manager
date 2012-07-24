import unittest

import gtk

# we need gtk 2.18+ to do the right markup in likify
MIN_GTK_MAJOR = 2
MIN_GTK_MINOR = 18
MIN_GTK_MICRO = 0

import rhsm_display
rhsm_display.set_display()

from subscription_manager.gui import utils


class TestLinkify(unittest.TestCase):
    no_url = "this does not have a url"
    https_url = "https://www.redhat.com"
    http_url = "http://www.redhat.com"
    expected_http_url = """<a href="%s">%s</a>""" % (http_url, http_url)
    expected_https_url = """<a href="%s">%s</a>""" % (https_url, https_url)

    http_url_dash = "http://example.com/something-foo/blah_something/"
    expected_http_url_dash = """<a href="%s">%s</a>""" % (http_url_dash, http_url_dash)

    nested_space = """<small>http://www.redhat.com </small>"""
    nested = """<small>http://www.redhat.com</small>"""
    expected_nested = """<small><a href="%s">%s</a></small>""" % (http_url, http_url)
    expected_nested_space = """<small><a href="%s">%s</a> </small>""" % (http_url, http_url)

    example_1 = """https://access.redhat.com/kb/docs/DOC-45563"""
    example_2 = """https://www.redhat.com/wapps/sso/rhn/lostPassword.html"""
    expected_example_1 = """<a href="%s">%s</a>""" % (example_1, example_1)
    expected_example_2 = """<a href="%s">%s</a>""" % (example_2, example_2)

    if gtk.check_version(MIN_GTK_MAJOR, MIN_GTK_MINOR, MIN_GTK_MICRO):
        __test__ = False

    def test_no_url(self):
        ret = utils.linkify(self.no_url)
        self.assertEquals(ret, self.no_url)

    def test_https_url(self):
        ret = utils.linkify(self.https_url)
        self.assertEquals(ret, self.expected_https_url)

    def test_http_url(self):
        ret = utils.linkify(self.http_url)
        self.assertEquals(ret, self.expected_http_url)

    def test_http_nested_space(self):
        ret = utils.linkify(self.nested_space)
        self.assertEquals(ret, self.expected_nested_space)

    def test_nested(self):
        ret = utils.linkify(self.nested)
        self.assertEquals(ret, self.expected_nested)

    def test_dash(self):
        ret = utils.linkify(self.http_url_dash)
        self.assertEquals(ret, self.expected_http_url_dash)

    def test_example_1(self):
        ret = utils.linkify(self.example_1)
        self.assertEquals(ret, self.expected_example_1)

    def test_example_2(self):
        ret = utils.linkify(self.example_2)
        self.assertEquals(ret, self.expected_example_2)
