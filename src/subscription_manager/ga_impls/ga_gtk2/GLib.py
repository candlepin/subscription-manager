import gobject

timeout_add = gobject.timeout_add
timeout_add_seconds = gobject.timeout_add_seconds
idle_add = gobject.idle_add

__all__ = [timeout_add, timeout_add_seconds, idle_add]
