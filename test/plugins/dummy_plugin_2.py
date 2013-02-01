#! /usr/bin/python

from subscription_manager.base_plugin import SubManPlugin

requires_api_version = "1.0"


# This is the same class name as the plugin in dummy_plugin.py
# We should be able to load both plugins since they are in different
# modules.
class DummyPlugin(SubManPlugin):
    pass
