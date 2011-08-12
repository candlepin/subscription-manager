# Copyright (c) 2011 Red Hat, Inc.
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

import unittest
import gtk

from subscription_manager.gui.widgets import MachineTypeColumn


class TestMachineTypeColumn(unittest.TestCase):

    def test_render_virtual_icon_when_virt_only(self):
        self._check_render_machine_type(True, MachineTypeColumn.VIRTUAL_MACHINE_PIXBUF)

    def test_render_physical_icon_when_not_virt_only(self):
        self._check_render_machine_type(False, MachineTypeColumn.PHYSICAL_MACHINE_PIXBUF)

    def test_render_astrisk_when_multi_entitled(self):
        self._check_render_asterisk(True, MachineTypeColumn.MULTI_ENTITLEMENT_STRING)

    def test_render_empty_string_when_not_multi_entitled(self):
        self._check_render_asterisk(False, MachineTypeColumn.NOT_MULTI_ENTITLEMENT_STRING)

    def _check_render_machine_type(self, is_virtual, expected_pix_buf):
        model = gtk.ListStore(bool)
        model.append([is_virtual])

        column = MachineTypeColumn(0, 2)
        column.render_machine_type_icon(None, column.image_renderer, model,
                                        model.get_iter_first())
        self.assertEquals(expected_pix_buf, column.image_renderer.get_property("pixbuf"))

    def _check_render_asterisk(self, is_multi_entitlement, expected_rendered_text):
        model = gtk.ListStore(bool)
        model.append([is_multi_entitlement])

        column = MachineTypeColumn(1, 0)
        column.render_as_multi_entitlement(None, column.asterisk_renderer, model,
                                        model.get_iter_first())
        self.assertEquals(expected_rendered_text, column.asterisk_renderer.get_property("text"))
