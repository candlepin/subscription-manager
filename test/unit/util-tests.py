import unittest

from mock import patch
from rhsm.utils import remove_scheme, get_env_proxy_info, \
    ServerUrlParseErrorEmpty, ServerUrlParseErrorNone, \
    ServerUrlParseErrorPort, ServerUrlParseErrorScheme, \
    ServerUrlParseErrorJustScheme, has_bad_scheme, has_good_scheme, \
    parse_url, cmd_name
from rhsm.config import DEFAULT_PORT, DEFAULT_PREFIX, DEFAULT_HOSTNAME


class TestParseServerInfo(unittest.TestCase):

    def test_fully_specified(self):
        local_url = "myhost.example.com:900/myapp"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("900", port)
        self.assertEquals("/myapp", prefix)

    def test_hostname_only(self):
        local_url = "myhost.example.com"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals(None, port)
        self.assertEquals(None, prefix)

    def test_hostname_port(self):
        local_url = "myhost.example.com:500"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("500", port)
        self.assertEquals(None, prefix)

    def test_hostname_prefix(self):
        local_url = "myhost.example.com/myapp"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals(None, port)
        self.assertEquals("/myapp", prefix)

    def test_hostname_slash_no_prefix(self):
        local_url = "http://myhost.example.com/"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals(None, port)
        self.assertEquals("/", prefix)

    def test_hostname_just_slash(self):
        local_url = "/"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals(None, hostname)
        self.assertEquals(None, port)
        self.assertEquals("/", prefix)

    def test_hostname_just_slash_with_defaults(self):
        local_url = "/"
        (username, password, hostname, port, prefix) = parse_url(local_url,
            default_hostname=DEFAULT_HOSTNAME,
            default_port=DEFAULT_PORT)
        self.assertEquals(DEFAULT_HOSTNAME, hostname)
        self.assertEquals(DEFAULT_PORT, port)
        self.assertEquals("/", prefix)

    def test_hostname_nested_prefix(self):
        local_url = "myhost.example.com/myapp/subapp"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals(None, port)
        self.assertEquals("/myapp/subapp", prefix)

    def test_hostname_nothing(self):
        local_url = ""
        self.assertRaises(ServerUrlParseErrorEmpty,
                          parse_url,
                          local_url)

    def test_hostname_none(self):
        local_url = None
        self.assertRaises(ServerUrlParseErrorNone,
                          parse_url,
                          local_url)

    def test_hostname_with_scheme(self):
        # this is the default, so test it here
        local_url = "https://subscription.rhsm.redhat.com/subscription"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("subscription.rhsm.redhat.com", hostname)
        self.assertEquals(None, port)
        self.assertEquals("/subscription", prefix)

    def test_hostname_with_scheme_no_prefix(self):
        local_url = "https://myhost.example.com"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals(None, port)
        self.assertEquals(None, prefix)

    def test_hostname_no_scheme_port_no_prefix(self):
        local_url = "myhost.example.com:8443"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("myhost.example.com", hostname)
        self.assertEquals("8443", port)
        self.assertEquals(None, prefix)

    def test_just_prefix(self):
        local_url = "/myapp"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals(None, hostname)
        self.assertEquals(None, port)
        self.assertEquals("/myapp", prefix)

    def test_short_name(self):
        # could argue anything could be a local hostname, and we should
        # use default port and path. You could also argue it should
        # throw an error, especially if it's not a valid hostname
        local_url = "a"
        (username, password, hostname, port, prefix) = parse_url(local_url,
               default_port=DEFAULT_PORT, default_prefix=DEFAULT_PREFIX)
        self.assertEquals("a", hostname)
        self.assertEquals(DEFAULT_PORT, port)
        self.assertEquals(DEFAULT_PREFIX, prefix)

    def test_wrong_scheme(self):
        local_url = "git://git.fedorahosted.org/candlepin.git"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    def test_bad_http_scheme(self):
        # note missing /
        local_url = "https:/myhost.example.com:8443/myapp"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    def test_colon_but_no_port(self):
        local_url = "https://myhost.example.com:/myapp"
        self.assertRaises(ServerUrlParseErrorPort,
                          parse_url,
                          local_url)

    def test_colon_but_no_port_no_scheme(self):
        local_url = "myhost.example.com:/myapp"
        self.assertRaises(ServerUrlParseErrorPort,
                          parse_url,
                          local_url)

    def test_colon_slash_slash_but_nothing_else(self):
        local_url = "http://"
        self.assertRaises(ServerUrlParseErrorJustScheme,
                          parse_url,
                          local_url)

    def test_colon_slash_but_nothing_else(self):
        local_url = "http:/"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    def test_colon_no_slash(self):
        local_url = "http:example.com/foobar"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    # Note: this means if you have a local server named
    # "http", and you like redundant slashes, this actually
    # valid url of http//path/to/something will fail.
    # Don't do that. (or just use a single slash like http/path)
    # But seriously, really?
    def test_no_colon_double_slash(self):
        local_url = "http//example.com/api"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    def test_https_no_colon_double_slash(self):
        local_url = "https//example.com/api"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    # fail at internet
    def test_just_colon_slash(self):
        local_url = "://"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    def test_one_slash(self):
        local_url = "http/example.com"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    def test_host_named_http(self):
        local_url = "http://http/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("http", hostname)
        self.assertEquals(None, port)
        self.assertEquals('/prefix', prefix)

    def test_one_slash_port_prefix(self):
        local_url = "https/bogaddy:80/candlepin"
        self.assertRaises(ServerUrlParseErrorScheme,
                          parse_url,
                          local_url)

    def test_host_named_http_port_prefix(self):
        local_url = "https://https:8000/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("https", hostname)
        self.assertEquals("8000", port)
        self.assertEquals('/prefix', prefix)

    def test_host_name_non_numeric_port(self):
        local_url = "https://example.com:https/prefix"
        self.assertRaises(ServerUrlParseErrorPort,
                          parse_url,
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


class TestHasBadScheme(unittest.TestCase):

    def test_bad(self):
        self.assertTrue(has_bad_scheme("://example.com"))
        self.assertTrue(has_bad_scheme("http/example.com"))
        self.assertTrue(has_bad_scheme("https/example.com"))
        self.assertTrue(has_bad_scheme("https:/example.com"))

    def test_good(self):
        self.assertFalse(has_bad_scheme("http://example.com"))
        self.assertFalse(has_bad_scheme("https://example.com"))


class TestHasGoodScheme(unittest.TestCase):

    def test_good(self):
        self.assertTrue(has_good_scheme("http://example.com"))
        self.assertTrue(has_good_scheme("https://example.com"))

    def test_bad(self):
        self.assertFalse(has_good_scheme("://example.com"))
        self.assertFalse(has_good_scheme("http/example.com"))
        self.assertFalse(has_good_scheme("https/example.com"))
        self.assertFalse(has_good_scheme("https:/example.com"))


class TestParseUrl(unittest.TestCase):

    def test_username_password(self):
        local_url = "http://user:pass@hostname:1111/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("user", username)
        self.assertEquals("pass", password)
        self.assertEquals("hostname", hostname)
        self.assertEquals("1111", port)
        self.assertEquals("/prefix", prefix)

    def test_no_password(self):
        local_url = "http://user@hostname:1111/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals("user", username)
        self.assertEquals(None, password)
        self.assertEquals("hostname", hostname)
        self.assertEquals("1111", port)
        self.assertEquals("/prefix", prefix)

    def test_no_userinfo(self):
        local_url = "http://hostname:1111/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals(None, username)
        self.assertEquals(None, password)
        self.assertEquals("hostname", hostname)
        self.assertEquals("1111", port)
        self.assertEquals("/prefix", prefix)

    def test_no_userinfo_with_at(self):
        local_url = "http://@hostname:1111/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEquals(None, username)
        self.assertEquals(None, password)
        self.assertEquals("hostname", hostname)
        self.assertEquals("1111", port)
        self.assertEquals("/prefix", prefix)


class TestProxyInfo(unittest.TestCase):
    def _gen_env(self, variables):
        """
        Return an environment with everything empty except
        those passed in variables.
        """
        proxy_env = {'HTTPS_PROXY': '', 'https_proxy': '',
                     'HTTP_PROXY': '', 'http_proxy': ''}
        if variables:
            for (key, value) in variables.items():
                proxy_env[key] = value
        return proxy_env

    def test_https_proxy_info(self):
        with patch.dict('os.environ', self._gen_env({'https_proxy': 'https://u:p@host:1111'})):
            proxy_info = get_env_proxy_info()
            self.assertEquals("u", proxy_info["proxy_username"])
            self.assertEquals("p", proxy_info["proxy_password"])
            self.assertEquals("host", proxy_info["proxy_hostname"])
            self.assertEquals(int("1111"), proxy_info["proxy_port"])

    def test_http_proxy_info(self):
        with patch.dict('os.environ', self._gen_env({'http_proxy': 'http://u:p@host:2222'})):
            proxy_info = get_env_proxy_info()
            self.assertEquals("u", proxy_info["proxy_username"])
            self.assertEquals("p", proxy_info["proxy_password"])
            self.assertEquals("host", proxy_info["proxy_hostname"])
            self.assertEquals(int("2222"), proxy_info["proxy_port"])

    def test_http_proxy_info_allcaps(self):
        with patch.dict('os.environ', self._gen_env({'HTTP_PROXY': 'http://u:p@host:3333'})):
            proxy_info = get_env_proxy_info()
            self.assertEquals("u", proxy_info["proxy_username"])
            self.assertEquals("p", proxy_info["proxy_password"])
            self.assertEquals("host", proxy_info["proxy_hostname"])
            self.assertEquals(int("3333"), proxy_info["proxy_port"])

    def test_https_proxy_info_allcaps(self):
        with patch.dict('os.environ', self._gen_env({'HTTPS_PROXY': 'https://u:p@host:4444'})):
            proxy_info = get_env_proxy_info()
            self.assertEquals("u", proxy_info["proxy_username"])
            self.assertEquals("p", proxy_info["proxy_password"])
            self.assertEquals("host", proxy_info["proxy_hostname"])
            self.assertEquals(int("4444"), proxy_info["proxy_port"])

    def test_order(self):
        # should follow the order: HTTPS, https, HTTP, http
        with patch.dict('os.environ', self._gen_env({'HTTPS_PROXY': 'http://u:p@host:1111', 'http_proxy': 'http://notme:orme@host:2222'})):
            proxy_info = get_env_proxy_info()
            self.assertEquals("u", proxy_info["proxy_username"])
            self.assertEquals("p", proxy_info["proxy_password"])
            self.assertEquals("host", proxy_info["proxy_hostname"])
            self.assertEquals(int("1111"), proxy_info["proxy_port"])

    def test_no_port(self):
        with patch.dict('os.environ', self._gen_env({'HTTPS_PROXY': 'http://u:p@host'})):
            proxy_info = get_env_proxy_info()
            self.assertEquals("u", proxy_info["proxy_username"])
            self.assertEquals("p", proxy_info["proxy_password"])
            self.assertEquals("host", proxy_info["proxy_hostname"])
            self.assertEquals(3128, proxy_info["proxy_port"])

    def test_no_user_or_password(self):
        with patch.dict('os.environ', self._gen_env({'HTTPS_PROXY': 'http://host:1111'})):
            proxy_info = get_env_proxy_info()
            self.assertEquals(None, proxy_info["proxy_username"])
            self.assertEquals(None, proxy_info["proxy_password"])
            self.assertEquals("host", proxy_info["proxy_hostname"])
            self.assertEquals(int("1111"), proxy_info["proxy_port"])


class TestCmdName(unittest.TestCase):
    def test_usr_sbin(self):
        argv = ['/usr/sbin/subscription-manager', 'list']
        self.assertEquals("subscription-manager", cmd_name(argv))

    def test_bin(self):
        argv = ['bin/subscription-manager', 'subscribe', '--auto']
        self.assertEquals("subscription-manager", cmd_name(argv))

    def test_sbin(self):
        argv = ['/sbin/subscription-manager', 'list']
        self.assertEquals("subscription-manager", cmd_name(argv))

    def test_subscription_manager_gui(self):
        argv = ['/sbin/subscription-manager-gui']
        self.assertEquals("subscription-manager-gui", cmd_name(argv))

    def test_initial_setup(self):
        argv = ['/usr/lib/python2.7/site-packages/initial_setup/__main__.py']
        self.assertEquals("initial-setup", cmd_name(argv))

    def test_yum(self):
        argv = ['/bin/yum', 'install', 'zsh']
        self.assertEquals("yum", cmd_name(argv))

    def test_rhsmcertd_worker(self):
        argv = ['/usr/libexec/rhsmcertd-worker']
        self.assertEquals("rhsmcertd-worker", cmd_name(argv))

    def test_rhsm_debug(self):
        argv = ['/bin/rhsm-debug']
        self.assertEquals("rhsm-debug", cmd_name(argv))

    def test_virt_who(self):
        argv = ['/usr/share/virt-who/virtwho.py']
        self.assertEquals("virtwho.py", cmd_name(argv))

    def test_rhsmd(self):
        argv = ['/usr/libexec/rhsmd', '-i', '-f', 'valid']
        self.assertEquals("rhsmd", cmd_name(argv))
