#!/usr/bin/env python
#
# Copyright 2017 ATIX AG
# Author: Matthias Dellweg
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Zypper pluging for listing subscription-manager repositories

import os

from subscription_manager import injection as inj
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.injectioninit import init_dep_injection
from rhsm import config

if __name__ == '__main__':
    # Check for uid==0 before reading configuration!
    if os.getuid() != 0:
        sys.exit(0)
    # Rehash CA-certificates since zypper accepts only capath
    C_REHASH = '/usr/bin/c_rehash'
    if os.path.isfile(C_REHASH):
        os.system(C_REHASH + ' /etc/rhsm/ca >/dev/null 2>&1')
    else:
        print '# WARNING: c_rehash could not be found!'
    # Read subscription-manager config
    cfg = config.initConfig()
    full_refresh_on_yum = bool(cfg.get_int('rhsm', 'full_refresh_on_yum'))
    # Start magic
    init_dep_injection()
    rl = RepoActionInvoker(cache_only=not full_refresh_on_yum)
    for repo in rl.get_repos():
        urlparams = list()
        if len(repo['sslverify']) == '1':
            urlparams.append('ssl_verify=true')
        if len(repo['sslclientcert']) != 0:
            urlparams.append('ssl_clientcert=' + repo['sslclientcert'])
        if len(repo['sslclientkey']) != 0:
            urlparams.append('ssl_clientkey=' + repo['sslclientkey'])
        if len(repo['sslcacert']) != 0:
            urlparams.append(
                'ssl_capath=' + os.path.dirname(repo['sslcacert']))
        if len(urlparams) != 0:
            repo['baseurl'] += '?' + '&'.join(urlparams)
        print repo
        print
