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

import connection
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
        self.subscription_store = gtk.ListStore(str, str, str, str, str, str, gtk.Button)
        self.subscription_view.set_model(self.subscription_store)

        text_renderer = gtk.CellRendererText()
        #button_renderer = gtk.CellRenderer()

        def add_text_column(name):
            column_number = len(self.subscription_view.get_columns())
            column = gtk.TreeViewColumn(_(name), text_renderer, text=column_number)

            self.subscription_view.append_column(column)

        # Set up columns on the view
        add_text_column("Subscription")
        add_text_column("Installed Products")
        add_text_column("Contract")
        add_text_column("Start Date")
        add_text_column("Expiration Date")
        add_text_column("Available Renewals")

        # Set sorting by fact name
#        self.facts_store.set_sort_column_id(0, gtk.SORT_ASCENDING)

    def get_content(self):
        return self.content

    def get_label(self):
        return _("My Subscriptions")
