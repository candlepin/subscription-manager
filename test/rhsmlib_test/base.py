#! /usr/bin/env python
from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
from tempfile import NamedTemporaryFile

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import sys
import dbus
import dbus.lowlevel
import dbus.bus
import dbus.mainloop.glib
import functools
import logging
import mock
import threading
import time
import six

from six.moves import queue
from rhsmlib.dbus import constants, server
from subscription_manager.identity import Identity

# Set DBus mainloop early in test run (test import time!)
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
log = logging.getLogger(__name__)


class TestUtilsMixin(object):
    def assert_items_equals(self, a, b):
        """Assert that two lists contain the same items regardless of order."""
        if sorted(a) != sorted(b):
            self.fail("%s != %s" % (a, b))
        return True

    def write_temp_file(self, data):
        # create a temp file for use as a config file. This should get cleaned
        # up magically when it is closed so make sure to close it!
        fid = NamedTemporaryFile(mode='w+', suffix='.tmp')
        fid.write(data)
        fid.seek(0)
        return fid


class InjectionMockingTest(unittest.TestCase):
    def setUp(self):
        super(InjectionMockingTest, self).setUp()
        injection_patcher = mock.patch("rhsmlib.dbus.base_object.inj.require")
        self.mock_require = injection_patcher.start()
        self.addCleanup(injection_patcher.stop)
        self.mock_require.side_effect = self.injection_definitions

    def injection_definitions(self, *args, **kwargs):
        '''Override this method to control what the injector returns'''
        raise NotImplementedError("Subclasses should define injected objects")


class DBusObjectTest(unittest.TestCase):
    '''Subclass of unittest.TestCase use for testing DBus methods in the same process.  During setUp this
    class starts a thread that makes a DBus connection and exposes some objects on the bus.  The main thread
    blocks until the connection has completed.

    When the main thread reaches a test case, the test case needs to call dbus_request() and pass in a DBus
    proxy object and a function to run after the DBus call has received a response.  The dbus_request method
    starts another thread that makes an async call to the thread serving the objects under test and then
    blocks the main thread (the DBus call must be asynchronous to avoid deadlock).  The function passed to
    dbus_request is run and then dbus_request unblocks the main thread.
    '''
    def setUp(self):
        super(DBusObjectTest, self).setUp()
        self.started_event = threading.Event()
        self.stopped_event = threading.Event()
        self.handler_complete_event = threading.Event()
        # This is up a level because it needs to be defined before the server is instantiated
        self.mock_identity = mock.Mock(spec=Identity, name="Identity").return_value
        self.mock_identity.cert_dir_path = "path.txt"  # must be a string, otherwise it is set as a mock object
        # and os.path throws type error, causing tests to hang

        # If we don't use a BusConnection and use say dbus.SessionBus() directly, each test will end up
        # getting old bus connections since the dbus bindings cache bus connections.  You can use the private
        # kwarg to tell dbus.SessionBus/SystemBus not to cache, but that's deprecated.
        self.server_thread = ServerThread(kwargs={
            'object_classes': self.dbus_objects(),
            'bus_name': self.bus_name(),
            'bus_class': dbus.bus.BusConnection,
            'bus_kwargs': self.bus_kwargs,
            'started_event': self.started_event,
            'stopped_event': self.stopped_event,
        })
        self.started_event.wait()
        self.result_queue = queue.Queue(maxsize=1)
        self.addCleanup(self.stop_server)
        sender_patcher = mock.patch("rhsmlib.client_info.DBusSender.get_cmd_line")
        self.mock_sender_get_cmd_line = sender_patcher.start()
        self.mock_sender_get_cmd_line.return_value = "nose-unit-test"

    def stop_server(self):
        self.server_thread.stop()
        self.stopped_event.wait()

    @property
    def bus_kwargs(self):
        if os.geteuid() == 0:
            return {'address_or_type': dbus.Bus.TYPE_SYSTEM}
        else:
            return {'address_or_type': dbus.Bus.TYPE_SESSION}

    def proxy_for(self, path):
        return dbus.bus.BusConnection(**self.bus_kwargs).get_object(self.bus_name(), path)

    def dbus_request(self, reply_handler, proxy, proxy_args=None, error_handler=None):
        '''This method makes an async request to the server thread and *does not* block.  Not blocking means
        that the rest of your test case will run potentially before the async callback finishes.  If you
        use this method, you will need to call self.handler_complete_event.wait() at the end of your
        test so that the test runner itself will block until the async callback finishes.'''

        DBusRequestThread(kwargs={
            'proxy': proxy,
            'proxy_args': proxy_args,
            'reply_handler': reply_handler,
            'error_handler': error_handler,
            'handler_complete_event': self.handler_complete_event,
            'queue': self.result_queue
        })
        self.handler_complete_event.wait()

        # Raise any exception generated by the handlers.  I.e. actually fail a test if assertions failed in
        # the DBusRequestThread
        if not self.result_queue.empty():
            result = self.result_queue.get()
            six.reraise(*result)

    def dbus_objects(self):
        '''This method should return a list of DBus service classes that need to be instantiated in the
        server thread.  Generally this should just be a list containing the class under test.
        In that list, you can also pass in a tuple composed of the object class and a dictionary of keyword
        arguments for the object's constructor
        '''
        raise NotImplementedError('Subclasses should define what DBus objects to test')

    def bus_name(self):
        '''This method should return the bus name that the server thread should use'''
        return constants.BUS_NAME


class ServerThread(threading.Thread):
    def __init__(self, **kwds):
        super(ServerThread, self).__init__(name=self.__class__.__name__, **kwds)
        kwargs = kwds['kwargs']
        self.bus_class = kwargs.get('bus_class', dbus.bus.BusConnection(dbus.bus.BUS_SESSION))
        self.bus_name = kwargs.get('bus_name', constants.BUS_NAME)
        self.object_classes = kwargs.get('object_classes', [])
        self.started_event = kwargs['started_event']
        self.stopped_event = kwargs['stopped_event']
        self.bus_kwargs = kwargs['bus_kwargs']
        self.server = None
        self.start()

    def run(self):
        try:
            self.server = server.Server(
                bus_class=self.bus_class,
                bus_name=self.bus_name,
                object_classes=self.object_classes,
                bus_kwargs=self.bus_kwargs)
            self.server.run(self.started_event, self.stopped_event)
        except Exception as e:
            log.exception(e)
            self.started_event.set()

    def stop(self):
        if self.server:
            self.server.shutdown()


class DBusRequestThread(threading.Thread):
    def __init__(self, **kwds):
        super(DBusRequestThread, self).__init__(name=self.__class__.__name__, **kwds)
        kwargs = kwds['kwargs']
        self.queue = kwargs['queue']
        self.proxy = kwargs['proxy']
        self.proxy_args = kwargs['proxy_args']

        if self.proxy_args is None:
            self.proxy_args = []

        self.reply_handler = self.reply_wrap(kwargs['reply_handler'])
        # If no error_handler is given, error_wrap will just raise the DBus error
        self.error_handler = self.error_wrap(kwargs.get('error_handler'))

        self.handler_complete_event = kwargs['handler_complete_event']
        self.start()

    def reply_wrap(self, func):
        def dummy(*args, **kwargs):
            pass

        if func is None:
            func = dummy

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception:
                self.queue.put(sys.exc_info())
            finally:
                self.handler_complete_event.set()

        return wrapper

    def error_wrap(self, func=None):
        def dummy(*args, **kwargs):
            raise args[0]

        if func is None:
            func = dummy

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception:
                self.queue.put(sys.exc_info())
            finally:
                self.handler_complete_event.set()

        return wrapper

    def run(self):
        try:
            # Under some circumstances (mismatch in arguments versus signature for example) the call to
            # self.proxy fails but does not invoke the error handler or throw an exception.
            #
            # In those cases, we end up deadlocking since handler_complete_event is never set.
            # I am not sure why, but a very brief pause before running the proxy is sufficient to
            # solve the problem.
            #
            # The proper solution would be to block here until some event but I'm not sure what event that is
            time.sleep(0.001)
            self.proxy(
                *self.proxy_args,
                reply_handler=self.reply_handler,
                error_handler=self.error_handler)
        except Exception as e:
            # If the proxy is messed up some how, we still need to push the error to the main thread
            log.exception(e)
            self.queue.put(sys.exc_info())

            # Wake the main thread.
            self.handler_complete_event.set()
