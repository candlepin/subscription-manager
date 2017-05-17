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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import mock
import six

from subscription_manager import plugins
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
# get_plugin_manager
#   multiple invocations of get_plugin_manager returnt he same PluginManager object
#   can we test that get_plugin_manager is not imported into a local namespace?


# this test class heavily uses mock to simulate the "default" case
# through PluginManager. The main issue being that PluginConfigs
# init'ed based on the PluginClass passed in, and by defaults, looks
# for a real config file somewhere.
class TestBasePluginManagerAddPluginsFromModule(unittest.TestCase):

    def setUp(self):
        self.base_manager = plugins.BasePluginManager()
        self.assertTrue(isinstance(self.base_manager, plugins.BasePluginManager))

    def test_empty_mock_module(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'
        self.base_manager.add_plugins_from_module(mock_module)
        # that was not a module, nor a plugin module, nor had any plugin classes
        # so we better not have any plugins found
        self.assertEqual({}, self.base_manager._slot_to_funcs)
        self.assertEqual({}, self.base_manager._plugin_classes)

    def test_no_classes(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        self.base_manager.add_plugins_from_module(mock_module)
        # that was not a module, nor a plugin module, nor had any plugin classes
        # so we better not have any plugins found
        self.assertEqual({}, self.base_manager._slot_to_funcs)
        self.assertEqual({}, self.base_manager._plugin_classes)

    def test_unrelated_classes(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        class NotAPluginClass(object):
            pass

        mock_module.NotAPluginClass = NotAPluginClass
        self.base_manager.add_plugins_from_module(mock_module)
        self.assertEqual({}, self.base_manager._slot_to_funcs)
        self.assertEqual({}, self.base_manager._plugin_classes)

    def test_plugin_class_no_conf(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

        mock_module.PluginClass = PluginClass

        # there is no config for this plugin, so it should raise a
        # PluginConfigException
        self.assertRaises(plugins.PluginConfigException,
                          self.base_manager.add_plugins_from_module,
                          mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)

        # these shouldn't get populated for this cases
        self.assertEqual({}, self.base_manager._slot_to_funcs)
        self.assertEqual({}, self.base_manager._plugin_classes)

    def test_plugin_config_fail(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

        mock_module.PluginClass = PluginClass
        # this config is empty, so we will fail to read its config
#        plugin_conf = PluginConfig(PluginClass.get_plugin_key())

        self.assertRaises(plugins.PluginConfigException,
                          self.base_manager.add_plugins_from_module,
                           mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)
        # these shouldn't get populated for this cases
        self.assertEqual({}, self.base_manager._slot_to_funcs)
        self.assertEqual({}, self.base_manager._plugin_classes)

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_plugin_config_disabled(self, mock_plugin_conf):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        mock_conf_instance = mock_plugin_conf.return_value
        mock_conf_instance.is_plugin_enabled.return_value = False

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

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
        self.assertEqual({}, self.base_manager._slot_to_funcs)

        # we shouldn't be in _plugins, since this was disabled
        self.assertFalse(PluginClass.get_plugin_key() in self.base_manager._plugins)

        # however, we were found
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugin_classes)

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_plugin_config_enabled(self, mock_plugin_conf):
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

        # we validate the plugins_conf plugin key matches...
        mock_conf_instance.plugin_key = PluginClass.get_plugin_key()
        mock_module.PluginClass = PluginClass

        # should be able to load this guy
        self.base_manager.add_plugins_from_module(mock_module)

        # we try to load a plugin class for this module, so it should
        # be in the list of tracked modules
        self.assertTrue(mock_module in self.base_manager._modules)

        # these shouldn't get populated for this cases, mp slots
        self.assertEqual({}, self.base_manager._slot_to_funcs)

        # we should be in _plugins, since this plugin was enabled
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugins)

        # and we account the plugin class
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugin_classes)

        # we don't provide any hooks (and we haven't setup any slots), so this
        # plugin is "unused"
        self.assertFalse(PluginClass.found_slots_for_hooks)

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_plugin_unmatch_hooks(self, mock_plugin_conf):
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
        self.assertEqual({}, self.base_manager._slot_to_funcs)

        # we should be in _plugins, since this plugin was enabled
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugins)

        # and we account the plugin class
        self.assertTrue(PluginClass.get_plugin_key() in self.base_manager._plugin_classes)

        # we don't provide any hooks (and we haven't setup any slots), so this
        # plugin is "unused"
        self.assertFalse(PluginClass.found_slots_for_hooks)

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_plugin_hooks_with_conduits(self, mock_plugin_conf):
        self.base_manager.conduits = [plugins.FactsConduit]
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
        self.assertEqual(plugins.FactsConduit,
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
    def test_with_conduits_no_matching_hooks(self, mock_plugin_conf):
        self.base_manager.conduits = [plugins.FactsConduit]
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
        self.assertEqual(plugins.FactsConduit,
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

    @mock.patch('subscription_manager.plugins.PluginConfig')
    def test_with_conduits_non_callable_hooks(self, mock_plugin_conf):
        self.base_manager.conduits = [plugins.FactsConduit]
        # to refill these
        self.base_manager._populate_slots()

        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        mock_conf_instance = mock_plugin_conf.return_value
        mock_conf_instance.is_plugin_enabled.return_value = True

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

            # attr with a hook name, that is not callable
            post_facts_collection_hook = True

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
        self.assertEqual(plugins.FactsConduit,
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


# This is more of a functional test, but for plugins I think that this is okay
# uses test plugins from test/plugins
class TestPluginManager(unittest.TestCase):
    def setUp(self):
        self.module_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.manager = plugins.PluginManager(self.module_dir, self.module_dir)

    def test_load_plugin_with_no_api_version(self):
        module = os.path.join(self.module_dir, "no_api_version.py")
        self.assertRaises(plugins.PluginModuleImportApiVersionMissingException,
                          self.manager._load_plugin_module_file,
                           module)

    def test_load_plugin_with_old_api_version(self):
        module = os.path.join(self.module_dir, "old_api_version.py")
        self.assertRaises(plugins.PluginModuleImportApiVersionException,
                          self.manager._load_plugin_module_file,
                        module)

    def test_load_plugin(self):
        module = os.path.join(self.module_dir, "dummy_plugin.py")
        plugin_module = self.manager._load_plugin_module_file(module)
        self.assertEqual("dummy_plugin", plugin_module.__name__)

    def test_no_config_plugin(self):
        self.assertRaises(plugins.PluginConfigException,
                          plugins.PluginConfig,
                          "config_plugin.BadConfigPlugin",
                           self.module_dir)

    def test_bad_config_plugin(self):
        self.assertRaises(plugins.PluginConfigException,
                          plugins.PluginConfig,
                          "config_plugin.BadConfigPlugin",
                          self.module_dir)

    def test_good_config_plugin(self):
        parser = plugins.PluginConfig("config_plugin.GoodConfigPlugin",
                                      self.module_dir)
        self.assertTrue(parser)


class TestPluginManagerLoadPluginsFromModule(unittest.TestCase):
    def setUp(self):
        self.module_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.manager = plugins.PluginManager("some/search/path", "some/config/path")
        self.manager.plugin_conf_path = self.module_dir
        self.manager.search_path = self.module_dir

    def test_load_plugin(self):
        module = os.path.join(self.module_dir, "dummy_plugin.py")
        plugin_module = self.manager._load_plugin_module_file(module)
        self.assertEqual("dummy_plugin", plugin_module.__name__)
        self.manager.add_plugins_from_module(plugin_module)
        self.assertEqual(1, len(self.manager._slot_to_funcs['post_product_id_install']))
        self.assertEqual(0, len(self.manager._slot_to_funcs['pre_product_id_install']))

    def test_load_plugins_with_same_class_name(self):
        module = os.path.join(self.module_dir, "dummy_plugin.py")
        module2 = os.path.join(self.module_dir, "dummy_plugin_2.py")
        plugin_modules = []
        plugin_modules.append(self.manager._load_plugin_module_file(module))
        plugin_modules.append(self.manager._load_plugin_module_file(module2))
        self.manager.add_plugins_from_modules(plugin_modules)
        self.assertEqual(2, len(self.manager._slot_to_funcs['post_product_id_install']))

    def test_load_plugin_from_module_bad_config(self):
        module_file = os.path.join(self.module_dir, "config_plugin.py")
        module = self.manager._load_plugin_module_file(module_file)
        self.assertRaises(plugins.PluginConfigException,
                          self.manager.add_plugins_from_module,
                          module)

    def test_disabled_plugin(self):
        module_file = os.path.join(self.module_dir, "disabled_plugin.py")
        module = self.manager._load_plugin_module_file(module_file)
        self.manager.add_plugins_from_module(module)
        self.assertEqual(0, len(self.manager._plugins))

    def test_run_no_such_slot(self):
        module_file = os.path.join(self.module_dir, "dummy_plugin.py")
        self.manager.search_path = self.module_dir
        self.manager.plugin_conf_path = self.module_dir
        module = self.manager._load_plugin_module_file(module_file)
        self.manager.add_plugins_from_module(module)
        self.assertRaises(plugins.SlotNameException,
                          self.manager.run,
                        'this_is_a_slot_that_doesnt_exist')


# sub class for testing just for easier init
class PluginConfigForTest(plugins.PluginConfig):
    def __init__(self, plugin_key, enabled):
        super(PluginConfigForTest, self).__init__(plugin_key)
        self.parser.add_section("main")
        self.parser.set("main", "enabled", enabled)


class TestPluginManagerConfigMap(unittest.TestCase):
    class PluginClass(base_plugin.SubManPlugin):
        __module__ = "some_module"

    def setUp(self):
        self.manager = plugins.BasePluginManager()
        self.plugin_config = PluginConfigForTest(self.PluginClass.get_plugin_key(),
                                           enabled='1')
        self.plugin_to_config_map = {self.PluginClass.get_plugin_key(): self.plugin_config}

    def test_plugin_no_config_in_map(self):
        # we look in the map, but can't find anything, so we
        # get a PluginConfigException
        broken_map = {'you_wont_find_this': self.plugin_config}
        self.assertRaises(plugins.PluginConfigException,
                          self.manager.add_plugin_class,
                          self.PluginClass,
                          plugin_to_config_map=broken_map)


class TestPluginManagerConfigMapAllHooks(TestPluginManagerConfigMap):
    # example of how a all_hooks class might work
    class PluginClass(base_plugin.SubManPlugin):
        all_hooks = True
        __module__ = "some_module"

        def __getattr__(self, name):
            if name.endswith('_hook'):
                return self.generic_hook_handler
            raise AttributeError

        def generic_hook_handler(self, conduit):
            pass


class TestPluginManagerConfigMapNotCallable(TestPluginManagerConfigMap):
    # example of how a all_hooks class might work
    class PluginClass(base_plugin.SubManPlugin):
        __module__ = "some_module"

        # non callable hook
        some_non_callable_hook = True

    def test_plugin(self):
        self.manager.add_plugin_class(self.PluginClass,
                                      plugin_to_config_map=self.plugin_to_config_map)


class TestPluginManagerReporting(unittest.TestCase):
    class ConduitPluginManager(plugins.BasePluginManager):
        _conduit_list = []

        def _get_conduits(self):
            return self._conduit_list

    def setUp(self):
        #plugin_class_names = ['Plugin1', 'Plugin2', 'Plugin3']
        plugin_class_names = [str(x) for x in range(0, 10)]
        self.plugin_classes = []

        def test_hook(self):
            pass

        conduit_classes = []
        plugin_classes = []
        for plugin_class_name in plugin_class_names:
            plugin_class = type('PluginClass%s' % plugin_class_name,
                                (base_plugin.SubManPlugin,),
                                 {'test_%s_hook' % plugin_class_name: test_hook})
            conduit_class = type('Conduit%s' % plugin_class_name,
                                 (plugins.BaseConduit,),
                                 {'slots': ['test_%s' % plugin_class_name]})
            plugin_classes.append(plugin_class)
            conduit_classes.append(conduit_class)

        for plugin_class in plugin_classes:
            self.plugin_classes.append(plugin_class)

        self.ConduitPluginManager._conduit_list = conduit_classes
        self.manager = self.ConduitPluginManager()

    def test_factory(self):
        plugin_to_config_map = {}
        for plugin_class in self.plugin_classes:
            plugin_config = PluginConfigForTest(plugin_class.get_plugin_key(),
                                                enabled='1')
            plugin_to_config_map[plugin_class.get_plugin_key()] = plugin_config

        for plugin_class in self.plugin_classes:
            self.manager.add_plugin_class(plugin_class,
                                          plugin_to_config_map=plugin_to_config_map)

        self.assertEqual(10, len(self.manager.get_plugins()))
        self.assertEqual(10, len(self.manager.get_slots()))


#functional
class TestPluginManagerRun(unittest.TestCase):
    def setUp(self):
        self.module_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.manager = plugins.PluginManager("some/search/path", "some/config/path")
        self.manager.conduits = [plugins.ProductConduit]
        self.manager._populate_slots()
        self.manager.plugin_conf_path = self.module_dir
        self.manager.search_path = self.module_dir
        module = os.path.join(self.module_dir, "dummy_plugin.py")
        plugin_module = self.manager._load_plugin_module_file(module)
        self.manager.add_plugins_from_module(plugin_module)

    def test_dummy_run(self):
        self.manager.run("post_product_id_install", product_list=[])

    def test_bad_conduit(self):
        self.assertRaises(TypeError, self.manager.run,
                          "post_product_id_install",
                           not_an_actual_arg=None)

    def test_hook_raises_exception(self):
        class ExceptionalPluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

            def post_product_id_install_hook(self, conduit):
                raise IndexError

        plugin_config = PluginConfigForTest(ExceptionalPluginClass.get_plugin_key(),
                                            enabled='1')

        plugin_to_config_map = {ExceptionalPluginClass.get_plugin_key(): plugin_config}
        self.manager.add_plugin_class(ExceptionalPluginClass,
                                      plugin_to_config_map=plugin_to_config_map)
        self.assertRaises(IndexError, self.manager.run,
                          'post_product_id_install', product_list=[])


class TestPluginManagerRunIter(TestPluginManagerRun):
    def setUp(self):
        super(TestPluginManagerRunIter, self).setUp()

        # add dummy 2 and 3, so we have multiple hooks registered for the same
        # slot
        module = os.path.join(self.module_dir, "dummy_plugin_2.py")
        plugin_module = self.manager._load_plugin_module_file(module)
        self.manager.add_plugins_from_module(plugin_module)

        module = os.path.join(self.module_dir, "dummy_plugin_3.py")
        plugin_module = self.manager._load_plugin_module_file(module)
        self.manager.add_plugins_from_module(plugin_module)
        # add

    def test_dummy_runiter(self):
        for runner in self.manager.runiter("post_product_id_install", product_list=[]):
            runner.run()

    def test_iter_wrapper(self):
        class Wrapper(object):
            def __init__(self, runner):
                self.runner = runner
                self.runner_func = self.runner.func
                self.runner_conduit = self.runner.conduit
                self.status = 0

            def update(self):
                self.runner.run()
                self.status = 1

        for runner in self.manager.runiter("post_product_id_install", product_list=[]):
            wrapper = Wrapper(runner)
            wrapper.update()

    def test_update_content_iter(self):
        reports = set()
        reports.add("Started with this")

        ent_source = []

        for runner in self.manager.runiter("update_content",
                                           reports=reports,
                                           ent_source=ent_source):
            runner.run()


class BaseConduitTest(unittest.TestCase):
    conf_buf = ""

    def setUp(self):
        self.conf_io = six.StringIO(self.conf_buf)
        self.conduit = self._conduit()

    def _conduit(self):
        mock_module = mock.Mock()
        mock_module.__name__ = 'mock_module'

        # we check that the plugin's thinks it is from the same
        # module as the module we pass
        class PluginClass(base_plugin.SubManPlugin):
            __module__ = "mock_module"

        plugin_config = plugins.PluginConfig(PluginClass.get_plugin_key)
        plugin_config.parser.readfp(self.conf_io)

        #
        conduit = plugins.BaseConduit(PluginClass,
                                      plugin_config)
        return conduit


class TestBaseConduitEmptyUsesDefaults(BaseConduitTest):
    def test_default_boolean_false(self):
        val = self.conduit.conf_bool("main", "enabled", False)
        self.assertEqual(False, val)

    def test_default_boolean_true(self):
        val = self.conduit.conf_bool("main", "enabled", True)
        self.assertEqual(True, val)

    def test_bad_default_boolean(self):
        self.assertRaises(ValueError,
                          self.conduit.conf_bool,
                           "main", "enabled", "not a bool")

    def test_boolean_no_section(self):
        self.assertRaises(ValueError,
                          self.conduit.conf_bool,
                          'this_section_is_not_real', 'enabled')

    def test_default_int(self):
        val = self.conduit.conf_int("main", "enabled", 1)
        self.assertEqual(1, val)

    def test_bad_default_int(self):
        self.assertRaises(ValueError,
                          self.conduit.conf_int,
                          "main", "enabled", "not an int")

    def test_default_float(self):
        val = self.conduit.conf_float("main", "enabled", 1.0)
        self.assertEqual(1.0, val)

    def test_bad_default_float(self):
        self.assertRaises(ValueError,
                          self.conduit.conf_float,
                          "main", "enabled", "not a float")

    def test_default_string(self):
        val = self.conduit.conf_string("main", "enabled", "a string")
        self.assertEqual("a string", val)

    def test_string_no_section(self):
        val = self.conduit.conf_string('this_section_is_not_real', 'enabled')
        self.assertTrue(val is None)


class TestBaseConduitDefaultConfig(BaseConduitTest):
    conf_buf = """
[main]
enabled=False
"""


class TestBaseConduitConfig(BaseConduitTest):
    conf_buf = """
[main]
enabled=True
street=place
notabool=0.7

[section1]
string_value=Foo
int_value=37
not_an_int=justastring
not_a_float=sdfadf
float_value=1.0
bool_value=True
"""

    def test_enabled(self):
        val = self.conduit.conf_bool("main", "enabled")
        self.assertTrue(val)

    def test_enabled_default(self):
        val = self.conduit.conf_bool("main", "enabled", False)
        self.assertTrue(val)

    def test_default_boolean_true(self):
        val = self.conduit.conf_bool("main", "enabled", True)
        self.assertTrue(val)

    def test_bad_default_boolean(self):
        self.assertRaises(ValueError,
                          self.conduit.conf_bool,
                           "main", "notabool", "not a bool")

    def test_boolean_no_section(self):
        self.assertRaises(ValueError,
                          self.conduit.conf_bool,
                          'this_section_is_not_real', 'enabled')

    def test_int(self):
        val = self.conduit.conf_int("section1", "int_value")
        self.assertEqual(37, val)

    def test_int_default(self):
        val = self.conduit.conf_int("section1", "int_value", 37)
        self.assertEqual(37, val)

    def test_bad_default_int(self):
        self.assertRaises(ValueError,
                          self.conduit.conf_int,
                          "section1", "not_an_int", "not an int")

    def test_default_float(self):
        val = self.conduit.conf_float("section1", "float_value", 1.0)
        self.assertEqual(1.0, val)

    def test_bad_default_float(self):
        self.assertRaises(ValueError,
                          self.conduit.conf_float,
                          "section1", "not_a_float", "not a float")

    def test_string(self):
        val = self.conduit.conf_string("section1", "string_value")
        self.assertEqual("Foo", val)

    def test_default_string(self):
        val = self.conduit.conf_string("section1", "string_value", "bar")
        self.assertEqual("Foo", val)

    def test_string_no_section(self):
        val = self.conduit.conf_string('this_section_is_not_real', 'enabled')
        self.assertTrue(val is None)


class TestVersionChecks(unittest.TestCase):
    def test_parse_version(self):
        maj_ver, min_ver = plugins.parse_version("1.0")
        self.assertEqual(1, maj_ver)
        self.assertEqual(0, min_ver)

    def test_api_versions_equal(self):
        self.assertTrue(plugins.api_version_ok("1.0", "1.0"))

    def test_api_version_old_minor(self):
        self.assertTrue(plugins.api_version_ok("1.1", "1.0"))

    def test_api_version_old_major(self):
        self.assertFalse(plugins.api_version_ok("1.0", "0.9"))

    def test_api_version_new(self):
        self.assertFalse(plugins.api_version_ok("1.0", "1.1"))


class StubPluginClass(base_plugin.SubManPlugin):
    pass


class TestProductConduit(unittest.TestCase):
    def test_product_conduit(self):
        conduit = plugins.ProductConduit(StubPluginClass, product_list=[])
        self.assertEqual([], conduit.product_list)


class TestProductUpdateConduit(unittest.TestCase):
    def test_product_update_conduit(self):
        conduit = plugins.ProductUpdateConduit(StubPluginClass, product_list=[])
        self.assertEqual([], conduit.product_list)


class TestFactsConduit(unittest.TestCase):
    def test_facts_conduit(self):
        conduit = plugins.FactsConduit(StubPluginClass, facts={})
        self.assertEqual({}, conduit.facts)


class TestUpdateContentConduit(unittest.TestCase):
    def test_content_plugin_conduit(self):
        mock_reports = mock.Mock()

        # out ent source is a empty list (of mock entitlements)
        mock_ent_source = []
        conduit = plugins.UpdateContentConduit(StubPluginClass,
                                               reports=mock_reports,
                                               ent_source=mock_ent_source)
        self.assertEqual(mock_reports, conduit.reports)


class TestRegistrationConduit(unittest.TestCase):
    def test_registration_conduit(self):
        conduit = plugins.RegistrationConduit(StubPluginClass,
                                              name="name",
                                              facts={})
        self.assertEqual("name", conduit.name)
        self.assertEqual({}, conduit.facts)


class TestPostRegistrationConduit(unittest.TestCase):
    def test_post_registration_conduit(self):
        conduit = plugins.PostRegistrationConduit(StubPluginClass,
                                                  consumer={'uuid': 'some_uuid'},
                                                  facts={})
        self.assertEqual("some_uuid", conduit.consumer['uuid'])
        self.assertEqual({}, conduit.facts)


class TestSubscriptionConduit(unittest.TestCase):
    def test_subscription_conduit(self):
        conduit = plugins.SubscriptionConduit(StubPluginClass,
                                              consumer_uuid="123456789",
                                              pool_id="4444",
                                              quantity=4)
        self.assertEqual("123456789", conduit.consumer_uuid)
        self.assertEqual(4, conduit.quantity)
        self.assertEqual("4444", conduit.pool_id)


class TestPostSubscriptionConduit(unittest.TestCase):
    def test_post_subscription_conduit(self):
        conduit = plugins.PostSubscriptionConduit(StubPluginClass,
                                                  consumer_uuid="123456789",
                                                  entitlement_data={})
        self.assertEqual("123456789", conduit.consumer_uuid)
        self.assertEqual({}, conduit.entitlement_data)


class TestAutoAttachConduit(unittest.TestCase):
    def test_auto_attach_conduit(self):
        conduit = plugins.AutoAttachConduit(StubPluginClass, "a-consumer-uuid")
        self.assertEqual("a-consumer-uuid", conduit.consumer_uuid)


class TestPostAutoAttachConduit(unittest.TestCase):
    def test_post_auto_attach_conduit(self):
        conduit = plugins.PostAutoAttachConduit(StubPluginClass,
                                                "a-consumer-uuid",
                                                {})
        self.assertEqual("a-consumer-uuid", conduit.consumer_uuid)
        self.assertEqual({}, conduit.entitlement_data)


class BasePluginException(unittest.TestCase):
    """At least create and raise all the exceptions."""
    e = plugins.PluginException

    def raise_exception(self):
        raise self.e

    def test_exception(self):
        self.assertRaises(self.e,
                          self.raise_exception)


class TestPluginException(BasePluginException):
    def test_add_message(self):
        # the base PluginException is expected to just ignore any args
        # so just tested we dont raise anything in this case
        self.e("hello exception")


class TestPluginImportException(BasePluginException):
    e = plugins.PluginImportException

    def raise_exception(self):
        raise self.e("module_file", "module_name", "import failed")

    def test(self):
        try:
            self.raise_exception()
        except self.e as exp:
            self.assertEqual("module_file", exp.module_file)
            self.assertEqual("module_name", exp.module_name)

    def test_str(self):
        try:
            self.raise_exception()
        except self.e as exp:
            buf = str(exp)
            lines = buf.splitlines()
            # last line is Message:...
            self.assertEqual("Message: import failed", lines[-1])


class TestPluginModuleImportException(TestPluginImportException):
    e = plugins.PluginModuleImportException


class TestPluginModuleImportApiVersionMissingException(TestPluginImportException):
    e = plugins.PluginModuleImportApiVersionMissingException


class TestPluginModuleImportApiVersionException(TestPluginImportException):
    e = plugins.PluginModuleImportApiVersionException

    def raise_exception(self):
        raise self.e("module_file",
                     "module_name",
                     "module_ver",
                     "api_ver",
                     "import failed")


class TestPluginConfigException(BasePluginException):
    e = plugins.PluginConfigException

    def raise_exception(self):
        raise self.e("plugin_name",
                     "msg")

    def test_str(self):
        try:
            self.raise_exception()
        except self.e as exp:
            buf = str(exp)
            lines = buf.splitlines()
            # last line is Message:...
            self.assertEqual("Message: msg", lines[-1])


class TestSlotNameException(BasePluginException):
    e = plugins.SlotNameException

    def raise_exception(self):
        raise self.e("slot_name")

    def test(self):
        try:
            self.raise_exception()
        except self.e as exp:
            self.assertEqual("slot_name", exp.slot_name)
            self.assertTrue("slot_name" in str(exp))
