#
# String constants for the Subscription Manager CLI/GUI
#
# Author: Pradeep Kilambi <pkilambi@redhat.com>
#
# Copyright (c) 2010 Red Hat, Inc.
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
#

import gettext
_ = gettext.gettext


installed_product_status = _("""
ProductName:        \t%-25s
Status:             \t%-25s
Expires:            \t%-25s
Subscription:       \t%-25s
ContractNumber:     \t%-25s
AccountNumber:      \t%-25s
""")

available_subs_list = _("""
ProductName:       \t%-25s
ProductId:         \t%-25s
PoolId:            \t%-25s
Quantity:          \t%-25s
Expires:           \t%-25s
""")

consumed_subs_list = _("""
ProductName:        \t%-25s
ContractNumber:     \t%-25s
AccountNumber:      \t%-25s
SerialNumber:       \t%-25s
Active:             \t%-25s
Begins:             \t%-25s
Expires:            \t%-25s
""")

UNREGISTER_ERROR = _("<b>Errors were encountered during unregister.</b>\n%s\nPlease see /var/log/rhsm/rhsm.log for more information.")

REGISTER_ERROR = _("<b>Unable to register the system.</b>\n\n %s\n\nPlease see /var/log/rhsm/rhsm.log for more information.")

CONFIRM_UNREGISTER = _("<b>Are you sure you want to unregister?</b>")
