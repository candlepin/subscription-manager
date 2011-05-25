import gettext
_ = gettext.gettext

class Branding(object):
    def __init__(self):
        self.CLI_REGISTER = _("register the client to RHN")
        self.CLI_UNREGISTER = _("unregister the client from RHN")
        self.RHSMD_REGISTERED_TO_OTHER = \
                _("This system is registered to RHN Classic")
        self.REGISTERED_TO_OTHER_WARNING = _("""WARNING

You have already registered with RHN using RHN Classic technology. This tool requires registration using RHN Certificate-Based Entitlement technology.

Except for a few cases, Red Hat recommends customers only register with RHN once.

For more information, including alternate tools, consult this Knowledge Base Article: https://access.redhat.com/kb/docs/DOC-45563
""")

        self.GUI_REGISTRATION_HEADER = \
                _("Please enter your Red Hat Network account information:")
        self.GUI_FORGOT_LOGIN_TIP = \
                _("""Tip: Forgot your login or password? Look it up at
https://www.redhat.com/wapps/sso/rhn/lostPassword.html""")
