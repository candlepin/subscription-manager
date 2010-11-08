# Subscription Manager Compliance Assistant
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

import os
import gtk
import logging
import gettext
_ = gettext.gettext

from logutil import getLogger
log = getLogger(__name__)

prefix = os.path.dirname(__file__)
COMPLIANCE_GLADE = os.path.join(prefix, "data/compliance.glade")

class ComplianceAssistant(object):
    """ Compliance Assistant GUI window. """
    def __init__(self):
        self.compliance_xml = gtk.glade.XML(COMPLIANCE_GLADE)
        self.window = self.compliance_xml.get_widget('compliance_assistant_window')

    def show(self):
        self.window.show()
