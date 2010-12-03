import os
import gtk


class Progress:

    def __init__(self, label):
        glade_prefix = os.path.dirname(__file__)

        self.xml = gtk.glade.XML(os.path.join(glade_prefix, "data/progress.glade"),
                "progressWindow")
        self.progressWindow = self.xml.get_widget("progressWindow")
        self.progressWindow.connect("delete-event", self._on_delete_event)
        cursor = gtk.gdk.Cursor(gtk.gdk.WATCH)
        self.progressWindow.window.set_cursor(cursor)

        self.lastProgress = 0.0

        self.setLabel(label)

    def hide(self):
        self.progressWindow.hide()

        del self

    def setLabel(self, text):
        label = self.xml.get_widget("progressLabel")
        label.set_text(text)

    def pulse(self):
        """
        pulse for a glib mainloop timeout callback
        """
        self.xml.get_widget("progressBar").pulse()
        return True

    def setProgress(self, amount, total):
        if total:
            i = float(amount) / total
        else:
            i = 1

        if i > 1:
            i = 1
        if i > self.lastProgress + .01 or i == 1:
            self.xml.get_widget("progressBar").set_fraction(i)
            if i == 1:
                # reset
                i = 0
            self.lastProgress = i

    def setStatusLabel(self, text):
        self.xml.get_widget("statusLabel").set_text(text)

    def destroy(self):
        self.progressWindow.destroy()

    def set_parent_window(self, window):
        self.progressWindow.set_transient_for(window)

    def _on_delete_event(self, widget, event):
        self.destroy()
