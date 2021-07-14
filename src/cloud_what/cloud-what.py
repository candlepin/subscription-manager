#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import logging
import sys

from cloud_what.provider import get_cloud_provider, gather_system_facts


def init_logger():
    """
    Initialize logger to use /dev/null at this moment
    :return: None
    """
    root_namespaces = ['cloud_what', 'rhsmlib']
    for namespace in root_namespaces:
        # Create logger for namespace
        logger = logging.getLogger(namespace)
        logger.setLevel(logging.DEBUG)
        # Create file handler which logs even debug messages
        fh = logging.FileHandler('cloud-what.log')
        fh.setLevel(logging.DEBUG)
        # Create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # Add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


def main() -> int:
    """
    Main function of cloud-what application
    :return: Integer status code
    """

    logger = init_logger()

    logger.info('Trying to gather system facts')
    facts = gather_system_facts()

    cloud_provider = get_cloud_provider(facts=facts, threshold=0.5)

    if cloud_provider is None:
        print("none")
        return 1
    else:
        print(cloud_provider.CLOUD_PROVIDER_ID)
        return 0


if __name__ == '__main__':
    try:
        sys.exit(abs(main() or 0))
    except SystemExit as err:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except IOError:
            pass
        raise err
    except KeyboardInterrupt:
        sys.stderr.write("\n" + "User interrupted process.")
        sys.exit(0)
