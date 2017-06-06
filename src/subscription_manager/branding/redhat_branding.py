from __future__ import print_function, division, absolute_import

from subscription_manager.i18n import ugettext as _


class Branding(object):
    def __init__(self):
        self.CLI_REGISTER = _("Register this system to the Customer Portal or another subscription management service")
        self.CLI_UNREGISTER = _("Unregister this system from the Customer Portal or another subscription management service")
        self.RHSMD_REGISTERED_TO_OTHER = \
                _("This system is registered to RHN Classic.")
        self.REGISTERED_TO_OTHER_WARNING = _("WARNING") + \
            "\n\n" + \
            _("This system has already been registered with Red Hat using RHN Classic.") + \
            "\n\n" + \
            _("Your system is being registered again using Red Hat Subscription Management. Red Hat recommends that customers only register once.") + \
            "\n\n" + \
            _("To learn how to unregister from either service please consult this Knowledge Base Article: https://access.redhat.com/kb/docs/DOC-45563")
        self.REGISTERED_TO_OTHER_SUMMARY = _("RHN Classic")
        self.REGISTERED_TO_SUBSCRIPTION_MANAGEMENT_SUMMARY = _("Red Hat Subscription Management")
        self.GUI_REGISTRATION_HEADER = \
                _("Please enter your Red Hat account information:")
        self.REGISTERED_TO_BOTH_WARNING = \
                _("This system is registered using both RHN Classic and Red Hat Subscription Management.") + \
                "\n\n" + \
                _("Red Hat recommends that customers only register with one service.") + \
                "\n\n" + \
                _("To learn more about RHN registration and technologies please consult this Knowledge Base Article: https://access.redhat.com/kb/docs/DOC-45563")
        self.REGISTERED_TO_BOTH_SUMMARY = _("RHN Classic and Red Hat Subscription Management")
        self.GUI_FORGOT_LOGIN_TIP = \
                _("Tip: Forgot your login or password? Look it up at https://redhat.com/forgot_password")
