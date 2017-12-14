from __future__ import print_function, division, absolute_import

from . import fixture
from . import stubs

from mock import Mock, patch
from rhsm.utils import ServerUrlParseErrorEmpty, \
    ServerUrlParseErrorNone, ServerUrlParseErrorPort, \
    ServerUrlParseErrorScheme, ServerUrlParseErrorJustScheme
from subscription_manager.utils import parse_server_info, \
    parse_baseurl_info, format_baseurl, \
    get_version, get_client_versions, unique_list_items, \
    get_server_versions, friendly_join, is_true_value, url_base_join,\
    ProductCertificateFilter, EntitlementCertificateFilter
from .stubs import StubProductCertificate, StubProduct, StubEntitlementCertificate
from .fixture import SubManFixture

from rhsm.config import DEFAULT_PORT, DEFAULT_PREFIX, DEFAULT_HOSTNAME, \
    DEFAULT_CDN_HOSTNAME, DEFAULT_CDN_PORT, DEFAULT_CDN_PREFIX

from rhsmlib.services import config


class TestParseServerInfo(SubManFixture):
    def setUp(self):
        SubManFixture.setUp(self)
        self.stubConfig = stubs.StubConfig()

    def test_fully_specified(self):
        local_url = "myhost.example.com:900/myapp"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("900", port)
        self.assertEqual("/myapp", prefix)

    def test_hostname_only(self):
        local_url = "myhost.example.com"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("443", port)
        self.assertEqual(DEFAULT_PREFIX, prefix)

    def test_hostname_port(self):
        local_url = "myhost.example.com:500"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("500", port)
        self.assertEqual(DEFAULT_PREFIX, prefix)

    def test_hostname_prefix(self):
        local_url = "myhost.example.com/myapp"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("443", port)
        self.assertEqual("/myapp", prefix)

    def test_hostname_only_config(self):
        self.stubConfig.set("server", "port", "344")
        self.stubConfig.set("server", "prefix", "/test-prefix")

        local_url = "myhost.example.com"
        (hostname, port, prefix) = parse_server_info(local_url, config.Config(self.stubConfig))
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("344", port)
        self.assertEqual("/test-prefix", prefix)

    def test_hostname_port_config(self):
        self.stubConfig.set("server", "port", "600")

        local_url = "myhost.example.com/myapp"
        (hostname, port, prefix) = parse_server_info(local_url, config.Config(self.stubConfig))
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("600", port)
        self.assertEqual("/myapp", prefix)

    def test_hostname_prefix_config(self):
        self.stubConfig.set("server", "prefix", "/test-prefix")

        local_url = "myhost.example.com:500"
        (hostname, port, prefix) = parse_server_info(local_url, config.Config(self.stubConfig))
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("500", port)
        self.assertEqual("/test-prefix", prefix)

    def test_hostname_slash_no_prefix(self):
        local_url = "http://myhost.example.com/"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("443", port)
        self.assertEqual("/", prefix)

    def test_hostname_just_slash(self):
        local_url = "/"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual(DEFAULT_HOSTNAME, hostname)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual("/", prefix)

    def test_hostname_nested_prefix(self):
        local_url = "myhost.example.com/myapp/subapp"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("443", port)
        self.assertEqual("/myapp/subapp", prefix)

    def test_hostname_nothing(self):
        local_url = ""
        self.assertRaises(ServerUrlParseErrorEmpty,
                          parse_server_info,
                          local_url)

    def test_hostname_none(self):
        local_url = None
        self.assertRaises(ServerUrlParseErrorNone,
                          parse_server_info,
                          local_url)

    def test_hostname_with_scheme(self):
        # this is the default, so test it here
        local_url = "https://subscription.rhsm.redhat.com/subscription"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("subscription.rhsm.redhat.com", hostname)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual("/subscription", prefix)

    def test_hostname_with_scheme_no_prefix(self):
        local_url = "https://myhost.example.com"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual("/subscription", prefix)

    def test_hostname_no_scheme_port_no_prefix(self):
        local_url = "myhost.example.com:8443"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("8443", port)
        self.assertEqual("/subscription", prefix)

    def test_just_prefix(self):
        local_url = "/myapp"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual(DEFAULT_HOSTNAME, hostname)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual("/myapp", prefix)

    def test_short_name(self):
        # could argue anything could be a local hostname, and we should
        # use default port and path. You could also argue it should
        # throw an error, especially if it's not a valid hostname
        local_url = "a"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("a", hostname)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual(DEFAULT_PREFIX, prefix)

    def test_wrong_scheme(self):
        local_url = "git://git.fedorahosted.org/candlepin.git"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    def test_bad_http_scheme(self):
        # note missing /
        local_url = "https:/myhost.example.com:8443/myapp"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    def test_colon_but_no_port(self):
        local_url = "https://myhost.example.com:/myapp"
        self.assertRaises(ServerUrlParseErrorPort,
                          parse_server_info,
                          local_url)

    def test_colon_but_no_port_no_scheme(self):
        local_url = "myhost.example.com:/myapp"
        self.assertRaises(ServerUrlParseErrorPort,
                          parse_server_info,
                          local_url)

    def test_colon_slash_slash_but_nothing_else(self):
        local_url = "http://"
        self.assertRaises(ServerUrlParseErrorJustScheme,
                          parse_server_info,
                          local_url)

    def test_colon_slash_but_nothing_else(self):
        local_url = "http:/"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    def test_colon_no_slash(self):
        local_url = "http:example.com/foobar"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    # Note: this means if you have a local server named
    # "http", and you like redundant slashes, this actually
    # valid url of http//path/to/something will fail.
    # Don't do that. (or just use a single slash like http/path)
    # But seriously, really?
    def test_no_colon_double_slash(self):
        local_url = "http//example.com/api"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    def test_https_no_colon_double_slash(self):
        local_url = "https//example.com/api"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    # fail at internet
    def test_just_colon_slash(self):
        local_url = "://"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    def test_one_slash(self):
        local_url = "http/example.com"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    def test_host_named_http(self):
        local_url = "http://http/prefix"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("http", hostname)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual('/prefix', prefix)

    def test_one_slash_port_prefix(self):
        local_url = "https/bogaddy:80/candlepin"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    def test_host_named_http_port_prefix(self):
        local_url = "https://https:8000/prefix"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEqual("https", hostname)
        self.assertEqual("8000", port)
        self.assertEqual('/prefix', prefix)

    def test_host_name_non_numeric_port(self):
        local_url = "https://example.com:https/prefix"
        self.assertRaises(ServerUrlParseErrorPort,
                          parse_server_info,
                          local_url)


# TestParseServerInfo pretty much covers this code wise
class TestParseBaseUrlInfo(fixture.SubManFixture):
    def test_hostname_with_scheme(self):
        # this is the default, so test it here
        local_url = "https://cdn.redhat.com"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEqual(DEFAULT_CDN_HOSTNAME, hostname)
        self.assertEqual(DEFAULT_CDN_PORT, port)
        self.assertEqual("/", prefix)

    def test_format_base_url(self):
        local_url = "https://cdn.redhat.com"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEqual(local_url, format_baseurl(hostname, port, prefix))

    def test_format_base_url_with_port(self):
        local_url = "https://cdn.redhat.com:443"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEqual(prefix, DEFAULT_CDN_PREFIX)
        self.assertEqual("https://cdn.redhat.com", format_baseurl(hostname, port, prefix))

    def test_format_thumbslug_url_with_port(self):
        local_url = "https://someserver.example.com:8088"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEqual(prefix, DEFAULT_CDN_PREFIX)
        self.assertEqual("https://someserver.example.com:8088", format_baseurl(hostname, port, prefix))

    def test_format_not_fqdn_with_port(self):
        local_url = "https://foo-bar:8088"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEqual(prefix, DEFAULT_CDN_PREFIX)
        self.assertEqual("https://foo-bar:8088", format_baseurl(hostname, port, prefix))


class TestUrlBaseJoinEmptyBase(fixture.SubManFixture):

    def test_blank_base_blank_url(self):
        self.assertEqual("",
                          url_base_join("", ""))

    def test_blank_base_url(self):
        url = "http://foo.notreal/"
        self.assertEqual(url,
                          url_base_join("", url))

    def test_blank_base_url_fragment(self):
        url = "baz"
        self.assertEqual(url,
                          url_base_join("", url))

# Not sure this makes sense.
#    def test_blank_base_url_fragment_slash(self):
#        url = "/baz"
#        self.assertEquals(url,
#                          url_base_join("", url))


class TestUrlBaseJoin(fixture.SubManFixture):
    base = "http://foo/bar"

    def test_file_url(self):
        # File urls should be preserved
        self.assertEqual("file://this/is/a/file",
            url_base_join(self.base, "file://this/is/a/file"))

    def test_http_url(self):
        # Http locations should be preserved
        self.assertEqual("http://this/is/a/url",
            url_base_join(self.base, "http://this/is/a/url"))

    def test_blank_url(self):
        # Blank should remain blank
        self.assertEqual("",
            url_base_join(self.base, ""))

    def test_url_fragments(self):
        # Url Fragments should work
        self.assertEqual(self.base + "/baz",
            url_base_join(self.base, "baz"))
        self.assertEqual(self.base + "/baz",
            url_base_join(self.base, "/baz"))

    def test_base_slash(self):
        base = self.base + '/'
        self.assertEqual(self.base + "/baz",
            url_base_join(base, "baz"))
        self.assertEqual(self.base + "/baz",
            url_base_join(base, "/baz"))


class TestUrlBaseJoinFileUrl(TestUrlBaseJoin):
    base = "file:///etc"


class TestUrlBaseJoinJustHttpScheme(TestUrlBaseJoin):
    base = "http://"


class TestUrlBaseJoinHttps(TestUrlBaseJoin):
    base = "https://somesecure.cdn.example.notreal"


class TestUrlBaseJoinHostname(TestUrlBaseJoin):
    base = "cdn.redhat.com"


class TestUrlBaseJoinDefaultCdn(TestUrlBaseJoin):
    base = "https://cdn.redhat.com"


NOT_COLLECTED = "non-collected-package"


class TestGetServerVersions(fixture.SubManFixture):

    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_classic(self, MockClassicCheck):
        self._inject_mock_invalid_consumer()
        instance = MockClassicCheck.return_value
        instance.is_registered_with_classic.return_value = True

        sv = get_server_versions(None)
        self.assertEqual(sv['server-type'], "RHN Classic")
        self.assertEqual(sv['candlepin'], "Unknown")

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_no_status(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = False
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = False
        sv = get_server_versions(MockUep)
        self.assertEqual(sv['server-type'], 'Red Hat Subscription Management')
        self.assertEqual(sv['candlepin'], "Unknown")

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_with_status(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = False
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = True
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c', 'rulesVersion': '6.1'}
        sv = get_server_versions(MockUep)
        self.assertEqual(sv['server-type'], 'Red Hat Subscription Management')
        self.assertEqual(sv['candlepin'], '101-23423c')
        self.assertEqual(sv['rules-version'], '6.1')

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_with_status_no_rules_version(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = False
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = True
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEqual(sv['server-type'], 'Red Hat Subscription Management')
        self.assertEqual(sv['candlepin'], '101-23423c')
        self.assertEqual(sv['rules-version'], 'Unknown')

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_with_status_no_keys(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = False
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = True
        MockUep.getStatus.return_value = {}
        sv = get_server_versions(MockUep)
        self.assertEqual(sv['server-type'], 'Red Hat Subscription Management')
        self.assertEqual(sv['candlepin'], 'Unknown-Unknown')
        self.assertEqual(sv['rules-version'], 'Unknown')

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_with_status_bad_data(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = False
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = True

        dataset = [
            {'version': None, 'release': '123'},
            {'version': 123, 'release': '123'},

            {'version': '123', 'release': None},
            {'version': '123', 'release': 123},

            {'version': None, 'release': None},
            {'version': None, 'release': 123},
            {'version': 123, 'release': None},
            {'version': 123, 'release': 123},
        ]

        for value in dataset:
            MockUep.getStatus.return_value = value
            sv = get_server_versions(MockUep)
            self.assertEqual(sv['server-type'], 'Red Hat Subscription Management')
            self.assertEqual(sv['candlepin'], 'Unknown')
            self.assertEqual(sv['rules-version'], 'Unknown')

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_with_status_and_classic(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = True
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = True
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c', 'rulesVersion': '6.1'}
        sv = get_server_versions(MockUep)
        self.assertEqual(sv['server-type'], 'RHN Classic and Red Hat Subscription Management')
        self.assertEqual(sv['candlepin'], '101-23423c')
        self.assertEqual(sv['rules-version'], '6.1')

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_exception(self, mock_classic, MockUep):
        def raise_exception(arg):
            raise Exception("boom")
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = False
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.side_effect = raise_exception
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEqual(sv['server-type'], "Red Hat Subscription Management")
        self.assertEqual(sv['candlepin'], "Unknown")

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_exception_and_classic(self, mock_classic, MockUep):
        def raise_exception(arg):
            raise Exception("boom")
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = True
        self._inject_mock_invalid_consumer()
        MockUep.supports_resource.side_effect = raise_exception
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEqual(sv['server-type'], "RHN Classic")
        self.assertEqual(sv['candlepin'], "Unknown")


class TestGetClientVersions(fixture.SubManFixture):
    @patch('subscription_manager.utils.subscription_manager.version')
    def test_get_client_versions(self, mock_sub_version):
        mock_sub_version.rpm_version = '9.8.7-6'
        cv = get_client_versions()
        self.assertEqual(cv['subscription-manager'], "9.8.7-6")
        self.assertTrue(isinstance(cv['subscription-manager'], str))

    @patch('subscription_manager.utils.subscription_manager.version')
    def test_get_client_versions_strings(self, mock_sub_version):
        mock_sub_version.rpm_version = 'ef-gh'
        cv = get_client_versions()
        self.assertEqual(cv['subscription-manager'], "ef-gh")


class TestGetVersion(fixture.SubManFixture):
    def test_version_and_release_present(self):
        versions = Mock()
        versions.get_version.return_value = "1.0"
        versions.get_release.return_value = "1"
        result = get_version(versions, "foobar")
        self.assertEqual("1.0-1", result)

    def test_version_no_release(self):
        versions = Mock()
        versions.get_version.return_value = "1.0"
        versions.get_release.return_value = ""
        result = get_version(versions, "foobar")
        self.assertEqual("1.0", result)


class TestFriendlyJoin(fixture.SubManFixture):

    def test_join(self):
        self.assertEqual("One", friendly_join(["One"]))
        self.assertEqual("One and Two", friendly_join(["One", "Two"]))
        self.assertEqual("One, Two, and Three", friendly_join(["One", "Two", "Three"]))
        self.assertEqual("", friendly_join([]))
        self.assertEqual("", friendly_join(None))
        self.assertEqual("", friendly_join(set()))
        self.assertEqual("One", friendly_join([None, "One"]))
        self.assertEqual("One", friendly_join(["One", None]))
        self.assertEqual("", friendly_join([None, None, None]))

        # We allow any iterable, so test a set created from a list with dupes
        words = set(["Two", "One", "Two", "Two"])
        res = friendly_join(words)
        self.assertTrue(res in ["One and Two", "Two and One"])

        self.assertEqual("1, 2, 3, 4, 5, 6, and fish",
                          friendly_join([1, 2, u"3", 4, "5", 6, "fish"]))


class TestTrueValue(fixture.SubManFixture):

    def test_true_value(self):
        self.assertTrue(is_true_value("1"))
        self.assertTrue(is_true_value("True"))
        self.assertTrue(is_true_value("true"))
        self.assertTrue(is_true_value("truE"))
        self.assertTrue(is_true_value("yes"))
        self.assertTrue(is_true_value("YeS"))

    def test_false_value(self):
        self.assertFalse(is_true_value("0"))
        self.assertFalse(is_true_value("False"))
        self.assertFalse(is_true_value("FalsE"))
        self.assertFalse(is_true_value("no"))
        self.assertFalse(is_true_value("nO"))
        self.assertFalse(is_true_value("y"))
        self.assertFalse(is_true_value("n"))
        self.assertFalse(is_true_value("t"))
        self.assertFalse(is_true_value("f"))


class TestUniqueListItems(fixture.SubManFixture):
    def test_preserves_order(self):
        input_list = [1, 1, 2, 2, 3, 3]
        expected = [1, 2, 3]
        self.assertEqual(expected, unique_list_items(input_list))

    def test_hash_function(self):
        mock_item_1 = Mock()
        mock_item_1.value = 1
        mock_item_2 = Mock()
        mock_item_2.value = 2
        input_list = [mock_item_1, mock_item_1, mock_item_2, mock_item_2]
        expected = [mock_item_1, mock_item_2]
        self.assertEqual(expected, unique_list_items(input_list, lambda x: x.value))


class TestProductCertificateFilter(fixture.SubManFixture):

    def test_set_filter_string(self):
        test_data = [
            (None, True),

            ("", True),
            ("test", True),
            ("?", True),
            ("*", True),
            ("\\?", True),
            ("\\*", True),
            ("\\\\", True),
            ("*test*", True),
            ("*test\\?", True),
            ("a?b\\\\*c\\?d", True),
            ("**", True),
            ("??", True),
            ("*?", True),
            ("?*", True),
            ("te**st", True),
            ("te*?st", True),
            ("te?*st", True),
            ("te??st", True),
            ("*te\\st*", True),
            ("*te\\\\st*", True),
            ("*te\*\?st*", True),

            (123, False),
            (True, False),
            (False, False),
            (["nope"], False),
            ({"key": "value"}, False)
        ]

        for (index, data) in enumerate(test_data):
            cert_filter = ProductCertificateFilter()
            result = cert_filter.set_filter_string(data[0])

            self.assertEqual(result, data[1], "ProductCertificateFilter.set_filter_string failed with data set %i.\nActual:   %s\nExpected: %s)" % (index, result, data[1]))

    def test_match(self):
        prod_cert = StubProductCertificate(product=StubProduct(name="test*product?", product_id="123456789"))

        test_data = [
            (None, prod_cert, False),
            ("", prod_cert, False),
            ("test", prod_cert, False),
            ("product", prod_cert, False),
            ("test\*product\?", prod_cert, True),
            ("test*", prod_cert, True),
            ("test*********", prod_cert, True),
            ("test?????????", prod_cert, True),
            ("*product?", prod_cert, True),
            ("*product\?", prod_cert, True),
            ("?????product*", prod_cert, True),
            ("*****product*", prod_cert, True),
            ("?????????????", prod_cert, True),
            ("*************", prod_cert, True),
            ("??**??*??**??", prod_cert, True),
            ("**??**?**??**", prod_cert, True),
            ("test?product\?", prod_cert, True),
            ("test*product?", prod_cert, True),
            ("test*nope", prod_cert, False),
            ("nope*product", prod_cert, False),
            ("*nope*", prod_cert, False),
            ("test*nope*product", prod_cert, False),

            ("1234*", prod_cert, True),
            ("*4567*", prod_cert, True),
            ("123???789", prod_cert, True),
            ("??34567??", prod_cert, True),
            ("*4?6*", prod_cert, True),
            ("1234", prod_cert, False),
            ("??123456789", prod_cert, False),
        ]

        for (index, data) in enumerate(test_data):
            cert_filter = ProductCertificateFilter(filter_string=data[0])
            result = cert_filter.match(data[1])

            self.assertEqual(result, data[2], "ProductCertificateFilter.match failed with data set %i.\nActual:   %s\nExpected: %s" % (index, result, data[2]))


class TestEntitlementCertificateFilter(fixture.SubManFixture):

    def test_set_service_level(self):
        test_data = [
            (None, True),
            ("", True),
            ("Bacon", True),
            ("Cheese", True),
            ("Burger", True),

            (123, False),
            (True, False),
            (False, False),
            (["nope"], False),
            ({"key": "value"}, False)
        ]

        for (index, data) in enumerate(test_data):
            cert_filter = EntitlementCertificateFilter()
            result = cert_filter.set_service_level(data[0])

            self.assertEqual(result, data[1], "EntitlementCertificateFilter.set_service_level failed with data set %i.\nActual:   %s\nExpected: %s)" % (index, result, data[1]))

    def test_match(self):
        ent_cert = StubEntitlementCertificate(product=StubProduct(name="test*entitlement?", product_id="123456789"), service_level="Premium", provided_products=[
                "test product b",
                "beta product 1",
                "shared product",
                "back\\slash"
        ])
        # Order information is hard-coded in the stub, so we've to modify it
        # separately:
        ent_cert.order.contract = "Contract-A"

        no_sla_ent_cert = StubEntitlementCertificate(
            product=StubProduct(name="nobodycares", product_id="123456789"),
            service_level=None, provided_products=[])

        test_data = [
            (None, None, ent_cert, False),
            ("*entitlement*", None, ent_cert, True),
            ("*shared*", None, ent_cert, True),
            ("beta*", None, ent_cert, True),
            ("123456789", None, ent_cert, True),
            ("prem*", None, ent_cert, True),                   # service level via --contains-text vs --servicelevel
            ("*contract*", None, ent_cert, True),
            ("contract-a", None, ent_cert, True),
            ("contract-b", None, ent_cert, False),
            ("*entitlement*", "Premium", ent_cert, True),
            ("*shared*", "Premium", ent_cert, True),
            ("beta*", "Premium", ent_cert, True),
            ("123456789", "Premium", ent_cert, True),
            ("prem*", "Premium", ent_cert, True),              # ^
            ("*contract*", "Premium", ent_cert, True),
            ("contract-a", "Premium", ent_cert, True),
            ("contract-b", "Premium", ent_cert, False),
            ("*entitlement*", "Standard", ent_cert, False),
            ("*shared*", "Standard", ent_cert, False),
            ("beta*", "Standard", ent_cert, False),
            ("123456789", "Standard", ent_cert, False),
            ("prem*", "Standard", ent_cert, False),            # ^
            ("*contract*", "Standard", ent_cert, False),
            ("contract-a", "Standard", ent_cert, False),
            ("contract-b", "Standard", ent_cert, False),
            (None, "Premium", ent_cert, True),
            (None, "pReMiUm", ent_cert, True),
            (None, "Standard", ent_cert, False),
            (None, "sTANDard", ent_cert, False),
            (None, "aslfk;", ent_cert, False),
            (None, "", ent_cert, False),
            (None, "", no_sla_ent_cert, True),
        ]

        for (index, data) in enumerate(test_data):
            cert_filter = EntitlementCertificateFilter(
                filter_string=data[0], service_level=data[1])
            result = cert_filter.match(data[2])

            self.assertEqual(result, data[3], "EntitlementCertificateFilter.match failed with data set %i.\nActual:   %s\nExpected: %s" % (index, result, data[3]))
