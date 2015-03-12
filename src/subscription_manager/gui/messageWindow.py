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
import gettext

import gobject
import gtk

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

    def __init__(self, text, parent=None, title=None):
        self.__gobject_init__()
        self.rc = None

        # this seems to be wordwrapping text passed to
        # it, which is making for ugly error messages
        self.dialog = gtk.MessageDialog(parent, 0, self.STYLE, self.BUTTONS)

        if title:
            self.dialog.set_title(title)

        # escape product strings see rh bz#633438
        self.dialog.set_markup(text)

        self.dialog.set_default_response(0)

        self.dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.dialog.show_all()
        self.dialog.set_icon_name('subscription-manager')

        self.dialog.set_modal(True)
        #this seems spurious, but without it, a ref to this obj gets "lost"
        gobject.add_emission_hook(self, 'response', self.noop_hook)

        self.dialog.connect("response", self._on_response_event)

    def _on_response_event(self, dialog, response):
        rc = response in [gtk.RESPONSE_OK, gtk.RESPONSE_YES]
        self.emit('response', rc)
        self.hide()

    def hide(self):
        self.dialog.hide()

    def noop_hook(self, dummy1=None, dummy2=None):
        pass


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


class ContinueDialog(MessageWindow):

    BUTTONS = gtk.BUTTONS_OK_CANCEL
    STYLE = gtk.MESSAGE_WARNING
