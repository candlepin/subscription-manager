import time
import re


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


def subman_identity(subman) -> dict[str, str]:
    """
    The method returns a dict of properties that
    a command 'subscription-manager identity' provides
    """
    subman_response = subman.run("identity")
    # (env) [root@kvm-08-guest21 integration-tests]# subscription-manager identity
    #
    # system identity: 5c00d2c6-5bea-4b6d-8662-8680e38f0dab
    # name: kvm-08-guest21.lab.eng.rdu2.dc.redhat.com
    # org name: Donald Duck
    # org ID: donaldduck
    # environment name: env-name-01

    def read_pair(line):
        result = re.search(r"^([^:]+):(.*)", line.strip())
        if result:
            pair = [g.strip() for g in result.groups()]
            return pair
        return []

    pairs = dict([read_pair(line) for line in subman_response.stdout.splitlines()])
    return pairs
