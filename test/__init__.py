from contextlib import contextmanager


@contextmanager
def capture():
    import sys
    import StringIO
    old_out = sys.stdout
    try:
        out = StringIO.StringIO()
        sys.stdout = out
        yield out
    finally:
        sys.stdout = old_out
