import sys
import gtk

from firstboot.config import *
from firstboot.constants import *
from firstboot.functions import *
from firstboot.module import *
from firstboot.module import Module

import gettext
_ = lambda x: gettext.ldgettext("firstboot", x)

sys.path.append("/usr/share/rhsm")
import rhsm.connection as connection
from gui import managergui
from certlib import ConsumerIdentity
from facts import Facts
from gui import networkConfig


class moduleClass(Module, managergui.RegisterScreen):

    def __init__(self):
        """
        Create a new firstboot Module for the 'register' screen.
        """
        Module.__init__(self)

        backend = managergui.Backend(connection.UEPConnection(
            cert_file=ConsumerIdentity.certpath(),
            key_file=ConsumerIdentity.keypath()))

        managergui.RegisterScreen.__init__(self, backend, managergui.Consumer(),
                Facts())

#        managergui.create_and_set_basic_connection()
        # this value is relative to when you want to load the screen
        # so check other modules before setting
        self.priority = 1.2
        self.sidebarTitle = _("Entitlement Registration")
        self.title = _("Entitlement Platform Registration")
        self._cached_credentials = None

    def apply(self, interface, testing=False):
        """
        'Next' button has been clicked - try to register with the
        provided user credentials and return the appropriate result
        value.
        """
        credentials = self._get_credentials_hash()

        if credentials == self._cached_credentials and \
                ConsumerIdentity.exists():
            # User has already successfully authenticaed with these
            # credentials, just go on to the next module without
            # reregistering the consumer
            return RESULT_SUCCESS
        else:
            valid_registration = self.register(testing=testing)

            if valid_registration:
                self._cached_credentials = credentials
                return RESULT_SUCCESS
            else:
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
        self.register_dialog = managergui.registration_xml.get_widget("dialog-vbox6")
        self.register_dialog.reparent(self.vbox)

        # Get rid of the 'register' and 'cancel' buttons, as we are going to
        # use the 'forward' and 'back' buttons provided by the firsboot module
        # to drive the same functionality
        self._destroy_widget('register_button')
        self._destroy_widget('cancel_button')

        # Add a button to launch network config for using a proxy
        box = gtk.HButtonBox()
        box.set_layout(gtk.BUTTONBOX_START)
        config_button = gtk.Button(_("Proxy Configuration"))
        config_button.connect("clicked", self._proxy_button_clicked)
        box.pack_start(config_button)
        self.register_dialog.pack_start(box, expand=False, fill=False)
        self.network_config_dialog = networkConfig.NetworkConfigDialog()

    def initializeUI(self):
        self.initializeConsumerName()

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
        login_text = managergui.registration_xml.get_widget("account_login")
        login_text.grab_focus()

    def shouldAppear(self):
        """
        Indicates to firstboot whether to show this screen.  In this case
        we want to skip over this screen if there is already an identity
        certificate on the machine (most likely laid down in a kickstart),
        but showing the screen and allowing the user to reregister if
        firstboot is run in reconfig mode.
        """
        return self._is_mode(MODE_RECONFIG) or not ConsumerIdentity.exists()

    def _is_mode(self, mode):
        """
        Is firstboot in the specified mode?
        """
        # config.mode is a bitmask off all current modes
        return config.mode & mode == mode

    def _destroy_widget(self, widget_name):
        """
        Destroy a widget by name.

        See gtk.Widget.destroy()
        """
        widget = managergui.registration_xml.get_widget(widget_name)
        widget.destroy()

    def _get_credentials_hash(self):
        """
        Return an internal hash representation of the text input
        widgets.  This is used to compare if we have changed anything
        when moving back and forth across modules.
        """
        credentials = [self._get_text(name) for name in \
                           ('account_login', 'account_password',
                               'consumer_name')]
        return hash(tuple(credentials))

    def _get_text(self, widget_name):
        """
        Return the text value of an input widget referenced
        by name.
        """
        widget = managergui.registration_xml.get_widget(widget_name)
        return widget.get_text()

    def _proxy_button_clicked(self, widget):
        self.network_config_dialog.show()
