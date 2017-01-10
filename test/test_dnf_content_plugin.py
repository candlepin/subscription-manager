#
# -*- coding: utf-8 -*-

import imp
import os
import types

from nose.plugins.skip import SkipTest

try:
    import dnf
    import librepo
except ImportError as e:
    raise SkipTest(e)


import fixture


# Yeah, this is weird. The yum plugins aren't on sys.path, nor are they in the
# local src path that nosetest searches for modules. src/plugins is also not a
# package dir (no __init__). And to top it off, the module name isn't a valid
# python module name ('product-id.py', ie with an invalid '-').
rel_path = "../src/dnf-plugins/product-id.py"
plugin_file_path = os.path.join(os.path.dirname(__file__), rel_path)
plugin_file = open(plugin_file_path, 'r')

dir_path, module_name = os.path.split(plugin_file_path)
module_name = module_name.split(".py")[0]


# NOTE: the yum plugin 'product-id' gets imported as yum_product_id
fp, pathname, description = imp.find_module(module_name, [dir_path])
try:
    dnf_product_id = imp.load_module('dnf_product_id', fp, pathname, description)
except ImportError as e:
    raise SkipTest(e)
finally:
    fp.close()


class TestDnfPluginModule(fixture.SubManFixture):
    def setUp(self):
        super(TestDnfPluginModule, self).setUp()

    def test(self):
        self.assertTrue(isinstance(dnf_product_id, types.ModuleType))
        self.assertTrue(isinstance(dnf, types.ModuleType))
        self.assertTrue(isinstance(librepo, types.ModuleType))
