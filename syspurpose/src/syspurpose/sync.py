# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import
#
# Copyright (c) 2018 Red Hat, Inc.
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

"""
This module contains utilities for syncing system syspurpose with candlepin server
"""

# We do not want to have hard dependency on rhsm module nor subscription_manager
try:
    import rhsm
    import rhsm.connection
    import rhsm.certificate2
    import rhsm.config
except ImportError:
    rhsm = None


class SyspurposeSync(object):
    """
    Sync local, remote and cached system purpose
    """

    def __new__(cls, *args, **kwargs):
        """
        We do not want to create instance of SyspurposeSync, when rhsm module is not available,
        because it would be useless. When rhsm module is not available, then exception is raised.
        :return: Instance of Syspurpose, when rhsm module is available. Otherwise raise exception.
        """
        if rhsm:
            return super(SyspurposeSync, cls).__new__(cls)
        else:
            raise ImportError('Module rhsm is not available')

    def __init__(self, proxy_server=None, proxy_port=None, proxy_user=None, proxy_pass=None):
        """
        Initialization of SyspurposeSync has to have optional arguments with
        proxy settings, because proxy settings can be part of e.g. command line arguments
        """

        self.config = rhsm.config.initConfig()

        if proxy_server:
            self.proxy_server = proxy_server
            self.proxy_port = proxy_port or rhsm.config.DEFAULT_PROXY_PORT
            self.proxy_user = proxy_user
            self.proxy_pass = proxy_pass
        else:
            self.proxy_server = self.config.get('server', 'proxy_hostname')
            self.proxy_port = self.config.get('server', 'proxy_port')
            self.proxy_user = self.config.get('server', 'proxy_user')
            self.proxy_pass = self.config.get('server', 'proxy_password')

        self.connection = None
        self.consumer_uuid = None

    def send_syspurpose_to_candlepin(self, syspurpose_store):
        """
        Try to sync system purpose to candlepin server.
        :param syspurpose_store: Instance of SystempurposeStore
        :return: True, when system purpose was sent to candlepin server.
        """

        if rhsm:
            cert_dir = self.config.get('rhsm', 'consumerCertDir')
            cert_file_path = cert_dir + '/cert.pem'
            key_file_path = cert_dir + '/key.pem'
            self.connection = rhsm.connection.UEPConnection(
                proxy_hostname=self.proxy_server,
                proxy_port=self.proxy_port,
                proxy_user=self.proxy_user,
                proxy_password=self.proxy_pass,
                cert_file=cert_file_path,
                key_file=key_file_path
            )

            if not self.connection.has_capability("syspurpose"):
                print("Note: The currently configured entitlement server does not support System Purpose")
                return False

            try:
                consumer_cert = rhsm.certificate.create_from_file(cert_file_path)
            except rhsm.certificate.CertificateException as err:
                print('Unable to read consumer certificate: %s' % err)
                return False
            consumer_uuid = consumer_cert.subject.get('CN')

            try:
                self.connection.updateConsumer(
                    uuid=consumer_uuid,
                    role=syspurpose_store.contents.get('role') or '',
                    addons=syspurpose_store.contents.get('addons') or [],
                    service_level=syspurpose_store.contents.get('service_level_agreement') or '',
                    usage=syspurpose_store.contents.get('usage') or ''
                )
            except Exception as err:
                print('Unable to update consumer with system purpose: %s' % err)
                return False

            return True
