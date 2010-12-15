
import gobject
import gtk
import gettext
_ = gettext.gettext


# wrap a long line...
def wrap_line(line, max_line_size=100):
    if len(line) < max_line_size:
        return line
    ret = []
    l = ""
    for w in line.split():
        if not len(l):
            l = w
            continue
        if len(l) > max_line_size:
            ret.append(l)
            l = w
        else:
            l = "%s %s" % (l, w)
    if len(l):
        ret.append(l)
    return '\n'.join(ret)


# wrap an entire piece of text
def wrap_text(txt):
    return '\n'.join(map(wrap_line, txt.split('\n')))



class MessageWindow(gobject.GObject):

    __gsignals__ = {
            'response': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                (gobject.TYPE_BOOLEAN,))
    }

    def __init__(self, text, parent=None):
        gobject.GObject.__init__(self) 
        self.rc = None

        # this seems to be wordwrapping text passed to
        # it, which is making for ugly error messages
        self.dialog = gtk.MessageDialog(parent, 0, self.STYLE, self.BUTTONS)

        # escape product strings see rh bz#633438
        self.dialog.set_markup(text)

        self.dialog.set_default_response(0)

        self.addFrame(self.dialog)
        self.dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.dialog.show_all()

        self.dialog.set_modal(True)

        self.dialog.connect("response", self._on_response_event)

    def _on_response_event(self, dialog, response):
        rc = response in [gtk.RESPONSE_OK, gtk.RESPONSE_YES]
        self.emit('response', rc)
        self.hide()

    def hide(self):
        self.dialog.hide()
        self.dialog.destroy()

    @staticmethod
    def addFrame(dialog):
        contents = dialog.get_children()[0]
        dialog.remove(contents)
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_OUT)
        frame.add(contents)
        dialog.add(frame)


class ErrorDialog(MessageWindow):

    BUTTONS = gtk.BUTTONS_OK
    STYLE = gtk.MESSAGE_ERROR


class OkDialog(MessageWindow):

    BUTTONS = gtk.BUTTONS_OK
    STYLE = gtk.MESSAGE_INFO


class InfoDialog(MessageWindow):

    BUTTONS = gtk.BUTTONS_OK
    STYLE = gtk.MESSAGE_INFO


class YesNoDialog(MessageWindow):

    BUTTONS = gtk.BUTTONS_YES_NO
    STYLE = gtk.MESSAGE_QUESTION
