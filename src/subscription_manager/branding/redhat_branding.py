import gettext
_ = gettext.gettext


class Branding(object):
    def __init__(self):
        self.CLI_REGISTER = _("register the client to RHN")
        self.CLI_UNREGISTER = _("unregister the client from RHN")
        self.RHSMD_REGISTERED_TO_OTHER = \
                _("This system is registered to RHN Classic")
        self.REGISTERED_TO_OTHER_WARNING = _("WARNING") + \
            "\n" + \
            _("This system has already been registered with RHN using RHN Classic technology.") + \
            "\n" + \
            _("The tool you are using is attempting to re-register using RHN Certificate-Based technology. Red Hat recommends (except in a few cases) that customers only register with RHN once.") + \
            "\n" + \
            _("To learn more about RHN registration and technologies please consult this Knowledge Base Article: https://access.redhat.com/kb/docs/DOC-45563")

        self.GUI_REGISTRATION_HEADER = \
                _("Please enter your Red Hat Network account information:")
        self.GUI_FORGOT_LOGIN_TIP = \
                _("Tip: Forgot your login or password? Look it up at https://www.redhat.com/wapps/sso/rhn/lostPassword.html")
