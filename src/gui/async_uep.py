from threading import Lock
from threading import Thread

import glib

from connection import UEPConnection
import managerlib


class _Message(object):

    def __init__(self, body, callback):
        self.body = body
        self.callback = callback


class _MessageQueue(object):

    def __init__(self):
        self._messages = []
        self._lock = Lock()

    def set_message(self, message):
        self._lock.acquire()
        self._messages.append(message)
        self._lock.release()

    def get_message(self):
        self._lock.acquire()
        if len(self._messages) == 0:
            message = None
        else:
            message = self._messages.pop(-1)
        self._lock.release()
        return message


class _WorkItem(object):

    def __init__(self, queue, callback, error_handler, method, *args):
        self._method = method
        self._args = args
        self._queue = queue
        self._callback = callback
        self._error_handler = error_handler

    def __call__(self):
        print "SLEEPING"
        import time
        time.sleep(3)
        print "CALLING"
        try:
            res = self._method(*self._args)
        except Exception, e:
            self._queue.set_message(_Message(e, self._error_handler))
            return
        self._queue.set_message(_Message(res, self._callback))

# Async decorator. makes callback and error handling args implicit,
# and at the beginning of the call.
# XXX should they be explicit?
def async(f):
    # self is self of the async.UEP
    def new_f(self, callback, error_handler, *args):
        self._launch_async(callback, error_handler, f, *args)
    return new_f

class UEP(object):

    def __init__(self, host, ssl_port, cert_file=None, key_file=None):
        if cert_file and key_file:
            self._uep = UEPConnection(host, ssl_port, "/candlepin", cert_file,
                    key_file)
        else:
            self._uep = UEPConnection(host, ssl_port, "/candlepin")

        self._worker = None
        self._queue = _MessageQueue()

    def _check_messages(self):
        message = self._queue.get_message()
        if message:
            self._worker = None
            # remove from glib's idle queue
            message.callback(message.body)
            return False
        return True

    def _launch_async(self, callback, error_handler, method, *args):
        work_item = _WorkItem(self._queue, callback, error_handler, method,
                self, *args)
        self._worker = Thread(None, work_item)
        glib.idle_add(self._check_messages)
        self._worker.start()

    def unBindBySerialNumber(self, uuid, psubs):
        return self._uep.unBindBySerialNumber(uuid, psubs)

    @async
    def unregisterConsumer(self, uuid):
        return self._uep.unregisterConsumer(uuid)

    @async
    def registerConsumer(self, username, password, register_info):
        return self._uep.registerConsumer(username, password, register_info)

    def bindByProduct(self, uuid, phash):
        return self._uep.bindByProduct(uuid, phash)

    def bindByRegNumber(self, uuid, reg_token):
        return self._uep.bindByRegNumber(uuid, reg_token)

    def bindByEntitlementPool(self, uuid, pool):
        return self._uep.bindByEntitlementPool(uuid, pool)

    def getCompatibleSubscriptions(self, uuid):
        return managerlib.getCompatibleSubscriptions(self._uep, uuid)

    def getAllAvailableSubscriptions(self, uuid):
        return managerlib.getAllAvailableSubscriptions(self._uep, uuid)

    def getAvailableEntitlements(self, uuid):
        return managerlib.getAvailableEntitlements(self_uep, uuid)
