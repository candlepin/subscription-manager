#! /usr/bin/python

from __future__ import print_function, division, absolute_import

from subscription_manager.base_plugin import SubManPlugin

requires_api_version = "1.0"


# This plugin should fail to load as there is no associated
# config file.
class NoConfigPlugin(SubManPlugin):
    pass


# This plugin should fail to load as there is a malformed
# associated config file.
class BadConfigPlugin(SubManPlugin):
    pass


# This plugin should load.
class GoodConfigPlugin(SubManPlugin):
    pass
