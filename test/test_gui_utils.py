import unittest


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

class TestAllowsMutliEntitlement(unittest.TestCase):

    def test_allows_when_yes(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("yes")
        self.assertTrue(utils.allows_multi_entitlement(pool))

    def test_allows_when_1(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("1")
        self.assertTrue(utils.allows_multi_entitlement(pool))

    def test_does_not_allow_when_no(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("no")
        self.assertFalse(utils.allows_multi_entitlement(pool))

    def test_does_not_allow_when_0(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("0")
        self.assertFalse(utils.allows_multi_entitlement(pool))

    def test_does_not_allow_when_not_set(self):
        pool = {"productAttributes": []}
        self.assertFalse(utils.allows_multi_entitlement(pool))

    def test_does_not_allow_when_empty_string(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("")
        self.assertFalse(utils.allows_multi_entitlement(pool))

    def test_does_not_allow_when_any_other_value(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("not_a_good_value")
        self.assertFalse(utils.allows_multi_entitlement(pool))

    def test_is_case_insensitive(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("YeS")
        self.assertTrue(utils.allows_multi_entitlement(pool))

        pool = self._create_pool_data_with_multi_entitlement_attribute("nO")
        self.assertFalse(utils.allows_multi_entitlement(pool))

    def _create_pool_data_with_multi_entitlement_attribute(self, value):
        return {"productAttributes": [{"name": "multi-entitlement", "value": value}]}
