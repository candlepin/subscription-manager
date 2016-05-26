from __future__ import print_function


def kluge_it():
    import sys

    # gobject and gi and python module loading tricks are fun.
    gmodules = [x for x in sys.modules.keys() if x.startswith('gobject')]
    for gmodule in gmodules:
        del sys.modules[gmodule]

    try:
        import slip._wrappers
        slip._wrappers._gobject = None
    except ImportError:
        print('fix me, workaround for rhel6')
