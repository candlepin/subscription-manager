import unittest

from subscription_manager.utils import *
from subscription_manager.constants import *


class LocalServerRegexTests(unittest.TestCase):

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
        self.assertRaises(ServerUrlParseErrorSchemeNoDoubleSlash,
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
        self.assertRaises(ServerUrlParseErrorSchemeNoDoubleSlash,
                          parse_server_info,
                          local_url)

    # fail at internet
    def test_just_colon_slash(self):
        local_url = "://"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_server_info,
                          local_url)

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

