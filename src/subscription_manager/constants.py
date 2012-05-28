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
_ = lambda x: gettext.ldgettext("rhsm", x)


installed_product_status = \
    _("Product Name:         \t%s") + \
    "\n" + \
    _("Product ID:           \t%s") + \
    "\n" + \
    _("Version:              \t%s") + \
    "\n" + \
    _("Arch:                 \t%s") + \
    "\n" + \
    _("Status:               \t%s") + \
    "\n" + \
    _("Starts:               \t%s") + \
    "\n" + \
    _("Ends:                 \t%s") + \
    "\n"

available_subs_list = \
    _("Product Name:         \t%s") + \
    "\n" + \
    _("Product Id:           \t%s") + \
    "\n" + \
    _("Pool Id:              \t%s") + \
    "\n" + \
    _("Quantity:             \t%s") + \
    "\n" + \
    _("Service Level:        \t%s") + \
    "\n" + \
    _("Service Type:         \t%s") + \
    "\n" + \
    _("Multi-Entitlement:    \t%s") + \
    "\n" + \
    _("Ends:                 \t%s") + \
    "\n" + \
    _("Machine Type:         \t%s") + \
    "\n"

repos_list = \
    _("Repo Id:              \t%s") + \
    "\n" + \
    _("Repo Name:            \t%s") + \
    "\n" + \
    _("Repo Url:             \t%s") + \
    "\n" + \
    _("Enabled:              \t%s") + \
    "\n"

product_status = \
    _("Product Name:         \t%s") + \
    "\n" + \
    _("Status:               \t%s") + \
    "\n"

environment_list = \
    _("Name:                 \t%s") + \
    "\n" + \
    _("Description:          \t%s") + \
    "\n" \

UNREGISTER_ERROR = _("<b>Errors were encountered during unregister.</b>") + \
    "\n%s\n" + \
    _("Please see /var/log/rhsm/rhsm.log for more information.")

REGISTER_ERROR = _("<b>Unable to register the system.</b>") + \
    "\n%s\n" + \
    _("Please see /var/log/rhsm/rhsm.log for more information.")

CONFIRM_UNREGISTER = _("<b>Are you sure you want to unregister?</b>")

NO_ORG_ERROR = _("<b>User %s is not able to register with any orgs.</b>")
