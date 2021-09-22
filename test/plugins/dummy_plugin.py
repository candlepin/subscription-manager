#! /usr/bin/python
from subscription_manager.base_plugin import SubManPlugin

requires_api_version = "1.0"


class DummyPlugin(SubManPlugin):
    def __init__(self):
        pass

    def post_product_id_install_hook(self, conduit):
        conduit.log.error("Hello World")


class DontImportMe(object):
    pass
