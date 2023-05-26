from subscription_manager.i18n import ugettext as _


class Branding:
    def __init__(self):
        self.CLI_REGISTER = _(
            "Register this system to the Customer Portal or another subscription management service"
        )
        self.CLI_UNREGISTER = _(
            "Unregister this system from the Customer Portal or another subscription management service"
        )
        self.REGISTERED_TO_SUBSCRIPTION_MANAGEMENT_SUMMARY = _("Red Hat Subscription Management")
