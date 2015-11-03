import gobject

timeout_add = gobject.timeout_add
idle_add = gobject.idle_add

__all__ = [timeout_add, idle_add]
