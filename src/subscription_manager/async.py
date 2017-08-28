from __future__ import print_function, division, absolute_import

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

import threading
import sys

from six.moves import queue

from subscription_manager.ga import GObject as ga_GObject
from subscription_manager.entcertlib import Disconnected
from subscription_manager.managerlib import fetch_certificates
from subscription_manager.injection import IDENTITY, \
        PLUGIN_MANAGER, CP_PROVIDER, require

from rhsmlib.services import attach, entitlement


class AsyncPool(object):

    def __init__(self, pool):
        self.pool = pool
        self.queue = queue.Queue()

    def _run_refresh(self, active_on, callback, data):
        """
        method run in the worker thread.
        """
        try:
            self.pool.refresh(active_on)
            self.queue.put((callback, data, None))
        except Exception:
            self.queue.put((callback, data, sys.exc_info()))

    def _watch_thread(self):
        """
        glib idle method to watch for thread completion.
        runs the provided callback method in the main thread.
        """
        try:
            (callback, data, error) = self.queue.get(block=False)
            callback(data, error)
            return False
        except queue.Empty:
            return True

    def refresh(self, active_on, callback, data=None):
        """
        Run pool stash refresh asynchronously.
        """
        ga_GObject.idle_add(self._watch_thread)
        threading.Thread(target=self._run_refresh, name="AsyncPoolRefreshThread",
                args=(active_on, callback, data)).start()


class AsyncBind(object):

    def __init__(self, certlib):
        self.cp_provider = require(CP_PROVIDER)
        self.identity = require(IDENTITY)
        self.plugin_manager = require(PLUGIN_MANAGER)
        self.certlib = certlib

    def _run_bind(self, pool, quantity, bind_callback, cert_callback, except_callback):
        try:
            attach.AttachService(self.cp_provider.get_consumer_auth_cp()).attach_pool(pool['id'], quantity)
            if bind_callback:
                ga_GObject.idle_add(bind_callback)
            fetch_certificates(self.certlib)
            if cert_callback:
                ga_GObject.idle_add(cert_callback)
        except Exception:
            ga_GObject.idle_add(except_callback, sys.exc_info())

    def _run_unbind(self, serial, selection, callback, except_callback):
        """
        Selection is only passed to maintain the gui error message.  This
        can be removed, because it doesn't really give us any more information
        """
        try:
            ent_service = entitlement.EntitlementService(self.cp_provider.get_consumer_auth_cp())
            ent_service.remove_entitlements_by_serials([serial])
            try:
                self.certlib.update()
            except Disconnected:
                pass

            if callback:
                ga_GObject.idle_add(callback)
        except Exception:
            ga_GObject.idle_add(except_callback, sys.exc_info(), selection)

    def bind(self, pool, quantity, except_callback, bind_callback=None, cert_callback=None):
        threading.Thread(target=self._run_bind, name="AsyncBindBindThread",
                args=(pool, quantity, bind_callback, cert_callback, except_callback)).start()

    def unbind(self, serial, selection, callback, except_callback):
        threading.Thread(target=self._run_unbind, name="AsyncBindUnbindThread",
                args=(serial, selection, callback, except_callback)).start()


class AsyncRepoOverridesUpdate(object):

    def __init__(self, overrides_api):
        self.overrides_api = overrides_api
        self.identity = require(IDENTITY)

    def _load_data(self, success_callback, except_callback):
        try:
            # pull the latest overrides from the cache which will be the ones from the server.
            current_overrides = self.overrides_api.get_overrides(self.identity.uuid) or []

            # Fetch the repositories from repolib without any overrides applied.
            # We do this so that we can tell if anything has been modified by
            # overrides.
            current_repos = self.overrides_api.repo_lib.get_repos(apply_overrides=False)

            self._process_callback(success_callback, current_overrides, current_repos)
        except Exception:
            self._process_callback(except_callback, sys.exc_info())

    def _update(self, to_add, to_remove, success_callback, except_callback):
        '''
        Processes the override mapping and sends the overrides to the server for addition/removal.
        '''
        try:
            # TODO: At some point we should look into providing a single API call that can handle
            #       additions and removals in the same call (currently not supported by server).
            current_overrides = None
            if len(to_add) > 0:
                current_overrides = self.overrides_api.add_overrides(self.identity.uuid, to_add)

            if len(to_remove) > 0:
                current_overrides = self.overrides_api.remove_overrides(self.identity.uuid, to_remove)

            if current_overrides:
                self.overrides_api.update(current_overrides)

            # Fetch the repositories from repolib without any overrides applied.
            # We do this so that we can tell if anything has been modified by
            # overrides.
            current_repos = self.overrides_api.repo_lib.get_repos(apply_overrides=False)

            self._process_callback(success_callback, current_overrides, current_repos)
        except Exception:
            self._process_callback(except_callback, sys.exc_info())

    def _remove_all(self, repo_ids, success_callback, except_callback):
        try:
            current_overrides = self.overrides_api.remove_all_overrides(self.identity.uuid, repo_ids)
            self.overrides_api.update(current_overrides)

            # Fetch the repositories from repolib without any overrides applied.
            # We do this so that we can tell if anything has been modified by
            # overrides.
            current_repos = self.overrides_api.repo_lib.get_repos(apply_overrides=False)

            self._process_callback(success_callback, current_overrides, current_repos)
        except Exception:
            self._process_callback(except_callback, sys.exc_info())

    def _process_callback(self, callback, *args):
        ga_GObject.idle_add(callback, *args)

    def load_data(self, success_callback, failure_callback):
        threading.Thread(target=self._load_data, name="AsyncRepoOverridesUpdateLoadDataThread",
                         args=(success_callback, failure_callback)).start()

    def update_overrides(self, to_add, to_remove, success_callback, except_callback):
        threading.Thread(target=self._update, name="AsyncRepoOverridesUpdateUpdateOverridesThread",
                         args=(to_add, to_remove, success_callback, except_callback)).start()

    def remove_all_overrides(self, repo_ids, success_callback, except_callback):
        threading.Thread(target=self._remove_all, name="AsyncRepoOverridesUpdateRemoveAllOverridesThread",
                         args=(repo_ids, success_callback, except_callback)).start()
