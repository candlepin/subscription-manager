

from subscription_manager.certlib import DataLib


class BrandingLib(DataLib):
    def __init__(self, lock=None, uep=None):
        super(BrandingLib, self).__init__(self, lock, uep)

    def _do_update(self):
        # see if we need to update branding
        # check entitlement certs for Products with branding info
        # For the products with branding info:
        #   if we have that product installed:
        #      create Brand()
        #      update Brand()
        #         which should probably assume existing file
        #         is a "cache" and not update if need be
        pass
