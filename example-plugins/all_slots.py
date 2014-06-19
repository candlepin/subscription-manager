#
# Copyright (c) 2013 Red Hat, Inc.
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
import types


from subscription_manager.base_plugin import SubManPlugin
requires_api_version = "1.0"


class AllSlotsPlugin(SubManPlugin):
    """Plugin with hooks for all slots."""
    name = "all_slots"
    all_slots = True

    def __init__(self, conf=None):
        super(AllSlotsPlugin, self).__init__(conf)

    def __getattr__(self, attrname):
        if attrname.endswith('_hook'):
            # if we get asked for a hook method, create one based on
            # "handler", set a slot_name attribute on it, and bind it
            # to our class with correct attribute name
            def handler(self, conduit):
                conduit.log.debug("%s all_slots_handler: %s slot_name: %s" %
                                  (self.name, handler, handler.slot_name))

            # add a slot_name attr to the handler method obj itself
            setattr(handler, 'slot_name', attrname[:-5])

            # create a new instance of it, and bind it to self
            new_hook = types.MethodType(handler, self, AllSlotsPlugin)

            # make the accesor point to the new method
            setattr(self, attrname, new_hook)

            # might we well return what we set via now working
            # attr lookup
            return getattr(self, attrname)

        # not a hook name, so legit attr error
        raise AttributeError
