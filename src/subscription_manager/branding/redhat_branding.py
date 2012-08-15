import gettext
_ = gettext.gettext


class Branding(object):
    def __init__(self):
        self.CLI_REGISTER = _("register the client to the Customer Portal or another subscription management service.")
        self.CLI_UNREGISTER = _("unregister the client from the Customer Portal or another subscription management service.")
        self.RHSMD_REGISTERED_TO_OTHER = \
                _("This system is registered to RHN Classic.")
        self.REGISTERED_TO_OTHER_WARNING = _("WARNING") + \
            "\n\n" + \
            _("This system has already been registered with Red Hat using RHN Classic technology.") + \
            "\n\n" + \
            _("The tool you are using is attempting to re-register using Red Hat Subscription Management technology. Red Hat recommends that customers only register once.") + \
            "\n\n" + \
            _("To learn how to unregister from either service please consult this Knowledge Base Article: https://access.redhat.com/kb/docs/DOC-45563")
        self.REGISTERED_TO_OTHER_SUMMARY = _("RHN Classic")

        self.GUI_REGISTRATION_HEADER = \
                _("Please enter your Red Hat account information:")
        self.REGISTERED_TO_BOTH_WARNING = \
                _("This system is registered using both RHN Classic and Red Hat Subscription Management.") + \
                "\n\n" + \
                _("Red Hat recommends that customers only register to one service.") + \
                "\n\n" + \
                _("To learn more about RHN registration and technologies please consult this Knowledge Base Article: https://access.redhat.com/kb/docs/DOC-45563")
        self.REGISTERED_TO_BOTH_SUMMARY = _("RHN classic and Red Hat Subscription Management")
        self.GUI_FORGOT_LOGIN_TIP = \
                _("Tip: Forgot your login or password? Look it up at http://red.ht/lost_password")
