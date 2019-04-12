#! /usr/bin/python
from __future__ import print_function, division, absolute_import

from subscription_manager.base_plugin import SubManPlugin

requires_api_version = "1.0"


# Another plugin that implements 'post_product_id_install_hook',
# so we can test plugin runtiter
class DummyPlugin3(SubManPlugin):
    def __init__(self):
        pass

    def post_product_id_install_hook(self, conduit):
        conduit.log.error("Hello World")
        conduit.product_list.append("Not a product actually")

    def update_content_hook(self, conduit):
        conduit.log.debug("Hellow new content!")
        conduit.reports.add("Not really a report")
