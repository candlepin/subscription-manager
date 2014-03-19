import fixture

from mock import Mock, patch
from rhsm.utils import ServerUrlParseErrorEmpty, \
    ServerUrlParseErrorNone, ServerUrlParseErrorPort, \
    ServerUrlParseErrorScheme, ServerUrlParseErrorJustScheme
from subscription_manager.utils import parse_server_info, \
    parse_baseurl_info, format_baseurl, \
    get_version, get_client_versions, \
    get_server_versions, Versions, friendly_join, is_true_value

from rhsm.config import DEFAULT_PORT, DEFAULT_PREFIX, DEFAULT_HOSTNAME, \
    DEFAULT_CDN_HOSTNAME, DEFAULT_CDN_PORT, DEFAULT_CDN_PREFIX


class TestParseServerInfo(fixture.SubManFixture):

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
class TestParseBaseUrlInfo(fixture.SubManFixture):
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


NOT_COLLECTED = "non-collected-package"


class TestGetServerVersions(fixture.SubManFixture):

    @patch('subscription_manager.utils.Versions', spec=Versions)
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_classic(self, mock_classic, mock_versions):
        self._inject_mock_invalid_consumer()
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = True

        sv = get_server_versions(None)
        self.assertEquals(sv['server-type'], "RHN Classic")
        self.assertEquals(sv['candlepin'], "Unknown")

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_no_status(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = False
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = False
        sv = get_server_versions(MockUep)
        self.assertEquals(sv['server-type'], 'Red Hat Subscription Management')
        self.assertEquals(sv['candlepin'], "Unknown")

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_with_status(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = False
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = True
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEquals(sv['server-type'], 'Red Hat Subscription Management')
        self.assertEquals(sv['candlepin'], '101-23423c')

    @patch('rhsm.connection.UEPConnection')
    @patch('subscription_manager.utils.ClassicCheck')
    def test_get_server_versions_cp_with_status_and_classic(self, mock_classic, MockUep):
        instance = mock_classic.return_value
        instance.is_registered_with_classic.return_value = True
        self._inject_mock_valid_consumer()
        MockUep.supports_resource.return_value = True
        MockUep.getStatus.return_value = {'version': '101', 'release': '23423c'}
        sv = get_server_versions(MockUep)
        self.assertEquals(sv['server-type'], 'RHN Classic and Red Hat Subscription Management')
        self.assertEquals(sv['candlepin'], '101-23423c')

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
        self.assertEquals(sv['server-type'], "Red Hat Subscription Management")
        self.assertEquals(sv['candlepin'], "Unknown")

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
        self.assertEquals(sv['server-type'], "RHN Classic")
        self.assertEquals(sv['candlepin'], "Unknown")


class TestGetClientVersions(fixture.SubManFixture):
    @patch('subscription_manager.utils.Versions')
    def test_get_client_versions(self, MockVersions):
        # FIXME: the singleton-esqu nature of subscription_manager.utils.Versions
        # make mocking/stubbing a little odd, more exhaustive testing
        # will require figuing that out
        instance = MockVersions.return_value

        instance.get_version.return_value = '2'
        instance.get_release.return_value = '3'
        cv = get_client_versions()

        self.assertEquals(cv['subscription-manager'], "2-3")
        self.assertEquals(cv['python-rhsm'], '2-3')

    @patch('subscription_manager.utils.Versions')
    def test_get_client_versions_strings(self, MockVersions):
        instance = MockVersions.return_value
        instance.get_version.return_value = 'as'
        instance.get_release.return_value = 'vc'
        cv = get_client_versions()

        self.assertEquals(cv['subscription-manager'], "as-vc")
        self.assertEquals(cv['python-rhsm'], 'as-vc')

    @patch('subscription_manager.utils.Versions')
    def test_get_client_versions_exception(self, MockVersions):
        def raise_exception(arg):
            raise Exception("boom" + arg)

        instance = MockVersions.return_value
        instance.get_version.return_value = 'as'
        instance.get_release.return_value = 'vc'
        instance.get_version.side_effect = raise_exception

        cv = get_client_versions()
        self.assertEquals(cv['subscription-manager'], "Unknown")
        self.assertEquals(cv['python-rhsm'], 'Unknown')


class TestGetVersion(fixture.SubManFixture):
    def test_version_and_release_present(self):
        versions = Mock()
        versions.get_version.return_value = "1.0"
        versions.get_release.return_value = "1"
        result = get_version(versions, "foobar")
        self.assertEquals("1.0-1", result)

    def test_version_no_release(self):
        versions = Mock()
        versions.get_version.return_value = "1.0"
        versions.get_release.return_value = ""
        result = get_version(versions, "foobar")
        self.assertEquals("1.0", result)


class TestFriendlyJoin(fixture.SubManFixture):

    def test_join(self):
        self.assertEquals("One", friendly_join(["One"]))
        self.assertEquals("One and Two", friendly_join(["One", "Two"]))
        self.assertEquals("One, Two, and Three", friendly_join(["One", "Two", "Three"]))
        self.assertEquals("Three, Two, and One", friendly_join(set(["One", "Two", "Three"])))
        self.assertEquals("", friendly_join([]))
        self.assertEquals("", friendly_join(None))


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
