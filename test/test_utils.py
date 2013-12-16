import unittest

from mock import patch
from subscription_manager.utils import remove_scheme, parse_server_info, \
    parse_baseurl_info, format_baseurl, ServerUrlParseErrorEmpty, \
    ServerUrlParseErrorNone, ServerUrlParseErrorPort, ServerUrlParseErrorScheme, \
    ServerUrlParseErrorJustScheme, get_client_versions, \
    get_server_versions, friendly_join
from subscription_manager import certlib
from rhsm.config import DEFAULT_PORT, DEFAULT_PREFIX, DEFAULT_HOSTNAME, \
    DEFAULT_CDN_HOSTNAME, DEFAULT_CDN_PORT, DEFAULT_CDN_PREFIX


class TestParseServerInfo(unittest.TestCase):

    def test_fully_specified(self):
        local_url = "myhost.example.com:900/myapp"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("900", port)
        self.assertEquals("/myapp", prefix)

    def test_hostname_only(self):
        local_url = "myhost.example.com"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("443", port)
        self.assertEquals(DEFAULT_PREFIX, prefix)

    def test_hostname_port(self):
        local_url = "myhost.example.com:500"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("500", port)
        self.assertEquals(DEFAULT_PREFIX, prefix)

    def test_hostname_prefix(self):
        local_url = "myhost.example.com/myapp"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("443", port)
        self.assertEquals("/myapp", prefix)

    def test_hostname_slash_no_prefix(self):
        local_url = "http://myhost.example.com/"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("443", port)
        self.assertEquals("/", prefix)

    def test_hostname_just_slash(self):
        local_url = "/"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals(DEFAULT_HOSTNAME, hostname)
        self.assertEquals(DEFAULT_PORT, port)
        self.assertEquals("/", prefix)

    def test_hostname_nested_prefix(self):
        local_url = "myhost.example.com/myapp/subapp"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("443", port)
        self.assertEquals("/myapp/subapp", prefix)

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
        local_url = "https://subscription.rhn.redhat.com/subscription"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("subscription.rhn.redhat.com", hostname)
        self.assertEquals(DEFAULT_PORT, port)
        self.assertEquals("/subscription", prefix)

    def test_hostname_with_scheme_no_prefix(self):
        local_url = "https://myhost.example.com"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals(DEFAULT_PORT, port)
        self.assertEquals("/subscription", prefix)

    def test_hostname_no_scheme_port_no_prefix(self):
        local_url = "myhost.example.com:8443"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("8443", port)
        self.assertEquals("/subscription", prefix)

    def test_just_prefix(self):
        local_url = "/myapp"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals(DEFAULT_HOSTNAME, hostname)
        self.assertEquals(DEFAULT_PORT, port)
        self.assertEquals("/myapp", prefix)

    def test_short_name(self):
        # could argue anything could be a local hostname, and we should
        # use default port and path. You could also argue it should
        # throw an error, especially if it's not a valid hostname
        local_url = "a"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("a", hostname)
        self.assertEquals(DEFAULT_PORT, port)
        self.assertEquals(DEFAULT_PREFIX, prefix)

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
        self.assertEquals("http", hostname)
        self.assertEquals(DEFAULT_PORT, port)
        self.assertEquals('/prefix', prefix)

    def test_one_slash_port_prefix(self):
        local_url = "https/bogaddy:80/candlepin"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

    def test_host_named_http_port_prefix(self):
        local_url = "https://https:8000/prefix"
        (hostname, port, prefix) = parse_server_info(local_url)
        self.assertEquals("https", hostname)
        self.assertEquals("8000", port)
        self.assertEquals('/prefix', prefix)

    def test_host_name_non_numeric_port(self):
        local_url = "https://example.com:https/prefix"
        self.assertRaises(ServerUrlParseErrorPort,
                          parse_server_info,
                          local_url)


# TestParseServerInfo pretty much covers this code wise
class TestParseBaseUrlInfo(unittest.TestCase):
    def test_hostname_with_scheme(self):
        # this is the default, so test it here
        local_url = "https://cdn.redhat.com"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEquals(DEFAULT_CDN_HOSTNAME, hostname)
        self.assertEquals(DEFAULT_CDN_PORT, port)
        self.assertEquals("/", prefix)

    def test_format_base_url(self):
        local_url = "https://cdn.redhat.com"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEquals(local_url, format_baseurl(hostname, port, prefix))

    def test_format_base_url_with_port(self):
        local_url = "https://cdn.redhat.com:443"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEquals(prefix, DEFAULT_CDN_PREFIX)
        self.assertEquals("https://cdn.redhat.com", format_baseurl(hostname, port, prefix))

    def test_format_thumbslug_url_with_port(self):
        local_url = "https://someserver.example.com:8088"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEquals(prefix, DEFAULT_CDN_PREFIX)
        self.assertEquals("https://someserver.example.com:8088", format_baseurl(hostname, port, prefix))

    def test_format_not_fqdn_with_port(self):
        local_url = "https://foo-bar:8088"
        (hostname, port, prefix) = parse_baseurl_info(local_url)
        self.assertEquals(prefix, DEFAULT_CDN_PREFIX)
        self.assertEquals("https://foo-bar:8088", format_baseurl(hostname, port, prefix))


class TestRemoveScheme(unittest.TestCase):
    def test_colon_port(self):
        proxy_url = "proxy.example.com:3128"
        res = remove_scheme(proxy_url)
        self.assertEquals(res, proxy_url)

    def test_http_scheme(self):
        proxy_url = "http://example.com:3128"
        res = remove_scheme(proxy_url)
        self.assertEquals(res, "example.com:3128")

    def test_https_scheme(self):
        proxy_url = "https://example.com:3128"
        res = remove_scheme(proxy_url)
        self.assertEquals(res, "example.com:3128")

    def test_no_port(self):
        proxy_url = "proxy.example.com"
        res = remove_scheme(proxy_url)
        self.assertEquals(res, proxy_url)


NOT_COLLECTED = "non-collected-package"


class TestGetServerVersions(unittest.TestCase):

    @patch('subscription_manager.utils.ClassicCheck')
    @patch.object(certlib.ConsumerIdentity, 'existsAndValid')
    def test_get_server_versions_classic(self, mci_exists_and_valid, MockClassicCheck):
        instance = MockClassicCheck.return_value
        instance.is_registered_with_classic.return_value = True
        mci_exists_and_valid.return_value = False

        sv = get_server_versions(None)
        self.assertEquals(sv['server-type'], "RHN Classic")
        self.assertEquals(sv['candlepin'], "Unknown")

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    @patch.object(certlib.ConsumerIdentity, 'existsAndValid')
    def test_get_server_versions_cp_no_status(self, mci_exists_and_valid, MockClassicCheck, MockUep):
        instance = MockClassicCheck.return_value
        instance.is_registered_with_classic.return_value = False
        mci_exists_and_valid.return_value = True
        MockUep.supports_resource.return_value = False
        sv = get_server_versions(MockUep)
        self.assertEquals(sv['server-type'], 'Red Hat Subscription Management')
        self.assertEquals(sv['candlepin'], "Unknown")

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    @patch.object(certlib.ConsumerIdentity, 'existsAndValid')
    def test_get_server_versions_cp_with_status(self, mci_exists_and_valid, MockClassicCheck, MockUep):
        instance = MockClassicCheck.return_value
        instance.is_registered_with_classic.return_value = False
        mci_exists_and_valid.return_value = True
        MockUep.supports_resource.return_value = True
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEquals(sv['server-type'], 'Red Hat Subscription Management')
        self.assertEquals(sv['candlepin'], '101-23423c')

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    @patch.object(certlib.ConsumerIdentity, 'existsAndValid')
    def test_get_server_versions_cp_with_status_and_classic(self, mci_exists_and_valid, MockClassicCheck, MockUep):
        instance = MockClassicCheck.return_value
        instance.is_registered_with_classic.return_value = True
        mci_exists_and_valid.return_value = True
        MockUep.supports_resource.return_value = True
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEquals(sv['server-type'], 'RHN Classic and Red Hat Subscription Management')
        self.assertEquals(sv['candlepin'], '101-23423c')

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    @patch.object(certlib.ConsumerIdentity, 'existsAndValid')
    def test_get_server_versions_cp_exception(self, mci_exists_and_valid, MockClassicCheck, MockUep):
        def raise_exception(arg):
            raise Exception("boom")
        instance = MockClassicCheck.return_value
        instance.is_registered_with_classic.return_value = False
        mci_exists_and_valid.return_value = True
        MockUep.supports_resource.side_effect = raise_exception
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEquals(sv['server-type'], "Red Hat Subscription Management")
        self.assertEquals(sv['candlepin'], "Unknown")

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    @patch.object(certlib.ConsumerIdentity, 'existsAndValid')
    def test_get_server_versions_cp_exception_and_classic(self, mci_exists_and_valid, MockClassicCheck, MockUep):
        def raise_exception(arg):
            raise Exception("boom")
        instance = MockClassicCheck.return_value
        instance.is_registered_with_classic.return_value = True
        mci_exists_and_valid.return_value = False
        MockUep.supports_resource.side_effect = raise_exception
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEquals(sv['server-type'], "RHN Classic")
        self.assertEquals(sv['candlepin'], "Unknown")


class TestClientVersion(unittest.TestCase):
    def test_get_client_versions(self):
        client_versions = get_client_versions()
        self.assertTrue('python-rhsm' in client_versions)
        self.assertTrue('subscription-manager' in client_versions)
        self.assertTrue(isinstance(client_versions['python-rhsm'], str))
        self.assertTrue(isinstance(client_versions['subscription-manager'], str))


class TestFriendlyJoin(unittest.TestCase):

    def test_join(self):
        self.assertEquals("One", friendly_join(["One"]))
        self.assertEquals("One and Two", friendly_join(["One", "Two"]))
        self.assertEquals("One, Two, and Three", friendly_join(["One", "Two", "Three"]))
        self.assertEquals("Three, Two, and One", friendly_join(set(["One", "Two", "Three"])))
        self.assertEquals("", friendly_join([]))
        self.assertEquals("", friendly_join(None))
