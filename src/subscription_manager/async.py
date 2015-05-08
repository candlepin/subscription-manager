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
import gettext

from subscription_manager import ga
from subscription_manager.entcertlib import Disconnected
from subscription_manager.managerlib import fetch_certificates
from subscription_manager.injection import IDENTITY, \
        PLUGIN_MANAGER, CP_PROVIDER, require

_ = gettext.gettext


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
        ga.GObject.idle_add(self._watch_thread)
        threading.Thread(target=self._run_refresh,
                args=(active_on, callback, data)).start()


class AsyncBind(object):

    def __init__(self, certlib):
        self.cp_provider = require(CP_PROVIDER)
        self.identity = require(IDENTITY)
        self.plugin_manager = require(PLUGIN_MANAGER)
        self.certlib = certlib

    def _run_bind(self, pool, quantity, bind_callback, cert_callback, except_callback):
        try:
            self.plugin_manager.run("pre_subscribe", consumer_uuid=self.identity.uuid,
                    pool_id=pool['id'], quantity=quantity)
            ents = self.cp_provider.get_consumer_auth_cp().bindByEntitlementPool(self.identity.uuid, pool['id'], quantity)
            self.plugin_manager.run("post_subscribe", consumer_uuid=self.identity.uuid, entitlement_data=ents)
            if bind_callback:
                ga.GObject.idle_add(bind_callback)
            fetch_certificates(self.certlib)
            if cert_callback:
                ga.GObject.idle_add(cert_callback)
        except Exception, e:
            ga.GObject.idle_add(except_callback, e)

    def _run_unbind(self, serial, selection, callback, except_callback):
        """
        Selection is only passed to maintain the gui error message.  This
        can be removed, because it doesn't really give us any more information
        """
        try:
            self.cp_provider.get_consumer_auth_cp().unbindBySerial(self.identity.uuid, serial)
            try:
                self.certlib.update()
            except Disconnected, e:
                pass

            if callback:
                ga.GObject.idle_add(callback)
        except Exception, e:
            ga.GObject.idle_add(except_callback, e, selection)

    def bind(self, pool, quantity, except_callback, bind_callback=None, cert_callback=None):
        threading.Thread(target=self._run_bind,
                args=(pool, quantity, bind_callback, cert_callback, except_callback)).start()

    def unbind(self, serial, selection, callback, except_callback):
        threading.Thread(target=self._run_unbind,
                args=(serial, selection, callback, except_callback)).start()
