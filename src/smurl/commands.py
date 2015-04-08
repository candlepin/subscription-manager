import gettext
import logging
import sys

log = logging.getLogger('rhsm-app.smurl.' + __name__)

from rhsm import connection
from rhsm import ourjson as json

from subscription_manager import managercli
import subscription_manager.injection as inj

_ = gettext.gettext


class ApiCommand(managercli.OrgCommand):
    request_types = ["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH"]

    def __init__(self):
        shortdesc = _("interface to rhsm API")

        self.uuid = inj.require(inj.IDENTITY).uuid

        super(ApiCommand, self).__init__("api", shortdesc, True)
        self.parser.add_option("--auth", dest="auth_type", default="consumer",
                               help=(_("auth type to use: consumer, user, none")))
        self.parser.add_option("-X", dest="request_type", default="GET",
                               help=(_("Type of http request: GET, POST, etc")))
        self.parser.add_option("-d", dest="data",
                               help=(_("Data to send, @filename, or @- for stdin")))
        self.parser.add_option("--method", dest="api_method",
                               default="/status",
                               help=(_("URL to request")))
        self.parser.add_option("--aliases", dest="list_aliases",
                               action="store_true", default=False,
                               help=(_("List the supported method aliases and values")))
        self._add_url_options()

        # FIXME: we could move RegisterCommand._determine_owner to OrgCommand and
        # we use it here to find the default org
        self.aliases = {'{c}': 'uuid',
                        '{consumer_uuid}': 'uuid',
                        #'{o}': self.owner,
                        '{u}': 'username',
                        '{username}': 'username',
                        '{owner_key}': 'username',
                        '{organization}': 'org',
                        '{org}': 'org'}

        # NOTE: what should we do with command line args?
        # assume they are url_methods? query params?

    def _validate_options(self):
        pass

    def _validate_args(self):
        #self.args = self.args[1:]
        # ignore anything bogus atm
        return

    def _parse_args(self):
        if not self.args:
            return

        # Various DWIM hackery to make cli 'do what I mean'
        # pull out things that look like http verbs or methods
        # and use them.
        for arg in self.args:
            # override the default GET if we see 'POST' or 'post'
            # in the free args on the cli. last one wins.
            if arg.upper() in self.request_types:
                self.options.request_type = arg

            # If it looks like a url path/method, try to use it as one
            if self._is_method(arg):
                self.options.api_method = arg

    def _is_method(self, method):
        "Guess if the arg is meant to be a method name."
        return '/' in method

    def expand_aliases(self, method_string):
        # ie, {consumer_uuid} for consumer uuid
        # {owner_key}
        # FIXME: plenty of other ways to do more powerful formatting
        full_method = method_string

        for alias, attr in self.aliases.items():
            if alias in full_method:
                # NOTE: this may prompt for interactive user/pass/org info
                attr_value = getattr(self, attr)
                if attr_value is None:
                    raise Exception("value of expansion of %s in %s was None" % (attr, full_method))

                full_method = full_method.replace(alias, getattr(self, attr))

        return full_method

    def _get_cp(self):
        if self.options.auth_type == 'consumer':
            return self.cp_provider.get_consumer_auth_cp()
        if self.options.auth_type == 'user':
            self.cp_provider.set_user_pass(self.username, self.password)
            return self.cp_provider.get_basic_auth_cp()
        if self.options.auth_type == "none":
            return self.cp_provider.get_no_auth_cp()

        print _("Unknown auth type: %s") % self.options.auth_type
        self._exit(code=1)

    def _exit(self, code=None):
        status_code = code or 0
        sys.exit(status_code)

    def _request(self, cp, request_type, method, info=None):
        return cp.conn._request(request_type, method, info)

    def _do_request(self, cp, request_type, method, info=None):
        try:
            result = self._request(cp, request_type, method, info)
        except connection.RestlibException, e:
            self._show_error(e)
            return

        self._show_result(result)

    def _show_error(self, exc):
        sys.stderr.write("%s\n" % exc)

    def _show_result(self, result):
        print json.dumps(result, indent=4, sort_keys=True)

    def _read_data(self, data_label):
        json_str = None
        if data_label is None:
            return None
        # ala curl -d @-
        elif data_label == '@-':
            json_str = sys.stdin.read()
        # ala curl -d @some_file
        elif data_label.startswith("@"):
            with open(data_label[1:], "r") as data_file:
                json_str = data_file.read()

        if json_str:
            return json.loads(json_str)

        return None

    def _list_aliases(self):
        interactive_attrs = ['username', 'password', 'org']

        for alias in sorted(self.aliases):
            attr_name = self.aliases[alias]

            # FIXME: little ugly to avoid being prompted,
            #        instead just see if the info is specified on cli
            if attr_name in interactive_attrs:
                # avoid the properties that will prompt
                value = getattr(self.options, attr_name)
            else:
                value = getattr(self, attr_name)

            expanded = value or 'Unknown'
            print "%s: %s" % (alias, expanded)

    def _do_command(self):
        self._parse_args()

        log.debug("smurl request with auth %s: %s %s",
                  self.options.auth_type, self.options.request_type,
                  self.options.api_method)

        if self.options.list_aliases:
            self._list_aliases()
            self._exit(code=1)

        request_type = self.options.request_type.upper()

        self._do_request(self._get_cp(),
                         request_type,
                         self.expand_aliases(self.options.api_method),
                         info=self._read_data(self.options.data))

        # TODO: exit with a useful status code
