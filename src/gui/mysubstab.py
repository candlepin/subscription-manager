#
# GUI Module for standalone subscription-manager - 'My Subscriptions' tab
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Justin Harris <jharris@redhat.com>
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

import os
import gtk

import managergui

import logutil
log = logutil.getLogger(__name__)

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

DIR = os.path.dirname(__file__)
GLADE_XML = os.path.join(DIR, "data/mysubs.glade")

class MySubscriptionsTab:

    def __init__(self, backend, consumer):
        self.backend = backend
        self.consumer = consumer

        glade = gtk.glade.XML(GLADE_XML)
        self.subscription_view = glade.get_widget("subscription_view")
        self.content = glade.get_widget("content")

        # Set up the model
        self.subscription_store = gtk.ListStore(str, str, str, str, str, str, bool)
        self.subscription_view.set_model(self.subscription_store)

        text_renderer = gtk.CellRendererText()

        def add_column(name, renderer=text_renderer):
            column_number = len(self.subscription_view.get_columns())
            column = gtk.TreeViewColumn(name, renderer, text=column_number)

            self.subscription_view.append_column(column)

        # Set up columns on the view
        add_column(_("Subscription"))
        add_column(_("Installed Products"))
        add_column(_("Contract"))
        add_column(_("Start Date"))
        add_column(_("Expiration Date"))
        add_column(_("Available Renewals"))

        renew_renderer = gtk.CellRendererToggle()
        renew_renderer.set_property('activatable', True)
        renew_renderer.connect('toggled', self.on_renew_click, None)

        add_column(_("Actions"), renderer=renew_renderer)

        self.update_subscriptions()

    def on_renew_click(self, cell, path, model):
        pass

    def update_subscriptions(self):
        # Just short-circuit if we are not registered...
        if not managergui.consumer:
            return

        pools = managergui.UEP.getPoolsList(managergui.consumer['uuid'])

        for pool in pools:
            subscription = []
            subscription.append(pool['productName'])
            subscription.append('%s/%s' % (pool['consumed'], pool['quantity']))
            subscription.append('Contract...')
            subscription.append(pool['startDate'])
            subscription.append(pool['endDate'])
            subscription.append('?')
            subscription.append(True)

            self.subscription_store.append(subscription)

    def get_content(self):
        return self.content

    def get_label(self):
        return _("My Subscriptions")
