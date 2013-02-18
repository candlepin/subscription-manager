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


import os
import mock
import unittest

from iniparse import SafeConfigParser
from StringIO import StringIO
from subscription_manager.plugins import api_version_ok, parse_version, \
        PluginManager, PluginModuleImportApiVersionException, \
        PluginConfigException, BaseConduit, SlotNameException, PluginConfig, \
        BasePluginManager, FactsConduit, PluginModuleImportApiVersionMissingException

from subscription_manager import base_plugin


# SubManPlugin
# plugin_key

# BasePluginManager
#  create
#  load test plugins
#  load no plugins
#  load plugins from bad plugin dir
#  load plugins no conduits
# _import_plugins dupe modules
# _load_plugin_module no modules
# _load_plugin_module import errors
# _load_plugin_module no api version
# _load_plugin_module unmet api ver dep
# add_plugins_from_module same plugin name
# add_plugins_from_module empty module
# add_plugins_from_module no classes
# add_plugins_from_module no SubManPlugin classes
# add_plugins_from_module classes imported into name space
#                         classes with bad new()
#                         no config for class
#                         bad config for class
#                         no enabled in config for class
#                         disabled in config for class
#                         enabled set on and off
#                         plugin classes that set a conf themselves
#                         verify all classes end up in found_plugin_classes
#                         enabled plugins added to _plugins
#                         disabled classes end up tracked as disabled
#                         verify we fail module if any plugin class in that module fails
#                         verify we dont fail module if plugin is disabled
# add_plugin_class
#                plugin_key is set properly
#                plugins instaniated
#                right exceptions on plugin init fail
#                loaded plugins get added to _plugins
#                dupe classes raise PluginException
#                valid plugins added to _plugin_classes
#                verify we handle no slots
#                handle _hook name variantions (ie, foo_hook ok, foo_hook_blip is not
#                   verify we handle '' slot names
#                verify we append found hook to slot_to_funcs
#                verify we DTRT on non callable instances that match
#                        aka (self.post_install_hook = 'asdasd')
#                        we should ignore non callables
#                        verify hooks are bound or class/static methods?
#                if we find a hook, verify clazz.found_slots_for_hooks is True
#                   make sure we handle multiple hooks (if any hooks are used,
#                   we mark class as used
#               can we verify we set the class.used and not the class itself?
#               after adding classes, verify our method of finding used classes is correct
# run
#      check how slot_name in kwargs works
#      make sure we work with no kwargs, None kwargs, empty kwargs
#      verify we dont return any value (can you assert on that? thing = this_does_not_return()
#      check we log  method call correctly, with correct arg
#      verify SlotNameException
#      handle/warn/assert no slots
#      handle slot name not being in slots
#      check that we handle no hooks for a slot
#      verify we handle multiple hooks for a slot
#      handle exeptions on hook invocation, and run rest of hooks
#       handle exceptions on conduit init (probably dont need to
#       conduit look up could fail if we munge self._slot_to_conduit
#     test variables Exceptions on conduit init
#      verify we dont reload plugin config on each conduit init
#      verify conduit logger gets created with correct class name
#        - how would we verufy conduits get there data attributes set after
#          super()?
# Conduits
#     verify we ignore unused kwargs
#
# reporting stuff
#     get_plugins returns all found plugins, including disabled ones
#     get_plugins accounts for used plugins
#
# PluginManager
#   init with no/default args get's our config
#   init with specified search_path/conf_path use those
#   verify _get_conduits only returns class objects, not instances
#   verify _get_conduits is not empty
#
# getPluginManager
#   multiple invocations of getPluginManager returnt he same PluginManager object
#   can we test that getPluginManager is not imported into a local namespace?

class TestBasePluginManager(unittest.TestCase):

    def setUp(self):
        self.base_manager = BasePluginManager()
        self.assertTrue(isinstance(self.base_manager, BasePluginManager))

    def test_add_plugins_from_empty_mock_module(self):
        mock_module = mock.Mock()
        self.base_manager.add_plugins_from_module(mock_module)
        # that was not a module, nor a plugin module, nor had any plugin classes
        # so we better not have any plugins found
        self.assertEquals({}, self.base_manager._slot_to_funcs)
        self.assertEquals({}, self.base_manager._plugin_classes)

    def test_add_plugins_from_module_no_classes(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        self.base_manager.add_plugins_from_module(mock_module)
        # that was not a module, nor a plugin module, nor had any plugin classes
        # so we better not have any plugins found
        self.assertEquals({}, self.base_manager._slot_to_funcs)
        self.assertEquals({}, self.base_manager._plugin_classes)

    def test_add_plugins_from_module_unrelated_classes(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        class NotAPluginClass(object):
            pass

        mock_module.NotAPluginClass = NotAPluginClass
        self.base_manager.add_plugins_from_module(mock_module)
        self.assertEquals({}, self.base_manager._slot_to_funcs)
        self.assertEquals({}, self.base_manager._plugin_classes)

    def test_add_plugins_from_module_plugin_class_no_conf(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"
            pass

        mock_module.PluginClass = PluginClass

        # there is no config for this plugin, so it should raise a
        # PluginConfigException
        self.assertRaises(PluginConfigException, self.base_manager.add_plugins_from_module, mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)

        # these shouldn't get populated for this cases
        self.assertEquals({}, self.base_manager._slot_to_funcs)
        self.assertEquals({}, self.base_manager._plugin_classes)

    def test_add_plugins_from_module_plugin_config_fail(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"
            pass

        mock_module.PluginClass = PluginClass
        # this config is empty, so we will fail to read its config
#        plugin_conf = PluginConfig(PluginClass.get_plugin_key())

        self.assertRaises(PluginConfigException, self.base_manager.add_plugins_from_module, mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)
        # these shouldn't get populated for this cases
        self.assertEquals({}, self.base_manager._slot_to_funcs)
        self.assertEquals({}, self.base_manager._plugin_classes)

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_add_plugins_from_module_plugin_config_disabled(self, mock_plugin_conf):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        mock_conf_instance = mock_plugin_conf.return_value
        mock_conf_instance.is_plugin_enabled.return_value = False

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"
            pass

        # unused in this case
        mock_conf_instance.plugin_key = PluginClass.get_plugin_key()

        mock_module.PluginClass = PluginClass
        # class wont be added, but no exceptions expected.
        # no plugin will be loaded though
        self.base_manager.add_plugins_from_module(mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)
        # these shouldn't get populated for this cases
        self.assertEquals({}, self.base_manager._slot_to_funcs)

        # we shouldn't be in _plugins, since this was disabled
        self.assertFalse(PluginClass.get_plugin_key() in self.base_manager._plugins)

        # however, we were found
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugin_classes)

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_add_plugins_from_module_plugin_config_enabled(self, mock_plugin_conf):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we have to mock this guy, since we dont really want to provide
        # a direct api for providing an alternate config, since that controls
        # if we enable the plugin or not. But maybe that's unneeded and we
        # could just pass add_plugins_from_module a dict of PluginConfs...
        mock_conf_instance = mock_plugin_conf.return_value
        mock_conf_instance.is_plugin_enabled.return_value = True

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"
            pass

        # we validate the plugins_conf plugin key matches...
        mock_conf_instance.plugin_key = PluginClass.get_plugin_key()
        mock_module.PluginClass = PluginClass

        # should be able to load this guy
        self.base_manager.add_plugins_from_module(mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)

        # these shouldn't get populated for this cases, mp slots
        self.assertEquals({}, self.base_manager._slot_to_funcs)

        # we should be in _plugins, since this plugin was enabled
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugins)

        # and we account the plugin class
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugin_classes)

        # we don't provide any hooks (and we haven't setup any slots), so this
        # plugin is "unused"
        self.assertFalse(PluginClass.found_slots_for_hooks)

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_add_plugins_from_module_plugin_unmatch_hooks(self, mock_plugin_conf):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we have to mock this guy, since we dont really want to provide
        # a direct api for providing an alternate config, since that controls
        # if we enable the plugin or not. But maybe that's unneeded and we
        # could just pass add_plugins_from_module a dict of PluginConfs...
        mock_conf_instance = mock_plugin_conf.return_value
        mock_conf_instance.is_plugin_enabled.return_value = True

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

            def this_doesnt_exist_hook(self):
                pass

        # we validate the plugins_conf plugin key matches...
        mock_conf_instance.plugin_key = PluginClass.get_plugin_key()
        mock_module.PluginClass = PluginClass

        # should be able to load this guy
        self.base_manager.add_plugins_from_module(mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)

        # these shouldn't get populated for this cases, mp slots
        self.assertEquals({}, self.base_manager._slot_to_funcs)

        # we should be in _plugins, since this plugin was enabled
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugins)

        # and we account the plugin class
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugin_classes)

        # we don't provide any hooks (and we haven't setup any slots), so this
        # plugin is "unused"
        self.assertFalse(PluginClass.found_slots_for_hooks)

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_add_plugins_from_module_plugin_hooks_with_conduits(self, mock_plugin_conf):
        self.base_manager.conduits = [FactsConduit]
        # to refill these
        self.base_manager._populate_slots()

        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we have to mock this guy, since we dont really want to provide
        # a direct api for providing an alternate config, since that controls
        # if we enable the plugin or not. But maybe that's unneeded and we
        # could just pass add_plugins_from_module a dict of PluginConfs...
        mock_conf_instance = mock_plugin_conf.return_value
        mock_conf_instance.is_plugin_enabled.return_value = True

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

            def this_doesnt_exist_hook(self):
                pass

            def post_facts_collection_hook(self):
                pass

        # we validate the plugins_conf plugin key matches...
        mock_conf_instance.plugin_key = PluginClass.get_plugin_key()
        mock_module.PluginClass = PluginClass

        # should be able to load this guy
        self.base_manager.add_plugins_from_module(mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)

        # we provide conduits with slots, so we should have known slots now
        self.assertTrue('post_facts_collection' in self.base_manager._slot_to_funcs)
        self.assertTrue('post_facts_collection' in self.base_manager._slot_to_conduit)
        self.assertEquals(FactsConduit,
                          self.base_manager._slot_to_conduit['post_facts_collection'])

        # we should be in _plugins, since this plugin was enabled
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugins)

        # and we account the plugin class
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugin_classes)

        # we found hooks that map to slots
        self.assertTrue(PluginClass.found_slots_for_hooks)

        funcs = self.base_manager._slot_to_funcs['post_facts_collection']
        # we find our hook mapped to this slot
        self.assertTrue('post_facts_collection_hook' in [x.__name__ for x in funcs])

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_add_plugins_from_module_with_conduits_no_matching_hooks(self, mock_plugin_conf):
        self.base_manager.conduits = [FactsConduit]
        # to refill these
        self.base_manager._populate_slots()

        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we have to mock this guy, since we dont really want to provide
        # a direct api for providing an alternate config, since that controls
        # if we enable the plugin or not. But maybe that's unneeded and we
        # could just pass add_plugins_from_module a dict of PluginConfs...
        mock_conf_instance = mock_plugin_conf.return_value
        mock_conf_instance.is_plugin_enabled.return_value = True

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

            def this_doesnt_exist_hook(self):
                pass

        # we validate the plugins_conf plugin key matches...
        mock_conf_instance.plugin_key = PluginClass.get_plugin_key()
        mock_module.PluginClass = PluginClass

        # should be able to load this guy
        self.base_manager.add_plugins_from_module(mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)

        # we provide conduits with slots, so we should have known slots now
        self.assertTrue('post_facts_collection' in self.base_manager._slot_to_funcs)
        self.assertTrue('post_facts_collection' in self.base_manager._slot_to_conduit)
        self.assertEquals(FactsConduit,
                          self.base_manager._slot_to_conduit['post_facts_collection'])

        # we should be in _plugins, since this plugin was enabled
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugins)

        # and we account the plugin class
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugin_classes)

        # we found no hooks that map to slots
        self.assertFalse(PluginClass.found_slots_for_hooks)

        funcs = self.base_manager._slot_to_funcs['post_facts_collection']
        # we dont find a hook mapped to this slot
        self.assertFalse('post_facts_collection_hook' in [x.__name__ for x in funcs])


# This is more of a functional test, but for plugins I think that is okay
class TestPluginManager(unittest.TestCase):
    def setUp(self):
        self.module_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.manager = PluginManager("some/search/path", "some/config/path")
        self.manager.plugin_conf_path = self.module_dir
        self.manager.search_path = self.module_dir

    def test_load_plugin_with_no_api_version(self):
        module = os.path.join(self.module_dir, "no_api_version.py")
        self.assertRaises(PluginModuleImportApiVersionMissingException, self.manager._load_plugin_module_file, module)

    def test_load_plugin_with_old_api_version(self):
        module = os.path.join(self.module_dir, "old_api_version.py")
        self.assertRaises(PluginModuleImportApiVersionException, self.manager._load_plugin_module_file, module)

    def test_load_plugin(self):
        module = os.path.join(self.module_dir, "dummy_plugin.py")
        plugin_module = self.manager._load_plugin_module_file(module)
        self.assertEquals("dummy_plugin", plugin_module.__name__)

# FIXME
#    def test_load_plugin_from_module_disabled_config(self):
#        module = os.path.join(self.module_dir, "disabled_plugin.py")
#        # no exceptions, but we should see something in disabled
##        self.assertRaises(PluginConfigException, self.manager._load_plugin_module, module)

    def test_no_config_plugin(self):
        self.assertRaises(PluginConfigException, PluginConfig, "config_plugin.BadConfigPlugin", self.module_dir)

    def test_bad_config_plugin(self):
        self.assertRaises(PluginConfigException, PluginConfig, "config_plugin.BadConfigPlugin", self.module_dir)

    def test_good_config_plugin(self):
        parser = PluginConfig("config_plugin.GoodConfigPlugin", self.module_dir)
        self.assertTrue(parser)

    def test_disabled_plugin(self):
        module = os.path.join(self.module_dir, "disabled_plugin.py")
        self.manager._load_plugin_module_file(module)
        self.assertEquals(0, len(self.manager._plugins))

    def test_run_no_such_slot(self):
        module = os.path.join(self.module_dir, "dummy_plugin.py")
        self.manager.search_path = self.module_dir
        self.manager.plugin_conf_path = self.module_dir
        self.manager._load_plugin_module_file(module)
        self.assertRaises(SlotNameException, self.manager.run, 'this_is_a_slot_that_doesnt_exist')


class TestPluginManagerLoadPlugins(unittest.TestCase):
    def setUp(self):
        self.module_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.manager = PluginManager("some/search/path", "some/config/path")
        self.manager.plugin_conf_path = self.module_dir
        self.manager.search_path = self.module_dir

    def test_load_plugin(self):
        module = os.path.join(self.module_dir, "dummy_plugin.py")
        plugin_module = self.manager._load_plugin_module_file(module)
        self.assertEquals("dummy_plugin", plugin_module.__name__)
        self.manager.add_plugins_from_module(plugin_module)
        self.assertEquals(1, len(self.manager._slot_to_funcs['post_product_id_install']))
        self.assertEquals(0, len(self.manager._slot_to_funcs['pre_product_id_install']))

    def test_load_plugins_with_same_class_name(self):
        module = os.path.join(self.module_dir, "dummy_plugin.py")
        module2 = os.path.join(self.module_dir, "dummy_plugin_2.py")
        plugin_modules = []
        plugin_modules.append(self.manager._load_plugin_module_file(module))
        plugin_modules.append(self.manager._load_plugin_module_file(module2))
        self.manager.add_plugins_from_modules(plugin_modules)
        self.assertEquals(2, len(self.manager._slot_to_funcs['post_product_id_install']))

    def test_load_plugin_from_module_bad_config(self):
        module_file = os.path.join(self.module_dir, "config_plugin.py")
        module = self.manager._load_plugin_module_file(module_file)
        self.assertRaises(PluginConfigException, self.manager.add_plugins_from_module, module)


class TestBaseConduit(unittest.TestCase):
    def setUp(self):
        conf_string = StringIO("")
        self.conf = SafeConfigParser()
        self.conf.readfp(conf_string)
        self.conduit = BaseConduit(BaseConduit, self.conf)

    def test_default_boolean(self):
        val = self.conduit.confBool("main", "enabled", False)
        self.assertEquals(False, val)

    def test_bad_default_boolean(self):
        self.assertRaises(ValueError, self.conduit.confBool, "main", "enabled", "not a bool")

    def test_default_int(self):
        val = self.conduit.confInt("main", "enabled", 1)
        self.assertEquals(1, val)

    def test_bad_default_int(self):
        self.assertRaises(ValueError, self.conduit.confInt, "main", "enabled", "not an int")

    def test_default_float(self):
        val = self.conduit.confFloat("main", "enabled", 1.0)
        self.assertEquals(1.0, val)

    def test_bad_default_float(self):
        self.assertRaises(ValueError, self.conduit.confFloat, "main", "enabled", "not a float")

    def test_default_string(self):
        val = self.conduit.confString("main", "enabled", "a string")
        self.assertEquals("a string", val)


class TestVersionChecks(unittest.TestCase):
    def test_parse_version(self):
        maj, min = parse_version("1.0")
        self.assertEquals(1, maj)
        self.assertEquals(0, min)

    def test_api_versions_equal(self):
        self.assertTrue(api_version_ok("1.0", "1.0"))

    def test_api_version_old_minor(self):
        self.assertTrue(api_version_ok("1.1", "1.0"))

    def test_api_version_old_major(self):
        self.assertFalse(api_version_ok("1.0", "0.9"))

    def test_api_version_new(self):
        self.assertFalse(api_version_ok("1.0", "1.1"))


#class TestFactsPlugin(unittest.TestCase):
#    def setUp(self):
#        self.module_dir = os.path.join(os.path.dirname(__file__), "plugins")
#        self.manager = PluginManager("some/search/path", "some/config/path")
#        self.manager.plugin_conf_path = self.module_dir
#        self.manager.search_path = self.module_dir
#        # reload plugins
#        self.manager._import_plugins()
#
#    @mock.patch.object(FactsConduit, 'getFacts')
#    def test_post_fact_collection(self, mock_facts_gf):
#        mock_facts_gf.return_value = {}
#        self.manager.run('post_facts_collection', facts={})
#        mock_facts_gf.assert_called_once_with()
