
from gtk.gdk import Pixbuf as _Pixbuf
from gtk.gdk import pixbuf_new_from_file_at_size


class Pixbuf(_Pixbuf):
    # FIXME: would monkey patching this onto _Pixbuf be better?
    @classmethod
    def new_from_file_at_size(cls, path, height, width):
        "Return a gtk.gdk.Pixbuf (note, not a ga.gtk.GdkPixbuf)"
        return pixbuf_new_from_file_at_size(path, height, width)

__all__ = [Pixbuf]
