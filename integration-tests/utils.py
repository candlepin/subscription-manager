import time
import re
from typing import Generator


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


def installed_products(subman) -> list[dict[str, str]]:
    """
    The function returns a list of products that subscription-manager provides
    """
    subman_response = subman.run("list", "--installed", check=False)
    #
    # [root@ad5327bd-5cc5-4a6c-b162-f1cf6d9bd61f integration-tests]# subscription-manager list --installed
    # +-------------------------------------------+
    # Installed Product Status
    # +-------------------------------------------+
    # Product Name: Red Hat Enterprise Linux for x86_64 Beta
    # Product ID:   486
    # Version:      10.1 Beta
    # Arch:         x86_64
    #
    # Product Name: Red Hat Enterprise Linux Builder for x86_64 Beta
    # Product ID:   495
    # Version:      10.1 Beta
    # Arch:         x86_64
    #

    def read_products(lines: list[str]) -> Generator[dict[str, str], None, None]:
        """
        parse an output from the command to find product's properties
        """
        product = {}
        for line in lines:
            if not line.strip():  # an empty line between two products
                if len(product.items()) > 0:
                    yield product
                    product = {}
                else:
                    continue
            result = re.search(r"^([^:]+):(.*)", line.strip())
            if result:
                pair = [g.strip() for g in result.groups()]
                product[pair[0]] = pair[1]

        if len(product.items()) > 0:
            yield product

    return list(read_products(subman_response.stdout.splitlines()))
