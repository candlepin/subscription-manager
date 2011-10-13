#
# Copyright (c) 2010 Red Hat, Inc.
#
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

import sys
import ConfigParser
from yum.plugins import TYPE_CORE, TYPE_INTERACTIVE

sys.path.append('/usr/share/rhsm')
from rhsm import connection

# we have a problem in that default setup's, only root
# can make connections to the entitlement server, which
# we need to get the consumer's environment and org
# At the moment, we work around that by just subbing
# in "env" and "org" for the vars. Need a better
# fix clearly.

# this fails as non root
# FIXME: this fais as non root
try:
    from subscription_manager.certlib import ConsumerIdentity
except ImportError:
    ConsumerIdentity = None
except ConfigParser.NoOptionError:
    ConsumerIdentity = None

requires_api_version = '2.5'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)


def populate_yumvars(conduit, env, org):
    for repo in conduit.getRepos().listEnabled():
        repo.yumvar['env'] = env
        repo.yumvar['org'] = org


def _init_hook(conduit):
    # FIXME: we can only run this plugin as root,
    # we do need to handle that

    env = "env"
    org = "org"
    # defaults in case we fail otherwise
    populate_yumvars(conduit, env, org)

    if not ConsumerIdentity:
        conduit.info(2, "Unable to import ConsumerIdentity")
        populate_yumvars(conduit, env, org)
        return

    cert_file = ConsumerIdentity.certpath()
    key_file = ConsumerIdentity.keypath()

    try:
        ConsumerIdentity.read().getConsumerId()
    except Exception, e:
        conduit.error(2, "Unable to read consumer identity")
        return

    has_env = None

    try:
        uep = connection.UEPConnection(cert_file=cert_file, key_file=key_file)
    #FIXME: catchall exception
    except Exception:
        # log
        conduit.info(2, "Unable to connect to entitlement server")
        return

    try:
        has_env = uep.supports_resource('environments')
    except Exception:
        conduit.info(2, "Unable to determine if this server supports environments")
        return

    # This doesn't work sans environments on vanilla candlepin
    if has_env:
        try:
            consumer = uep.getConsumer(ConsumerIdentity.read().getConsumerId())
            # assuming we want id's here..?
            org = consumer['owner']['id']
            env = consumer['environment']['name']
        except connection.RestlibException, e:
            conduit.info(2, e)
            return
    else:
        conduit.info(2, "Unable to find consumer: %s" % ConsumerIdentity.read().getConsumerId())
        # log env not supported on this cp version
        return

    populate_yumvars(conduit, env, org)


def init_hook(conduit):
    try:
        _init_hook(conduit)
    except Exception, e:
        #ugh, but we really don't want to break yum for
        # a rhsm related problem...
        conduit.info(2, "Error running katello plugin: %s" % e)
        return
