import threading
import time
import unittest

from rhsm.utils import (
    parse_bool,
    cmd_name,
    singleton,
    call_once,
    lock,
)


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


class TestParseBool(unittest.TestCase):
    def test_true(self):
        self.assertTrue(parse_bool("1"))
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("True"))
        self.assertTrue(parse_bool("TRUE"))
        self.assertTrue(parse_bool("yes"))
        self.assertTrue(parse_bool("Yes"))
        self.assertTrue(parse_bool("YES"))
        self.assertTrue(parse_bool("on"))
        self.assertTrue(parse_bool("On"))
        self.assertTrue(parse_bool("ON"))

    def test_false(self):
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("False"))
        self.assertFalse(parse_bool("FALSE"))
        self.assertFalse(parse_bool("no"))
        self.assertFalse(parse_bool("No"))
        self.assertFalse(parse_bool("NO"))
        self.assertFalse(parse_bool("off"))
        self.assertFalse(parse_bool("Off"))
        self.assertFalse(parse_bool("OFF"))

    def test_exception(self):
        self.assertRaises(ValueError, parse_bool, "foo")
        # These values could also be read as boolean, but we do not support them
        self.assertRaises(ValueError, parse_bool, "enabled")
        self.assertRaises(ValueError, parse_bool, "disabled")


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
