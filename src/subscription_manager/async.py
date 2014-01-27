#
# Async wrapper module for managerlib methods, with glib integration
#
# Copyright (c) 2010 Red Hat, Inc.
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
#

import Queue
import threading

import gobject


class AsyncPool(object):

    def __init__(self, pool):
        self.pool = pool
        self.queue = Queue.Queue()

    def _run_refresh(self, active_on, callback, data):
        """
        method run in the worker thread.
        """
        try:
            self.pool.refresh(active_on)
            self.queue.put((callback, data, None))
        except Exception, e:
            self.queue.put((callback, data, e))

    def _watch_thread(self):
        """
        glib idle method to watch for thread completion.
        runs the provided callback method in the main thread.
        """
        try:
            (callback, data, error) = self.queue.get(block=False)
            callback(data, error)
            return False
        except Queue.Empty:
            return True

    def refresh(self, active_on, callback, data=None):
        """
        Run pool stash refresh asynchronously.
        """
        gobject.idle_add(self._watch_thread)
        threading.Thread(target=self._run_refresh,
                args=(active_on, callback, data)).start()


class AsyncResponse(object):

    def __init__(self, function, callback, *args, **kwargs):
        self.result_queue = Queue.Queue()
        threading.Thread(target=self._execute_function,
                args=([function, callback] + list(args)), kwargs=kwargs).start()

    def read(self):
        result = self.result_queue.get(block=True)
        # Throw the exception in the main thread if it arises
        if isinstance(result, Exception):
            raise result
        return result

    def _execute_function(self, function, callback, *args, **kwargs):
        try:
            result = function(*args, **kwargs)
            callback(result, None)
        except Exception, e:
            result = e
            callback(None, e)
        self.result_queue.put(result)


class AsyncCP(object):

    def __init__(self, uep):
        self.uep = uep

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        attribute = getattr(self.uep, name)
        if hasattr(attribute, '__call__'):
            async_function = self.build_function(attribute)
            return async_function
        # Don't need to modify attributes
        return attribute

    def dummy_callback(self, data, exception):
        pass

    def build_function(self, uep_function):
        def generated_function(*args, **kwargs):
            # Make sure async args are removed even if we aren't using them
            threaded = kwargs.pop('threaded', None)
            # If None is supplied, we still want dummy_callback
            callback = kwargs.pop('callback', None) or self.dummy_callback
            if threaded:
                return AsyncResponse(uep_function, callback, *args, **kwargs)
            return uep_function(*args, **kwargs)  # Passthrough
        return generated_function
