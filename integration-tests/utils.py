import time


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
