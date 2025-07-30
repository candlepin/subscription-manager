import time
from funcy import identity
import json
from pathlib import Path


def loop_until(predicate, poll_sec=5, timeout_sec=120):
    """
    An helper function to handle a time period waiting for an external service
    to update its state.

    an example:

       assert loop_until(lambda: insights_client.is_registered)

    The loop function will retry to run predicate every 5secs
    until the total time exceeds timeout_sec.
    """
    start = time.time()
    ok = False
    while (not ok) and (time.time() - start < timeout_sec):
        time.sleep(poll_sec)
        ok = predicate()
    return ok


def dicts_are_the_same(dict01, dict02, transform=identity):
    """the function is used in assertations

    In case value is a list of values you can use transform method this way:

    >>> dicts_are_the_same(dict01, dict02, frozenset)
    """
    if len(dict01.keys()) != len(dict02.keys()):
        return False
    for key, value in dict01.items():
        if transform(value) != transform(dict02.get(key)):
            return False
    return True


def json_from_file(fpath: Path):
    """
    It is a simple function to hide context manager for open file.
    """
    with open(fpath, "rt") as infile:
        return json.load(infile)
