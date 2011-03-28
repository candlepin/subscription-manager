
import sys
import gtk

from firstboot_module_window import FirstbootModuleWindow

from rhpl.translate import _, N_
import rhpl.translate as translate
translate.textdomain("firstboot")
gtk.glade.bindtextdomain("firstboot", "/usr/share/locale")

import rhsm


sys.path.append("/usr/share/rhsm/")
try:
    from subscription_manager.gui import managergui
except Exception, e:
    print e
    raise



class moduleClass(FirstbootModuleWindow, managergui.MainWindow):
    runPriority = 109.11
    moduleName = "Subscription Manager"
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

    def apply(self, interface, testing=False):
        return True

    def launch(self, doDebug=None):
#    def createScreen(self):
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
