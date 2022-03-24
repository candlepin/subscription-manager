# -*- coding: utf-8 -*-
# ^ is to prevent selinux denials trying to load modules from unintended
#   paths. See https://bugzilla.redhat.com/show_bug.cgi?id=1136163
from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

# hack to allow bytes/strings to be interpolated w/ unicode values (gettext gives us bytes)
# Without this, for example, "Формат: %s\n" % u"foobar" will fail with UnicodeDecodeError
# See http://stackoverflow.com/a/29832646/6124862 for more details
import sys
import six
if six.PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

import signal
import logging
import dbus.mainloop.glib
import base64

from subscription_manager import logutil
import subscription_manager.injection as inj

from rhsm import connection, config

from subscription_manager import ga_loader
ga_loader.init_ga()

from subscription_manager.injectioninit import init_dep_injection
init_dep_injection()

from subscription_manager import action_client
from subscription_manager import managerlib
from subscription_manager.identity import ConsumerIdentity
from subscription_manager.i18n_optparse import OptionParser, \
    WrappedIndentedHelpFormatter, USAGE
from optparse import SUPPRESS_HELP
from subscription_manager.utils import generate_correlation_id

from subscription_manager.i18n import ugettext as _

from cloud_what.provider import detect_cloud_provider, CLOUD_PROVIDERS
from rhsmlib.services.register import RegisterService


def exit_on_signal(_signumber, _stackframe):
    sys.exit(0)


def _collect_cloud_info(cloud_list, log):
    """
    Try to collect cloud information: metadata and signature provided by cloud provider.
    :param cloud_list: The list of detected cloud providers. In most cases the list contains only one item.
    :param log: logging object
    :return: The dictionary with metadata and signature (when signature is provided by cloud provider).
        Metadata and signature are base64 encoded. Empty dictionary is returned, when it wasn't
        possible to collect any metadata
    """

    # Create dispatcher dictionary from the list of supported cloud providers
    cloud_providers = {
        provider_cls.CLOUD_PROVIDER_ID: provider_cls for provider_cls in CLOUD_PROVIDERS
    }

    result = {}
    # Go through the list of detected cloud providers and try to collect
    # metadata. When metadata are gathered, then break the loop
    for cloud_provider_id in cloud_list:
        # hw_info is set to {}, because we do not need to detect cloud providers
        cloud_provider = cloud_providers[cloud_provider_id](hw_info={})

        # Try to get metadata first
        metadata = cloud_provider.get_metadata()

        # When it wasn't possible to get metadata for this cloud provider, then
        # continue with next detected cloud provider
        if metadata is None:
            log.warning('No metadata gathered for cloud provider: {cloud_provider_id}'.format(
                cloud_provider_id=cloud_provider_id
            ))
            continue

        # Try to get signature
        signature = cloud_provider.get_signature()

        # When it is not possible to get signature for given cloud provider,
        # then silently set signature to empty string, because some cloud
        # providers does not provide signatures
        if signature is None:
            signature = ""

        log.info('Metadata and signature gathered for cloud provider: {cloud_provider_id}'.format(
            cloud_provider_id=cloud_provider_id
        ))

        # Encode metadata and signature using base64 encoding. Because base64.b64encode
        # returns values as bytes, then we decode it to string using ASCII encoding.
        b64_metadata = base64.b64encode(bytes(metadata)).decode('ascii')
        b64_signature = base64.b64encode(bytes(signature)).decode('ascii')

        result = {
            'cloud_id': cloud_provider_id,
            'metadata': b64_metadata,
            'signature': b64_signature
        }
        break

    return result


def _auto_register(cp_provider, log):
    """
    Try to perform auto-registration
    :param cp_provider: provider of connection to candlepin server
    :param log: logging object
    :return: None
    """
    log.debug("Trying to do auto-registration of this system")

    identity = inj.require(inj.IDENTITY)
    if identity.is_valid() is True:
        log.debug('System already registered. Skipping auto-registration')
        return

    log.debug('Trying to detect cloud provider')

    # Try to detect cloud provider first. Use lower threshold in this case,
    # because we want to have more sensitive detection in this case
    # (automatic registration is more important than reporting of facts)
    cloud_list = detect_cloud_provider(threshold=0.3)
    if len(cloud_list) == 0:
        log.warning('This system does not run on any supported cloud provider. Skipping auto-registration')
        sys.exit(-1)

    # When some cloud provider(s) was detected, then try to collect metadata
    # and signature
    cloud_info = _collect_cloud_info(cloud_list, log)
    if len(cloud_info) == 0:
        log.warning('It was not possible to collect any cloud metadata. Unable to perform auto-registration')
        sys.exit(-1)

    # Get connection not using any authentication
    cp = cp_provider.get_no_auth_cp()

    # Try to get JWT token from candlepin (cloud registration adapter)
    try:
        jwt_token = cp.getJWToken(
            cloud_id=cloud_info['cloud_id'],
            metadata=cloud_info['metadata'],
            signature=cloud_info['signature']
        )
    except Exception as err:
        log.error('Unable to get JWT token: {err}'.format(err=str(err)))
        log.warning('Canceling auto-registration')
        sys.exit(-1)

    # Try to register using JWT token
    register_service = RegisterService(cp=cp)
    # Organization ID is set to None, because organization ID is
    # included in JWT token
    try:
        register_service.register(org=None, jwt_token=jwt_token)
    except Exception as err:
        log.error("Unable to auto-register: {err}".format(err=err))
        sys.exit(-1)
    else:
        log.debug("Auto-registration performed successfully")
        sys.exit(0)


def _main(options, log):
    # Set default mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # exit on SIGTERM, otherwise finally statements don't run (one explanation: http://stackoverflow.com/a/41840796)
    # SIGTERM happens for example when systemd wants the service to stop
    # without finally statements, we get confusing behavior (ex. see bz#1431659)
    signal.signal(signal.SIGTERM, exit_on_signal)

    cp_provider = inj.require(inj.CP_PROVIDER)
    correlation_id = generate_correlation_id()
    log.debug('X-Correlation-ID: %s', correlation_id)
    cp_provider.set_correlation_id(correlation_id)
    cfg = config.initConfig()

    log.debug('check for rhsmcertd disable')
    if '1' == cfg.get('rhsmcertd', 'disable') and not options.force:
        log.warning('The rhsmcertd process has been disabled by configuration.')
        sys.exit(-1)

    # Was script exectured with --auto-register option
    if options.auto_register is True:
        _auto_register(cp_provider, log)

    if not ConsumerIdentity.existsAndValid():
        log.error('Either the consumer is not registered or the certificates' +
                  ' are corrupted. Certificate update using daemon failed.')
        sys.exit(-1)
    print(_('Updating entitlement certificates & repositories'))

    cp = cp_provider.get_consumer_auth_cp()
    cp.supports_resource(None)  # pre-load supported resources; serves as a way of failing before locking the repos

    try:
        if options.autoheal:
            actionclient = action_client.HealingActionClient()
        else:
            actionclient = action_client.ActionClient()

        actionclient.update(options.autoheal)

        for update_report in actionclient.update_reports:
            # FIXME: make sure we don't get None reports
            if update_report:
                print(update_report)

    except connection.ExpiredIdentityCertException as e:
        log.critical(_("Your identity certificate has expired"))
        raise e
    except connection.GoneException as ge:
        uuid = ConsumerIdentity.read().getConsumerId()

        # This code is to prevent an errant 410 response causing consumer cert deletion.
        #
        # If a server responds with a 410, we want to very that it's not just a 410 http status, but
        # also that the response is from candlepin, and include the right info about the consumer.
        #
        # A connection to the entitlement server could get an unintentional 410 response. A common
        # cause for that kind of error would be a bug or crash or misconfiguration of a reverse proxy
        # in front of candlepin. Most error codes we treat as temporary and transient, and they don't
        # cause any action to be taken (aside from error handling). But since consumer deletion is tied
        # to the 410 status code, and that is difficult to recover from, we try to be a little bit
        # more paranoid about that case.
        #
        # So we look for both the 410 status, and the expected response body. If we get those
        # then python-rhsm will create a GoneException that includes the deleted_id. If we get
        # A GoneException and the deleted_id matches, then we actually delete the consumer.
        #
        # However... If we get a GoneException and it's deleted_id does not match the current
        # consumer uuid, we do not delete the consumer. That would require using a valid consumer
        # cert, but making a request for a different consumer uuid, so unlikely. Could register
        # with --consumerid get there?
        if ge.deleted_id == uuid:
            log.critical("Consumer profile \"%s\" has been deleted from the server. Its local certificates will now be archived", uuid)
            managerlib.clean_all_data()
            log.critical("Certificates archived to '/etc/pki/consumer.old'. Contact your system administrator if you need more information.")

        raise ge


def main():
    logutil.init_logger()
    log = logging.getLogger('rhsm-app.' + __name__)

    parser = OptionParser(usage=USAGE,
                          formatter=WrappedIndentedHelpFormatter())
    parser.add_option("--autoheal", dest="autoheal", action="store_true",
            default=False, help="perform an autoheal check")
    parser.add_option("--force", dest="force", action="store_true",
            default=False, help=SUPPRESS_HELP)
    parser.add_option(
            "--auto-register", dest="auto_register", action="store_true",
            default=False, help="perform auto-registration"
    )

    (options, args) = parser.parse_args()
    try:
        _main(options, log)
    except SystemExit as se:
        # sys.exit triggers an exception in older Python versions, which
        # in this case  we can safely ignore as we do not want to log the
        # stack trace. We need to check the code, since we want to signal
        # exit with failure to the caller. Otherwise, we will exit with 0
        if se.code:
            sys.exit(-1)
    except Exception as e:
        log.error("Error while updating certificates using daemon")
        print(_('Unable to update entitlement certificates and repositories'))
        log.exception(e)
        sys.exit(-1)


if __name__ == '__main__':
    main()
