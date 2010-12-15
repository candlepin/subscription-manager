
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



class MessageWindow:

    def __init__(self, text, parent=None):
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
        rc = self.dialog.run()
        self.rc = rc in [gtk.RESPONSE_OK, gtk.RESPONSE_YES]
        self.dialog.destroy()

    def getrc(self):
        return self.rc

    def hide(self):
        self.dialog.hide()
        self.dialog.destroy()
        gtk.main_iteration()

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
