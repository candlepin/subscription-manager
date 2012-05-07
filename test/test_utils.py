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
