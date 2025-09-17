import time
from funcy import identity
import json
import re
import os
from typing import Generator
from pathlib import Path
import configparser


def loop_until(predicate, poll_sec=5, timeout_sec=120):
    """
    An helper function to handle a time period waiting for an external service
    to update its state.

    an example:

       assert loop_until(lambda: insights_client.is_registered)

    The loop function will retry to run predicate every 5secs
    until the total time exceeds timeout_sec.

    It stops looping when the predicate gets True
    """
    start = time.time()
    ok = False
    while (not ok) and ((time.time() - start) < timeout_sec):
        time.sleep(poll_sec)
        ok = predicate()
    return ok


def dicts_are_the_same(dict01, dict02, transform=identity):
    """the function is used in assertations

    In case a value is a list of values you can use transform method this way:

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
    It is a simple function to hide context manager to open a file.
    """
    with open(fpath, "rt") as infile:
        return json.load(infile)


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


def product_ids_in_dir(dirpath: Path) -> list[int]:
    """
    returns a list of IDs of products installed in the given directory
    """
    fnames = os.listdir(dirpath)
    matches = [re.search(r"^([0-9]+)\.pem", fname) for fname in fnames]
    product_ids = [int(m.group(1)) for m in matches if m is not None]
    return product_ids


def read_ini_file(path):
    """
    This method reads a config file at given path

    It returns a list of (key, value)
    ... key - abs path to the value (ie. including section name)
        for example:
            ("logging.default_level","INFO")
    """
    config = configparser.ConfigParser()
    config.read(path)
    for section in config.sections():
        config_section = config[section]
        for key in config_section:
            yield (f"{section}.{key}", config_section[key])


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
