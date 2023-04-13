import threading
import time
import unittest

from unittest.mock import patch
from rhsm.utils import (
    remove_scheme,
    get_env_proxy_info,
    ServerUrlParseErrorEmpty,
    ServerUrlParseErrorNone,
    ServerUrlParseErrorPort,
    ServerUrlParseErrorScheme,
    ServerUrlParseErrorJustScheme,
    has_bad_scheme,
    has_good_scheme,
    parse_url,
    cmd_name,
    singleton,
    call_once,
    lock,
)
from rhsm.config import DEFAULT_PORT, DEFAULT_PREFIX, DEFAULT_HOSTNAME


class TestParseServerInfo(unittest.TestCase):
    def test_fully_specified(self):
        local_url = "myhost.example.com:900/myapp"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("900", port)
        self.assertEqual("/myapp", prefix)

    def test_hostname_only(self):
        local_url = "myhost.example.com"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual(None, port)
        self.assertEqual(None, prefix)

    def test_hostname_port(self):
        local_url = "myhost.example.com:500"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("500", port)
        self.assertEqual(None, prefix)

    def test_hostname_prefix(self):
        local_url = "myhost.example.com/myapp"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual(None, port)
        self.assertEqual("/myapp", prefix)

    def test_hostname_slash_no_prefix(self):
        local_url = "http://myhost.example.com/"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual(None, port)
        self.assertEqual("/", prefix)

    def test_hostname_just_slash(self):
        local_url = "/"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual(None, hostname)
        self.assertEqual(None, port)
        self.assertEqual("/", prefix)

    def test_hostname_just_slash_with_defaults(self):
        local_url = "/"
        (username, password, hostname, port, prefix) = parse_url(
            local_url, default_hostname=DEFAULT_HOSTNAME, default_port=DEFAULT_PORT
        )
        self.assertEqual(DEFAULT_HOSTNAME, hostname)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual("/", prefix)

    def test_hostname_nested_prefix(self):
        local_url = "myhost.example.com/myapp/subapp"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual(None, port)
        self.assertEqual("/myapp/subapp", prefix)

    def test_hostname_nothing(self):
        local_url = ""
        self.assertRaises(ServerUrlParseErrorEmpty, parse_url, local_url)

    def test_hostname_none(self):
        local_url = None
        self.assertRaises(ServerUrlParseErrorNone, parse_url, local_url)

    def test_hostname_with_scheme(self):
        # this is the default, so test it here
        local_url = "https://subscription.rhsm.redhat.com/subscription"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("subscription.rhsm.redhat.com", hostname)
        self.assertEqual(None, port)
        self.assertEqual("/subscription", prefix)

    def test_hostname_with_scheme_no_prefix(self):
        local_url = "https://myhost.example.com"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual(None, port)
        self.assertEqual(None, prefix)

    def test_hostname_no_scheme_port_no_prefix(self):
        local_url = "myhost.example.com:8443"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("myhost.example.com", hostname)
        self.assertEqual("8443", port)
        self.assertEqual(None, prefix)

    def test_just_prefix(self):
        local_url = "/myapp"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual(None, hostname)
        self.assertEqual(None, port)
        self.assertEqual("/myapp", prefix)

    def test_short_name(self):
        # could argue anything could be a local hostname, and we should
        # use default port and path. You could also argue it should
        # throw an error, especially if it's not a valid hostname
        local_url = "a"
        (username, password, hostname, port, prefix) = parse_url(
            local_url, default_port=DEFAULT_PORT, default_prefix=DEFAULT_PREFIX
        )
        self.assertEqual("a", hostname)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual(DEFAULT_PREFIX, prefix)

    def test_wrong_scheme(self):
        local_url = "git://git.fedorahosted.org/candlepin.git"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    def test_bad_http_scheme(self):
        # note missing /
        local_url = "https:/myhost.example.com:8443/myapp"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    def test_colon_but_no_port(self):
        local_url = "https://myhost.example.com:/myapp"
        self.assertRaises(ServerUrlParseErrorPort, parse_url, local_url)

    def test_colon_but_no_port_no_scheme(self):
        local_url = "myhost.example.com:/myapp"
        self.assertRaises(ServerUrlParseErrorPort, parse_url, local_url)

    def test_colon_slash_slash_but_nothing_else(self):
        local_url = "http://"
        self.assertRaises(ServerUrlParseErrorJustScheme, parse_url, local_url)

    def test_colon_slash_but_nothing_else(self):
        local_url = "http:/"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    def test_colon_no_slash(self):
        local_url = "http:example.com/foobar"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    # Note: this means if you have a local server named
    # "http", and you like redundant slashes, this actually
    # valid url of http//path/to/something will fail.
    # Don't do that. (or just use a single slash like http/path)
    # But seriously, really?
    def test_no_colon_double_slash(self):
        local_url = "http//example.com/api"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    def test_https_no_colon_double_slash(self):
        local_url = "https//example.com/api"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    # fail at internet
    def test_just_colon_slash(self):
        local_url = "://"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    def test_one_slash(self):
        local_url = "http/example.com"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    def test_host_named_http(self):
        local_url = "http://http/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("http", hostname)
        self.assertEqual(None, port)
        self.assertEqual("/prefix", prefix)

    def test_one_slash_port_prefix(self):
        local_url = "https/bogaddy:80/candlepin"
        self.assertRaises(ServerUrlParseErrorScheme, parse_url, local_url)

    def test_host_named_http_port_prefix(self):
        local_url = "https://https:8000/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("https", hostname)
        self.assertEqual("8000", port)
        self.assertEqual("/prefix", prefix)

    def test_host_name_non_numeric_port(self):
        local_url = "https://example.com:https/prefix"
        self.assertRaises(ServerUrlParseErrorPort, parse_url, local_url)


class TestRemoveScheme(unittest.TestCase):
    def test_colon_port(self):
        proxy_url = "proxy.example.com:3128"
        res = remove_scheme(proxy_url)
        self.assertEqual(res, proxy_url)

    def test_http_scheme(self):
        proxy_url = "http://example.com:3128"
        res = remove_scheme(proxy_url)
        self.assertEqual(res, "example.com:3128")

    def test_https_scheme(self):
        proxy_url = "https://example.com:3128"
        res = remove_scheme(proxy_url)
        self.assertEqual(res, "example.com:3128")

    def test_no_port(self):
        proxy_url = "proxy.example.com"
        res = remove_scheme(proxy_url)
        self.assertEqual(res, proxy_url)


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
        self.assertEqual("user", username)
        self.assertEqual("pass", password)
        self.assertEqual("hostname", hostname)
        self.assertEqual("1111", port)
        self.assertEqual("/prefix", prefix)

    def test_no_password(self):
        local_url = "http://user@hostname:1111/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual("user", username)
        self.assertEqual(None, password)
        self.assertEqual("hostname", hostname)
        self.assertEqual("1111", port)
        self.assertEqual("/prefix", prefix)

    def test_no_userinfo(self):
        local_url = "http://hostname:1111/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual(None, username)
        self.assertEqual(None, password)
        self.assertEqual("hostname", hostname)
        self.assertEqual("1111", port)
        self.assertEqual("/prefix", prefix)

    def test_no_userinfo_with_at(self):
        local_url = "http://@hostname:1111/prefix"
        (username, password, hostname, port, prefix) = parse_url(local_url)
        self.assertEqual(None, username)
        self.assertEqual(None, password)
        self.assertEqual("hostname", hostname)
        self.assertEqual("1111", port)
        self.assertEqual("/prefix", prefix)


class TestProxyInfo(unittest.TestCase):
    def _gen_env(self, variables):
        """
        Return an environment with everything empty except
        those passed in variables.
        """
        proxy_env = {"HTTPS_PROXY": "", "https_proxy": "", "HTTP_PROXY": "", "http_proxy": ""}
        if variables:
            for key, value in list(variables.items()):
                proxy_env[key] = value
        return proxy_env

    def test_https_proxy_info(self):
        with patch.dict("os.environ", self._gen_env({"https_proxy": "https://u:p@host:1111"})):
            proxy_info = get_env_proxy_info()
            self.assertEqual("u", proxy_info["proxy_username"])
            self.assertEqual("p", proxy_info["proxy_password"])
            self.assertEqual("host", proxy_info["proxy_hostname"])
            self.assertEqual(int("1111"), proxy_info["proxy_port"])

    def test_http_proxy_info(self):
        with patch.dict("os.environ", self._gen_env({"http_proxy": "http://u:p@host:2222"})):
            proxy_info = get_env_proxy_info()
            self.assertEqual("u", proxy_info["proxy_username"])
            self.assertEqual("p", proxy_info["proxy_password"])
            self.assertEqual("host", proxy_info["proxy_hostname"])
            self.assertEqual(int("2222"), proxy_info["proxy_port"])

    def test_http_proxy_info_allcaps(self):
        with patch.dict("os.environ", self._gen_env({"HTTP_PROXY": "http://u:p@host:3333"})):
            proxy_info = get_env_proxy_info()
            self.assertEqual("u", proxy_info["proxy_username"])
            self.assertEqual("p", proxy_info["proxy_password"])
            self.assertEqual("host", proxy_info["proxy_hostname"])
            self.assertEqual(int("3333"), proxy_info["proxy_port"])

    def test_https_proxy_info_allcaps(self):
        with patch.dict("os.environ", self._gen_env({"HTTPS_PROXY": "https://u:p@host:4444"})):
            proxy_info = get_env_proxy_info()
            self.assertEqual("u", proxy_info["proxy_username"])
            self.assertEqual("p", proxy_info["proxy_password"])
            self.assertEqual("host", proxy_info["proxy_hostname"])
            self.assertEqual(int("4444"), proxy_info["proxy_port"])

    def test_order(self):
        # should follow the order: HTTPS, https, HTTP, http
        with patch.dict(
            "os.environ",
            self._gen_env(
                {"HTTPS_PROXY": "http://u:p@host:1111", "http_proxy": "http://notme:orme@host:2222"}
            ),
        ):
            proxy_info = get_env_proxy_info()
            self.assertEqual("u", proxy_info["proxy_username"])
            self.assertEqual("p", proxy_info["proxy_password"])
            self.assertEqual("host", proxy_info["proxy_hostname"])
            self.assertEqual(int("1111"), proxy_info["proxy_port"])

    def test_no_port(self):
        with patch.dict("os.environ", self._gen_env({"HTTPS_PROXY": "http://u:p@host"})):
            proxy_info = get_env_proxy_info()
            self.assertEqual("u", proxy_info["proxy_username"])
            self.assertEqual("p", proxy_info["proxy_password"])
            self.assertEqual("host", proxy_info["proxy_hostname"])
            self.assertEqual(3128, proxy_info["proxy_port"])

    def test_no_user_or_password(self):
        with patch.dict("os.environ", self._gen_env({"HTTPS_PROXY": "http://host:1111"})):
            proxy_info = get_env_proxy_info()
            self.assertEqual(None, proxy_info["proxy_username"])
            self.assertEqual(None, proxy_info["proxy_password"])
            self.assertEqual("host", proxy_info["proxy_hostname"])
            self.assertEqual(int("1111"), proxy_info["proxy_port"])


class TestCmdName(unittest.TestCase):
    def test_usr_sbin(self):
        argv = ["/usr/sbin/subscription-manager", "list"]
        self.assertEqual("subscription-manager", cmd_name(argv))

    def test_bin(self):
        argv = ["bin/subscription-manager", "subscribe", "--auto"]
        self.assertEqual("subscription-manager", cmd_name(argv))

    def test_sbin(self):
        argv = ["/sbin/subscription-manager", "list"]
        self.assertEqual("subscription-manager", cmd_name(argv))

    def test_subscription_manager_gui(self):
        argv = ["/sbin/subscription-manager-gui"]
        self.assertEqual("subscription-manager-gui", cmd_name(argv))

    def test_yum(self):
        argv = ["/bin/yum", "install", "zsh"]
        self.assertEqual("yum", cmd_name(argv))

    def test_rhsmcertd_worker(self):
        argv = ["/usr/libexec/rhsmcertd-worker"]
        self.assertEqual("rhsmcertd-worker", cmd_name(argv))

    def test_rhsm_debug(self):
        argv = ["/bin/rhsm-debug"]
        self.assertEqual("rhsm-debug", cmd_name(argv))

    def test_virt_who(self):
        argv = ["/usr/share/virt-who/virtwho.py"]
        self.assertEqual("virtwho.py", cmd_name(argv))


class TestSingletonize(unittest.TestCase):
    def test_class(self):
        """Test that two instances of singleton class are the same object."""

        @singleton
        class Singleton:
            pass

        singleton_1 = Singleton()
        singleton_2 = Singleton()
        self.assertEqual(id(singleton_1), id(singleton_2))
        self.assertEqual(singleton_1, singleton_2)

    def test_subclass(self):
        """Test that two singleton subclass instances are the same object."""

        class Parent:
            pass

        @singleton
        class Child(Parent):
            pass

        child_1 = Child()
        child_2 = Child()
        self.assertEqual(id(child_1), id(child_2))
        self.assertEqual(child_1, child_2)

    def test_subclass_of_singleton(self):
        """Test that singleton's subclass is also singleton."""

        @singleton
        class Parent:
            pass

        class Child(Parent):
            pass

        parent = Parent()
        child_1 = Child()
        child_2 = Child()

        self.assertNotEqual(parent, child_1)
        self.assertNotEqual(id(parent), id(child_1))
        self.assertEqual(child_1, child_2)
        self.assertEqual(id(child_1), id(child_2))

        self.assertEqual(type(child_1._instance), Child)
        self.assertEqual(type(child_2._instance), Child)

    def test_class_with_init(self):
        """Test that two instances of singleton share their object attributes."""

        @singleton
        class Singleton:
            def __init__(self, value: int):
                self.value = value

        singleton_1 = Singleton(1)
        singleton_2 = Singleton(2)
        self.assertEqual(singleton_1.value, 2)
        self.assertEqual(singleton_2.value, 2)

    def test_shared_attribute(self):
        """Test that two instances of singleton share their class attributes."""

        @singleton
        class Singleton:
            value: int = 0

            def __init__(self):
                self.value += 1

        singleton_1 = Singleton()
        singleton_2 = Singleton()
        self.assertEqual(singleton_1.value, 2)
        self.assertEqual(singleton_2.value, 2)

    def test_custom_new(self):
        """Test that singleton class works with custom __new__ methods."""

        @singleton
        class Singleton:
            value: int = 0

            def __new__(cls, value: int):
                cls.value = value
                return object.__new__(cls)

        singleton_1 = Singleton(1)
        singleton_2 = Singleton(2)

        self.assertEqual(singleton_1.value, 1)
        self.assertEqual(singleton_2.value, 1)


class TestCallOnce(unittest.TestCase):
    def test_basic(self):
        """Test that function with no parent class is called just once."""

        @call_once
        def add(a: int, b: int) -> int:
            return a + b

        result_1 = add(1, 2)
        self.assertEqual(result_1, 3)
        result_2 = add(3, 4)
        self.assertIsNone(result_2)

    def test_init(self):
        """Test that __init__ is called just once."""

        class Foo:
            value: int = 0

            @call_once
            def __init__(self, value: int):
                self.value = value

        foo1 = Foo(1)
        self.assertEqual(foo1.value, 1)
        foo2 = Foo(2)
        self.assertEqual(foo2.value, 0)

    def test_reset(self):
        """Test that call_once-decorated function can be reset."""

        class Foo:
            value: int = 0

            @call_once
            def __init__(self, value: int):
                self.value = value

        foo1 = Foo(1)
        self.assertEqual(foo1.value, 1)
        foo2 = Foo(2)
        self.assertEqual(foo2.value, 0)

        Foo.__init__._reset()

        foo3 = Foo(3)
        self.assertEqual(foo3.value, 3)
        foo4 = Foo(4)
        self.assertEqual(foo4.value, 0)

    def test_classmethod(self):
        """Test that classmethod is called just once."""

        class Foo:
            value: int = 0

            @classmethod
            @call_once
            def increase(cls):
                cls.value += 1

        foo = Foo()
        foo.increase()
        self.assertEqual(foo.value, 1)
        foo.increase()
        self.assertEqual(foo.value, 1)

    def test_staticmethod(self):
        """Test that staticmethod is called just once."""

        class Foo:
            value: int = 0

            @staticmethod
            @call_once
            def increase():
                Foo.value += 1

        foo = Foo()
        foo.increase()
        self.assertEqual(foo.value, 1)
        foo.increase()
        self.assertEqual(foo.value, 1)

    def test_callonce_inheritance(self):
        """Test that @call_once is inherited."""

        class Parent:
            @call_once
            def __init__(self, value: int):
                self.value = value

            @property
            def value(self):
                return self._value

            @value.setter
            def value(self, value: int):
                self._value = value

        class Child(Parent):
            def __init__(self, value: int):
                super().__init__(value)

        child_1 = Child(1)
        child_2 = Child(2)
        self.assertEqual(child_1.value, 1)
        with self.assertRaises(AttributeError) as exc_info:
            getattr(child_2, "value")
        self.assertEqual(str(exc_info.exception), "'Child' object has no attribute '_value'")


class TestLock(unittest.TestCase):
    """Test @lock decorator."""

    def test_lock_unlock(self):
        """Test lock(), unlock() and 'locked' property."""

        @lock
        class TestLock:
            pass

        test_lock = TestLock()

        self.assertEqual(test_lock.locked, False)
        test_lock.lock()
        self.assertEqual(test_lock.locked, True)
        test_lock.unlock()
        self.assertEqual(test_lock.locked, False)

    def test_unlocking_of_not_locked_lock(self):
        """Test that exception is not raised when we try to unlock not locked lock."""

        @lock
        class TestLock:
            pass

        test_lock = TestLock()

        self.assertEqual(test_lock.locked, False)
        test_lock.unlock()
        self.assertEqual(test_lock.locked, False)

    def test_locking_of_locked_lock(self):
        """Test that lock can be locked multiple times."""

        @lock
        class TestLock:
            pass

        test_lock = TestLock()

        test_lock.lock()
        self.assertEqual(test_lock.locked, True)
        test_lock.lock()
        self.assertEqual(test_lock.locked, True)

    def test_context_manager(self):
        """Test lock as context manager."""

        @lock
        class TestLock:
            pass

        with TestLock() as test_lock:
            self.assertEqual(test_lock.locked, True)
        self.assertEqual(test_lock.locked, False)

    def test_cannot_set_attribute(self):
        """Test that it's not possible to assign values to 'locked' attribute."""

        @lock
        class TestLock:
            pass

        test_lock = TestLock()

        with self.assertRaises(AttributeError):
            test_lock.locked = True


class TestComplexSingleton(unittest.TestCase):
    """Test combinations of @singletonize, @call_once and @lock."""

    def test_init(self):
        """Test that __init__ of singleton is called just once."""

        @singleton
        class Singleton:
            value = 0

            @call_once
            def __init__(self):
                self.value += 1

        singleton_1 = Singleton()
        singleton_2 = Singleton()
        self.assertEqual(singleton_1.value, 1)
        self.assertEqual(singleton_2.value, 1)

    def test_callonce_inheritance(self):
        """Test that @call_once is inherited in singletons."""

        @singleton
        class Parent:
            @call_once
            def __init__(self, value: int):
                self.value = value

            @property
            def value(self):
                return self._value

            @value.setter
            def value(self, value: int):
                self._value = value

        class Child(Parent):
            def __init__(self, value: int):
                super().__init__(value)

        child_1 = Child(1)
        self.assertEqual(child_1.value, 1)
        child_2 = Child(2)
        self.assertEqual(child_1, child_2)
        self.assertEqual(child_2.value, 1)

    def test_exception_does_not_prevent_lock_initialization(self):
        """Test that function is marked as called even if it raises an exception."""

        @lock
        @singleton
        class TestLock:
            @call_once
            def __init__(self):
                raise Exception("I am designed to fail exactly once.")

        with self.assertRaises(Exception):
            TestLock()

        self.assertIsNotNone(TestLock._instance)
        test_lock_1_id = id(TestLock._instance)

        test_lock_2 = TestLock()
        self.assertEqual(id(test_lock_2), test_lock_1_id)

    def test_unlock_with_multiple_instances(self):
        """Test that singleton lock is unlocked for all instances."""

        @lock
        @singleton
        class TestLock:
            pass

        test_lock_1 = TestLock()
        test_lock_2 = TestLock()

        self.assertEqual(test_lock_1, test_lock_2)

        test_lock_1.lock()
        self.assertEqual(test_lock_1.locked, True)
        self.assertEqual(test_lock_2.locked, True)

        test_lock_2.lock()
        self.assertEqual(test_lock_1.locked, True)
        self.assertEqual(test_lock_2.locked, True)

        test_lock_1.unlock()
        self.assertEqual(test_lock_1.locked, False)
        self.assertEqual(test_lock_2.locked, False)

    def test_threading(self):
        """Test that singletons are one object in two threads."""

        @singleton
        class Singleton:
            @call_once
            def __init__(self, foo: str, bar: str):
                self.foo = foo
                self.bar = bar

        def thread_function(foo, bar) -> None:
            Singleton(foo, bar)
            time.sleep(0.3)

        thread_1 = threading.Thread(target=thread_function, args=("foo", "bar"))
        thread_2 = threading.Thread(target=thread_function, args=("FOO", "BAR"))

        thread_1.start()
        time.sleep(0.1)

        thread_2.start()
        time.sleep(0.1)

        thread_1.join(timeout=0.5)
        thread_2.join(timeout=0.5)

        singleton_1 = Singleton()
        self.assertEqual(singleton_1.foo, "foo")
        self.assertEqual(singleton_1.bar, "bar")

    def test_lock_threading(self):
        """Test that singleton locks are one object in two threads."""

        @lock
        @singleton
        class TestLock:
            foo: str
            bar: str

        def thread_function(foo, bar) -> None:
            with TestLock() as test_lock:
                test_lock.foo = foo
                test_lock.bar = bar
                time.sleep(0.3)

        thread_1 = threading.Thread(target=thread_function, args=("foo", "bar"))
        thread_2 = threading.Thread(target=thread_function, args=("FOO", "BAR"))

        thread_1.start()
        time.sleep(0.1)

        thread_2.start()
        time.sleep(0.1)

        thread_1.join(timeout=0.5)
        thread_2.join(timeout=0.5)

        lock_1 = TestLock()
        self.assertEqual(lock_1.foo, "FOO")
        self.assertEqual(lock_1.bar, "BAR")
