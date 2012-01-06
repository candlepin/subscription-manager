
import sys
import gtk
from gtk import glade

from firstboot_module_window import FirstbootModuleWindow

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)
gettext.textdomain("rhsm")
gtk.glade.bindtextdomain("firstboot", "/usr/share/locale")

sys.path.append("/usr/share/rhsm/")
try:
    from subscription_manager.gui import managergui
except Exception, e:
    print e
    raise


class moduleClass(FirstbootModuleWindow, managergui.MainWindow):
    runPriority = 109.11
    moduleName = _("Subscription Manager")
    windowTitle = moduleName
    shortMessage = _("RHSM Subscriptions Managemen")
    needsnetwork = 1
    icon = None

    def __init__(self):
        FirstbootModuleWindow.__init__(self)
        managergui.MainWindow.__init__(self)
        self.main_window.hide()

    def _show_buttons(self):
        """
        Override the parent class behaviour to not display register/unregister
        buttons during firstboot
        """
        self.register_button.hide()
        self.unregister_button.hide()

    def _show_redemption_buttons(self):
        """
        Override the parent class to first put the button where the
        register/unregister button would be (so we take up less horizontal
        screen space). Then call the parent to determine if the button should
        be shown.
        """
        parent = self.register_button.get_parent()
        self.redeem_button.reparent(parent)
        managergui.MainWindow._show_redemption_buttons(self)

    def apply(self, interface, testing=False):
        return True

    def launch(self, doDebug=None):
        self.vbox = gtk.VBox(spacing=10)
        self.main_window.get_child().reparent(self.vbox)
        self.main_window.destroy()

        toplevel = gtk.VBox(False, 10)
        toplevel.pack_start(self.vbox, True)

        return toplevel, self.icon, self.windowTitle

    def initializeUI(self):
        self.refresh()

    def shouldAppear(self):
        return True

    def _get_window(self):
        return self.vbox.get_parent_window().get_user_data()

childWindow = moduleClass
