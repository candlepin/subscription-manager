from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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
This module provides service for system purpose identity.
"""

from subscription_manager import injection as inj
from subscription_manager.i18n import ugettext as _


STATUS_MAP = {'valid': _('Matched'),
        'invalid': _('Mismatched'),
        'partial': _('Partial'),
        'matched': _('Matched'),
        'mismatched': _('Mismatched'),
        'not specified': _('Not Specified'),
        'disabled': _('Disabled'),
        'unknown': _('Unknown')}


class Syspurpose(object):

    def __init__(self, cp):
        self.cp = cp
        self.identity = inj.require(inj.IDENTITY)
        self.purpose_status = {'status': 'unknown'}

    def get_syspurpose_status(self, on_date=None):
        if self.identity.is_valid() and self.cp.has_capability("syspurpose"):
            self.purpose_status = self.cp.getSyspurposeCompliance(self.identity.uuid, on_date)
        return self.purpose_status

    def get_overall_status(self, status):
        return STATUS_MAP.get(status, STATUS_MAP['unknown'])
