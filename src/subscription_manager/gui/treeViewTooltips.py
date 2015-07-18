# Copyright (c) 2006, Daniel J. Popowich
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Send bug reports and contributions to:
#
#    dpopowich AT astro dot umass dot edu
#

'''
Provides TreeViewTooltips, a class which presents tooltips for cells,
columns and rows in a gtk.TreeView.

To use, first subclass TreeViewTooltips and implement the get_tooltip()
method; see below.  Then add any number of gtk.TreeVew widgets to a
TreeViewTooltips instance by calling the add_view() method.  Overview
of the steps:

    # 1. subclass TreeViewTooltips
    class MyTooltips(TreeViewTooltips):

        # 2. overriding get_tooltip()
        def get_tooltip(...):
            ...

    # 3. create an instance
    mytips = MyTooltips()

    # 4. Build up your gtk.TreeView.
    myview = gtk.TreeView()
    ...# create columns, set the model, etc.

    # 5. Add the view to the tooltips
    mytips.add_view(myview)

How it works: the add_view() method connects the TreeView to the
"motion-notify" event with the callback set to a private method.
Whenever the mouse moves across the TreeView the callback will call
get_tooltip() with the following arguments:

    get_tooltip(view, column, path)

where,

    view:   the gtk.TreeView instance.
    column: the gtk.TreeViewColumn instance that the mouse is
            currently over.
    path:   the path to the row that the mouse is currently over.

Based on whether or not column and path are checked for specific
values, get_tooltip can return tooltips for a cell, column, row or the
whole view:

    Column Checked      Path Checked      Tooltip For...
          Y                 Y             cell
          Y                 N             column
          N                 Y             row
          N                 N             view

get_tooltip() should return None if no tooltip should be displayed.
Otherwise the return value will be coerced to a string (with the str()
builtin) and stripped; if non-empty, the result will be displayed as
the tooltip.  By default, the tooltip popup window will be displayed
centered and just below the pointer and will remain shown until the
pointer leaves the cell (or column, or row, or view, depending on how
get_tooltip() is implemented).
'''

import gtk
import gobject


class TreeViewTooltips(object):
    def __init__(self):
        '''
        Initialize the tooltip.  After initialization there are two
        attributes available for advanced control:

            window: the popup window that holds the tooltip text, an
                    instance of gtk.Window.
            label:  a gtk.Label that is packed into the window.  The
                    tooltip text is set in the label with the
                    set_label() method, so the text can be plain or
                    markup text.

        Be default, the tooltip is enabled.  See the enabled/disabled
        methods.
        '''
        # create the window
        self.window = window = gtk.Window(gtk.WINDOW_POPUP)
        window.set_name('gtk-tooltips')
        window.set_resizable(False)
        window.set_border_width(4)
        window.set_app_paintable(True)
        window.connect("expose-event", self.__on_expose_event)

        # create the label
        self.label = label = gtk.Label()
        label.set_line_wrap(True)
        label.set_alignment(0.5, 0.5)
        label.set_use_markup(True)
        label.show()
        window.add(label)

        # by default, the tooltip is enabled
        self.__enabled = True
        # saves the current cell
        self.__save = None
        # the timer id for the next tooltip to be shown
        self.__next = None
        # flag on whether the tooltip window is shown
        self.__shown = False

    def enable(self):
        'Enable the tooltip'
        self.__enabled = True

    def disable(self):
        'Disable the tooltip'
        self.__enabled = False

    def __show(self, tooltip, x, y):
        '''show the tooltip popup with the text/markup given by
        tooltip.

        tooltip: the text/markup for the tooltip.
        x, y:  the coord. (root window based) of the pointer.
        '''
        window = self.window

        # set label
        self.label.set_label(tooltip)
        # resize window
        w, h = window.size_request()
        # move the window
        window.move(*self.location(x, y, w, h))
        # show it
        window.show()
        self.__shown = True

    def __hide(self):
        'hide the tooltip'
        self.__queue_next()
        self.window.hide()
        self.__shown = False

    def __leave_handler(self, view, event):
        'when the pointer leaves the view, hide the tooltip'
        self.__hide()

    def __motion_handler(self, view, event):
        'As the pointer moves across the view, show a tooltip.'
        path = view.get_path_at_pos(int(event.x), int(event.y))

        if self.__enabled and path:
            path, col, x, y = path
            tooltip = self.get_tooltip(view, col, path)
            if tooltip is not None:
                tooltip = str(tooltip).strip()
                if tooltip:
                    self.__queue_next((path, col), tooltip,
                                      int(event.x_root),
                                      int(event.y_root))
                    return

        self.__hide()

    def __queue_next(self, *args):
        'queue next request to show a tooltip'
        # if args is non-empty it means a request was made to show a
        # tooltip.  if empty, no request is being made, but any
        # pending requests should be cancelled anyway.
        cell = None

        # if called with args, break them out
        if args:
            cell, tooltip, x, y = args

        # if it's the same cell as previously shown, just return
        if self.__save == cell:
            return

        # if we have something queued up, cancel it
        if self.__next:
            gobject.source_remove(self.__next)
            self.__next = None

        # if there was a request...
        if cell:
            # if the tooltip is already shown, show the new one
            # immediately
            if self.__shown:
                self.__show(tooltip, x, y)
            # else queue it up in 1/2 second
            else:
                self.__next = gobject.timeout_add(500, self.__show,
                                                  tooltip, x, y)

        # save this cell
        self.__save = cell

    def __on_expose_event(self, window, event):
        # this magic is required so the window appears with a 1-pixel
        # black border (default gtk Style).  This code is a
        # transliteration of the C implementation of gtk.Tooltips.
        w, h = window.size_request()
        window.style.paint_flat_box(window.window, gtk.STATE_NORMAL,
                                    gtk.SHADOW_OUT, None, window,
                                    'tooltip', 0, 0, w, h)

    def location(self, x, y, w, h):
        '''Given the x,y coordinates of the pointer and the width and
        height (w,h) demensions of the tooltip window, return the x, y
        coordinates of the tooltip window.

        The default location is to center the window on the pointer
        and 4 pixels below it.
        '''
        return x - w / 2, y + 4

    def add_view(self, view):
        'add a gtk.TreeView to the tooltip'
        assert isinstance(view, gtk.TreeView), \
               ('This handler should only be connected to '
                'instances of gtk.TreeView')

        view.connect("motion-notify-event", self.__motion_handler)
        view.connect("leave-notify-event", self.__leave_handler)

    def get_tooltip(self, view, column, path):
        'See the module doc string for a description of this method'
        raise NotImplemented("Subclass must implement get_tooltip()")
