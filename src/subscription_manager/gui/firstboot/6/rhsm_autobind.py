import sys
import gtk

from firstboot.config import *
from firstboot.constants import *
from firstboot.functions import *
from firstboot.module import *
from firstboot.module import Module

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

import rhsm

sys.path.append("/usr/share/rhsm")
from subscription_manager.gui import managergui
from subscription_manager.gui import autobind
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.facts import Facts


class moduleClass(Module, autobind.AutobindWizard):

    def __init__(self):
        Module.__init__(self)

        backend = managergui.Backend()
        consumer = managergui.Consumer()
        facts = Facts()
        autobind.AutobindWizard.__init__(self, backend, consumer, facts,
                None) 

        # this value is relative to when you want to load the screen
        # so check other modules before setting
        self.priority = 200.2
        self.sidebarTitle = _("Entitlement Registration")
        self.title = _("Service Level")
        self._cached_credentials = None
        self._registration_finished = False
        self._first_registration_apply_run = True

    def apply(self, interface, testing=False):
        """
        'Next' button has been clicked - try to register with the
        provided user credentials and return the appropriate result
        value.
        """

        self.interface = interface

        if self._registration_finished:
            self._registration_finished = False
            return RESULT_SUCCESS

        credentials = self._get_credentials_hash()

        if credentials == self._cached_credentials and \
                ConsumerIdentity.exists():
            # User has already successfully authenticaed with these
            # credentials, just go on to the next module without
            # reregistering the consumer
            return RESULT_SUCCESS
        else:
            # if they've already registered during firstboot and have clicked
            # back to register again, we must first unregister.
            # XXX i'd like this call to be inside the async progress stuff,
            # since it does take some time
            if self._first_registration_apply_run and ConsumerIdentity.exists():
                managerlib.unregister(self.backend.uep, self.consumer.uuid)
                self.consumer.reload()
                self._first_registration_apply_run = False

            valid_registration = self.register(testing=testing)

            if valid_registration:
                self._cached_credentials = credentials
            return RESULT_FAILURE

    def close_window(self):
        """
        Overridden from RegisterScreen - we want to bypass the default behavior
        of hiding the GTK window.
        """
        pass

    def emit_consumer_signal(self):
        """
        Overriden from RegisterScreen - we don't care about consumer update
        signals.
        """
        pass

    def registrationTokenScreen(self):
        """
        Overridden from RegisterScreen - ignore any requests to show the
        registration screen on this particular page.
        """
        pass

    def createScreen(self):
        """
        Create a new instance of gtk.VBox, pulling in child widgets from the
        glade file.
        """
        self.vbox = gtk.VBox(spacing=10)
        self.autobind_notebook.reparent(self.vbox)

        # Get rid of the 'register' and 'cancel' buttons, as we are going to
        # use the 'forward' and 'back' buttons provided by the firsboot module
        # to drive the same functionality
#        self._destroy_widget('register_button')
#        self._destroy_widget('cancel_button')

    def initializeUI(self):
        # Need to make sure that each time the UI is initialized we reset back to the
        # main register screen.
        #self._show_credentials_page()
        #self._clear_registration_widgets()
        #self.initializeConsumerName()

        self.consumer.reload()
        self.facts = managergui.Facts()

        self.show()

    def needsNetwork(self):
        """
        This lets firstboot know that networking is required, in order to
        talk to hosted UEP.
        """
        return True

    def focus(self):
        """
        Focus the initial UI element on the page, in this case the
        login name field.
        """
        # FIXME:  This is currently broken
#        login_text = registergui.registration_xml.get_widget("account_login")
#        login_text.grab_focus()

    def shouldAppear(self):
        """
        Indicates to firstboot whether to show this screen.  In this case
        we want to skip over this screen if there is already an identity
        certificate on the machine (most likely laid down in a kickstart).
        """
        return not ConsumerIdentity.existsAndValid()

    def _destroy_widget(self, widget_name):
        """
        Destroy a widget by name.

        See gtk.Widget.destroy()
        """
        widget = registergui.registration_xml.get_widget(widget_name)
        widget.destroy()

    def _get_text(self, widget_name):
        """
        Return the text value of an input widget referenced
        by name.
        """
        widget = registergui.registration_xml.get_widget(widget_name)
        return widget.get_text()

