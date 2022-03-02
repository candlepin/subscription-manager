# Copyright (c) 2016 Red Hat, Inc.
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

try:
    # Prefer using importlib where available
    import importlib

    def import_class(name):
        """Load a class from the string"""
        comps = name.split(".")
        module = importlib.import_module(".".join(comps[0:-1]))
        return getattr(module, comps[-1])

except ImportError:
    # in cases where importlib is not available (I'm looking at you python 2.6.9)
    # use the older "imp"
    import imp

    def import_class(name):
        """Load a class from a string.  Thanks http://stackoverflow.com/a/547867/61248"""
        components = name.split(".")
        current_level = components[0]
        module_tuple = imp.find_module(current_level)
        module = imp.load_module(current_level, *module_tuple)
        for comp in components[1:-1]:
            # import all the way down to the class
            module_tuple = imp.find_module(comp, module.__path__)
            module = imp.load_module(comp, *module_tuple)
        # the class will be an attribute on the lowest level module
        return getattr(module, components[-1])
