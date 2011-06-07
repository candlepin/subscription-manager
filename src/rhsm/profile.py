#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
import rpm

class InvalidProfileType(Exception):
    pass

class RPMProfile(object):

    def collect(self):
        """ 
	 Initialize rpm transaction and invoke the accumulation call 
	 @return : list of package info dicts
         @rtype: list
	"""
        ts = rpm.TransactionSet()
        ts.setVSFlags(-1)
        installed = ts.dbMatch()
        return self.__accumulateProfile(installed)

    def __accumulateProfile(self, rpm_header_list):
        """ 
         Accumulates list of installed rpm info 
         @param rpm_header_list: list of rpm headers
         @type rpm_header_list: list
         @return: list of package info dicts
         @rtype: list
        """

        pkg_list = []
        for h in rpm_header_list:
            if h['name'] == "gpg-pubkey":
                #dbMatch includes imported gpg keys as well
                # skip these for now as there isnt compelling 
                # reason for server to know this info
                continue
            info = {
                'name'          : h['name'],
                'version'       : h['version'],
                'release'       : h['release'],
                'epoch'         : h['epoch'] or 0,
                'arch'          : h['arch'],
                'vendor'        : h['vendor'] or None,
            }
            pkg_list.append(info)
        return pkg_list


class GemProfile(object):
    pass

def get_profile(type):
    '''
    Returns an instance of a Profile object
    @param type: profile type
    @type type: string
    Returns an instance of a Profile object
    '''
    if type not in PROFILE_MAP:
        raise InvalidProfileType('Could not find profile for type [%s]', type)
    profile = PROFILE_MAP[type]()
    return profile

PROFILE_MAP = {
    "rpm" : RPMProfile,
}

if __name__ == '__main__':
    p = get_profile("rpm")
    import pprint
    pprint.pprint(p.collect())
