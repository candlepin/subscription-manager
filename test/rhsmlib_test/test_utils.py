from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

"""
Unit tests for module rhsmlib.utils.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import threading
import time

from rhsmlib.utils import Singleton, no_reinitialization


class Child(Singleton):
    """
    Class used for testing of Singleton subclass
    """
    @no_reinitialization
    def __init__(self, foo=None, bar=None):
        self._foo = foo
        self._bar = bar

    @property
    def foo(self):
        with self:
            return self._foo

    @foo.setter
    def foo(self, value):
        with self:
            self._foo = value

    @property
    def bar(self):
        with self:
            return self._bar

    @bar.setter
    def bar(self, value):
        with self:
            self._bar = value


class GrandSon(Child):
    """
    Another class used for testing of Singleton subclass.
    In this subclass is re-initialization of Singleton forbidden
    using decorator @no_reinitialization
    """
    @no_reinitialization
    def __init__(self, foo=None, bar=None):
        super(GrandSon, self).__init__(foo=foo, bar=bar)


class GrandDaughter(Child):
    """
    Another class used for testing of Singleton subclass.
    Note that Child uses no_reinitialization and this
    class doesn't.
    """
    def __init__(self, foo=None, bar=None):
        super(GrandDaughter, self).__init__(foo=foo, bar=bar)


class Kid(Singleton):
    """
    Another class used for testing of Singleton subclass. Calling
    GrandDaughter() with new arguments will cause re-initialization
    of singleton. Note that Child uses no_reinitialization and this
    class doesn't
    """
    def __init__(self, foo=None, bar=None):
        self.foo = foo
        self.bar = bar


class SpoiledChild(Singleton):
    """
    Another class used for testing proper unlocking of singleton, when
    __init__ method raises some exception.
    """

    @no_reinitialization
    def __init__(self):
        raise Exception


class SingletonTestCase(unittest.TestCase):

    @staticmethod
    def _reset_singleton(clazz):
        """
        Method for resetting class
        :param clazz: class to be reseted
        :return: None
        """
        clazz._instance = None
        clazz._initialized = False
        clazz._lock = None

    def setUp(self):
        """
        This method all singleton instances before each test
        """
        # Add here every child of Singleton to be deleted before each test
        self._reset_singleton(Singleton)
        self._reset_singleton(Child)
        self._reset_singleton(GrandSon)
        self._reset_singleton(GrandDaughter)
        self._reset_singleton(Kid)
        self._reset_singleton(SpoiledChild)

    def test_is_singleton(self):
        """
        Simple test of singleton
        """
        s1 = Singleton()
        s2 = Singleton()
        self.assertEqual(id(s1), id(s2))

    def test_simple_locking_and_unlocking(self):
        """
        Test simple locking and unlocking using lock() and unlock()
        """
        s = Singleton()
        # Note: the s._lock._is_owned() should not be used in production, because
        # _lock and _is_owned are not part of public API. It is used here only for
        # testing purpose
        self.assertEqual(s._lock._is_owned(), False)
        s.lock()
        self.assertEqual(s._lock._is_owned(), True)
        s.unlock()
        self.assertEqual(s._lock._is_owned(), False)

    def test_unlocking_of_not_locked_lock(self):
        """
        Test that exception is not raised, when we try to unlock not locked lock
        """
        s = Singleton()
        s.unlock()
        # Note: the s._lock._is_owned() should not be used in production, because
        # _lock and _is_owned are not part of public API. It is used here only for
        # testing purpose
        self.assertEqual(s._lock._is_owned(), False)

    def test_locking_using_enter_exit(self):
        """
        Simple test of locking using with statement
        """
        with Singleton() as s:
            self.assertEqual(s._lock._is_owned(), True)
        s = Singleton()
        self.assertEqual(s._lock._is_owned(), False)

    def test_is_subclass_singleton(self):
        """
        Test of singleton and child of singleton

        """
        # First create parent to be sure that parent do not influence sub-classes
        s = Singleton()

        # Do asserts of sub-class
        self.assertEqual(Child._instance, None)
        self.assertEqual(Child._initialized, False)
        self.assertEqual(Child._lock, None)

        # Do own tests of sub-class
        ch1 = Child()
        ch2 = Child()
        self.assertNotEqual(id(s), id(ch1))
        self.assertEqual(id(ch1), id(ch2))

    def test_child_is_initialized(self):
        """
        Test that instance of class is initialized
        """
        self.assertEqual(Child._instance, None)
        self.assertEqual(Child._initialized, False)
        self.assertEqual(Child._lock, None)

        ch = Child("foo", bar="bar")

        self.assertEqual(ch.bar, "bar")
        self.assertEqual(ch.foo, "foo")
        self.assertEqual(ch._initialized, True)
        self.assertIsNotNone(ch._lock)

    def test_another_child_is_not_reinitialized(self):
        """
        Test of decorator no_reinitialization
        """
        ch1 = Child("foo", bar="bar")
        self.assertEqual(ch1.bar, "bar")
        self.assertEqual(ch1.foo, "foo")
        ch2 = Child("FOO", bar="BAR")
        # This singleton should still have still old values
        self.assertEqual(ch2.bar, "bar")
        self.assertEqual(ch2.foo, "foo")

    def test_grand_son(self):
        """
        Test of decorator no_reinitialization (subclass of child)
        """
        ch1 = Child("foo", bar="bar")
        ch2 = Child("foolish", bar="barista")
        gs = GrandSon("FOO", bar="BAR")
        self.assertNotEqual(id(ch1), id(gs))
        self.assertEqual(ch1.foo, "foo")
        self.assertEqual(ch2.bar, "bar")
        self.assertEqual(gs.foo, "FOO")
        self.assertEqual(gs.bar, "BAR")

    def test_grand_daughter(self):
        """
        This test is intended for testing class without decorator no_reinitialization
        """
        # Create instance of singleton with some arguments
        gd1 = GrandDaughter("foo", bar="bar")
        self.assertEqual(gd1.foo, "foo")
        self.assertEqual(gd1.bar, "bar")
        # No try to get instance with some different arguments
        gd2 = GrandDaughter("FOO", bar="BAR")
        self.assertEqual(id(gd1), id(gd2))
        # This singleton should have new values
        self.assertEqual(gd2.foo, "foo")
        self.assertEqual(gd2.bar, "bar")

    def test_kid(self):
        """
        This test is intended for testing class without decorator no_reinitialization. Parent
        of this class does not use the decorator no_reinitialization
        """
        # Create instance of singleton with some arguments
        kid1 = Kid("foo", bar="bar")
        self.assertEqual(kid1.foo, "foo")
        self.assertEqual(kid1.bar, "bar")
        # No try to get instance with some different arguments
        kid2 = Kid("FOO", bar="BAR")
        self.assertEqual(id(kid1), id(kid2))
        # This singleton should have new values
        self.assertEqual(kid2.foo, "FOO")
        self.assertEqual(kid2.bar, "BAR")

    def test_release_lock_after_exception_in_init(self):
        """
        Test proper releasing of singleton, when __init__ method is not implemented
        as expected (it raises some exception)
        """
        # Capture exception
        self.assertRaises(Exception, SpoiledChild)

        # Test that it was initialized despite exception
        self.assertIsNotNone(SpoiledChild._instance)
        self.assertEqual(SpoiledChild._instance._initialized, True)
        spoiled_child_id = id(SpoiledChild._instance)

        # Test that another calling of SpoiledChild is not destructive
        spoiled_child = SpoiledChild()
        self.assertEqual(id(spoiled_child), spoiled_child_id)

    def test_singleton_and_threading(self):
        """
        Test creating singletons in two threads
        """

        def thread_function(foo, bar):
            """
            Dummy thread function for testing singleton
            :param foo: foo argument
            :param bar: bar argument
            :return: None
            """
            Child(foo=foo, bar=bar)
            time.sleep(0.3)

        thread01 = threading.Thread(target=thread_function, args=("foo", "bar"))
        thread01.start()
        time.sleep(0.1)
        thread02 = threading.Thread(target=thread_function, args=("FOO", "BAR"))
        thread02.start()
        time.sleep(0.1)
        thread01.join()
        thread02.join()

        # Create testing singleton
        test_child = Child()
        self.assertEqual(test_child.bar, "bar")
        self.assertEqual(test_child.foo, "foo")

    def test_singleton_threading_and_locking(self):
        """
        Test creating singletons in two threads and locking of singleton
        """

        def thread_function(foo, bar):
            """
            Dummy thread function for testing singleton
            :param foo: foo argument
            :param bar: bar argument
            :return: None
            """
            with Child() as child:
                child.foo = foo
                child.bar = bar
                time.sleep(0.3)

        # Create testing singleton
        test_child = Child()

        thread01 = threading.Thread(target=thread_function, args=("foo", "bar"))
        thread01.start()
        time.sleep(0.1)

        self.assertEqual(test_child.bar, "bar")
        self.assertEqual(test_child.foo, "foo")

        thread02 = threading.Thread(target=thread_function, args=("FOO", "BAR"))
        thread02.start()
        time.sleep(0.1)

        self.assertEqual(test_child.bar, "BAR")
        self.assertEqual(test_child.foo, "FOO")

        thread01.join()
        thread02.join()
