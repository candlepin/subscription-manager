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
from yum.plugins import TYPE_CORE, TYPE_INTERACTIVE


sys.path.append('/usr/share/rhsm')
from rhsm import connection
from subscription_manager.certlib import  ConsumerIdentity

requires_api_version = '2.5'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)


def init_hook(conduit):
    # FIXME: we can only run this plugin as root,
    # we do need to handle that

    cert_file = ConsumerIdentity.certpath()
    key_file = ConsumerIdentity.keypath()
    uep = connection.UEPConnection(cert_file=cert_file, key_file=key_file)

    # This doesn't work sans environments on vanilla candlepin
    if uep.supports_resource('environments'):
        consumer = uep.getConsumer(ConsumerIdentity.read().getConsumerId())

        # assuming we want id's here..?
        org = consumer['owner']['id']
        env = consumer['environment']['id']
    else:
        org = "org"
        env = "env"

    for repo in conduit.getRepos().listEnabled():
        repo.yumvar['env'] = env
        repo.yumvar['org'] = org
        print repo.yumvar
