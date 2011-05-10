import sys
import gtk


from firstboot_module_window import FirstbootModuleWindow


from rhpl.translate import _, N_
import rhpl.translate as translate
translate.textdomain("firstboot")
gtk.glade.bindtextdomain("firstboot", "/usr/share/locale")

#import rhsm as sys_rhsm
#print "sys_rhsm", sys_rhsm.__file__

import rhsm
print "rhsm",rhsm, rhsm.__file__


sys.path.append("/usr/share/rhsm/")
print sys.path
try:
    from subscription_manager.gui import managergui
except Exception, e:
    print e
    raise

from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.facts import Facts

sys.path.append("/usr/share/rhn")
from up2date_client import config

class moduleClass(FirstbootModuleWindow, managergui.RegisterScreen):
    
    runPriority = 109.10
    moduleName = "Entitlement Registration"
    windowTitle = moduleName
    shortMessage = _("Entitlement Platform Registration")
    needsnetwork = 1
    icon = None

    def __init__(self):
        """
        Create a new firstboot Module for the 'register' screen.
        """
        FirstbootModuleWindow.__init__(self)

        backend = managergui.Backend()

        managergui.RegisterScreen.__init__(self, backend, managergui.Consumer(),
                Facts())

#        managergui.create_and_set_basic_connection()
        self._cached_credentials = None

    def _read_rhn_proxy_settings(self):
        # Read and store rhn-setup's proxy settings, as they have been set
        # on the prior screen (which is owned by rhn-setup)
        up2date_cfg = config.initUp2dateConfig()
        cfg = rhsm.config.initConfig()

        if up2date_cfg['enableProxy']:
            proxy = up2date_cfg['httpProxy']
            if proxy:
                try:
                    host, port = proxy.split(':')
                    cfg.set('server', 'proxy_hostname', host)
                    cfg.set('server', 'proxy_port', port)
                except ValueError:
                    cfg.set('server', 'proxy_hostname', proxy)
                    cfg.set('server', 'proxy_port',
                            rhsm.config.DEFAULT_PROXY_PORT)
            if up2date_cfg['enableProxyAuth']:
                cfg.set('server', 'proxy_user', up2date_cfg['proxyUser'])
                cfg.set('server', 'proxy_password',
                        up2date_cfg['proxyPassword'])
        else:
            cfg.set('server', 'proxy_hostname', '')
            cfg.set('server', 'proxy_port', '')
            cfg.set('server', 'proxy_user', '')
            cfg.set('server', 'proxy_password', '')

        cfg.save()
        self.backend.uep = rhsm.connection.UEPConnection(
            host=cfg.get('server', 'hostname'),
            ssl_port=int(cfg.get('server', 'port')),
            handler=cfg.get('server', 'prefix'),
            proxy_hostname=cfg.get('server', 'proxy_hostname'),
            proxy_port=cfg.get('server', 'proxy_port'),
            proxy_user=cfg.get('server', 'proxy_user'),
            proxy_password=cfg.get('server', 'proxy_password'),
            username=None, password=None,
            cert_file=ConsumerIdentity.certpath(),
            key_file=ConsumerIdentity.keypath())

    def apply(self, interface, testing=False):
        """
        'Next' button has been clicked - try to register with the
        provided user credentials and return the appropriate result
        value.
        """

        self._read_rhn_proxy_settings()

        credentials = self._get_credentials_hash()

        if credentials == self._cached_credentials and \
                ConsumerIdentity.exists():
            # User has already successfully authenticaed with these
            # credentials, just go on to the next module without
            # reregistering the consumer
            return 0
        else:
            valid_registration = self.register(testing=testing)

            if valid_registration:
                self._cached_credentials = credentials
                return 0
            else:
                return None

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

    def launch(self, doDebug=None):
        
        # return top level window, icon and windowtitle

#    def createScreen(self):
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

        toplevel = gtk.VBox(False, 10)
        toplevel.pack_start(self.vbox, True)

        return toplevel, self.icon, self.windowTitle

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
        return True

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

childWindow = moduleClass
