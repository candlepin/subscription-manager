# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Red Hat, Inc.
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

# TODO: test Python3 syntax using flake8
# flake8: noqa

"""
This module implements the base class for detecting cloud provider
"""


class CloudDetector(object):
    """
    Base class used for detecting cloud provider
    """

    ID = None

    def __init__(self, hw_info):
        """
        Initialize cloud detector
        """
        self.hw_info = hw_info

    def is_vm(self):
        """
        Is current system virtual machine?
        :return: Return True, when it is virtual machine; otherwise return False
        """
        return 'virt.is_guest' in self.hw_info and self.hw_info['virt.is_guest'] is True

    def is_running_on_cloud(self):
        """
        Try to guess cloud provider using collected hardware information (output of dmidecode, virt-what, etc.)
        :return: True, when we detected sign of cloud provider in hw info; Otherwise return False
        """
        raise NotImplementedError

    def is_likely_running_on_cloud(self):
        """
        When all subclasses cannot detect cloud provider using method is_running_on_cloud, because cloud provider
        started to provide something else in output of dmidecode, then try to use this heuristics method
        :return: Float value representing probability that vm is running using specific cloud provider
        """
        raise NotImplementedError
