#! /usr/bin/python
from __future__ import print_function, division, absolute_import

from subscription_manager.base_plugin import SubManPlugin

requires_api_version = "1.0"


# This plugin should load but not be enabled.
class DisabledPlugin(SubManPlugin):
    def post_product_id_install_hook(self, conduit):
        conduit.log.error("Hello World")
