import gettext
_ = gettext.gettext


class Branding(object):
    def __init__(self):
        self.CLI_REGISTER = _("register the client to RHN")
        self.CLI_UNREGISTER = _("unregister the client from RHN")
        self.RHSMD_REGISTERED_TO_OTHER = \
                _("This system is registered to RHN Classic")
        self.REGISTERED_TO_OTHER_WARNING = _("WARNING") + \
            "\n\n" + \
            _("This system has already been registered with RHN using RHN Classic technology.") + \
            "\n\n" + \
            _("The tool you are using is attempting to re-register using RHN Certificate-Based technology. Red Hat recommends (except in a few cases) that customers only register with RHN once.") + \
            "\n\n" + \
            _("To learn more about RHN registration and technologies please consult this Knowledge Base Article: https://access.redhat.com/kb/docs/DOC-45563")

        self.GUI_REGISTRATION_HEADER = \
                _("Please enter your Red Hat account information:")
        self.REGISTERED_TO_BOTH_WARNING = \
                _("This system is registered using both RHN Classic technology and RHN Certificate-Based technology.") + \
                "\n\n" + \
                _("Red Hat recommends (except in a few cases) that customers only register with RHN via one method.") + \
                "\n\n" + \
                _("To learn more about RHN registration and technologies please consult this Knowledge Base Article: https://access.redhat.com/kb/docs/DOC-45563")
        self.GUI_FORGOT_LOGIN_TIP = \
                _("Tip: Forgot your login or password? Look it up at http://red.ht/lost_password")
