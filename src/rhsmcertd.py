#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

import time
from config import initConfig
from certlib import CertLib
from logutil import getLogger


log = getLogger(__name__)


class Daemon:
    
    def __init__(self, delay):
        self.delay = delay
        self.certlib = CertLib()
    
    def run(self):
        while True:
            time.sleep(self.delay)
            self.update()
                
    def update(self):
        log.info('updating')
        try:
            self.certlib.update()
        except Exception, ex:
            log.exception(ex)
        
    
def main():
    cfg = initConfig()
    delay = cfg['certFrequency']
    log.info('started, frequency=%s', delay)
    d = Daemon(delay)
    d.run()
    
if __name__ == '__main__':
    main()



