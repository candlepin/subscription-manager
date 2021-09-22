# Copyright (c) 2010 Red Hat, Inc.
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

from mock import Mock, NonCallableMock
from datetime import datetime

from .fixture import SubManFixture
from subscription_manager.validity import ValidProductDateRangeCalculator
from rhsm import ourjson as json
import subscription_manager.injection as inj

from rhsm.certificate import GMT

# Sample installed product status from the server. Ignoring the
# rest of the consumer details for now, this is all we will use
# when checking product validity.
INST_PROD_STATUS = """
{
  "installedProducts" : [ {
    "created" : "2013-02-28T21:03:38.729+0000",
    "updated" : "2013-02-28T21:03:38.729+0000",
    "id" : "402881983d17fabf013d229e16e90ba7",
    "productId" : "37060",
    "productName" : "Awesome OS Server Bits",
    "version" : "6.1",
    "arch" : "ALL",
    "status" : "green",
    "startDate" : "2013-02-26T00:00:00.000+0000",
    "endDate" : "2014-02-26T00:00:00.000+0000"
  }, {
    "created" : "2013-02-28T21:03:38.729+0000",
    "updated" : "2013-02-28T21:03:38.729+0000",
    "id" : "402881983d17fabf013d229e16e90ba8",
    "productId" : "69",
    "productName" : "Red Hat Enterprise Linux Server",
    "version" : null,
    "arch" : null,
    "status" : null,
    "startDate" : null,
    "endDate" : null
  }, {
    "created" : "2013-02-28T21:03:38.729+0000",
    "updated" : "2013-02-28T21:03:38.729+0000",
    "id" : "402881983d17fabf013d229e16e90ba9",
    "productId" : "100000000000002",
    "productName" : "Awesome OS for x86_64 Bits",
    "version" : "3.11",
    "arch" : "x86_64",
    "status" : "green",
    "startDate" : "2013-02-26T00:00:00.000+0000",
    "endDate" : "2014-02-26T00:00:00.000+0000"
  } ]
}
"""

INST_PID_1 = '37060'
INST_PID_2 = '100000000000002'
INST_PID_3 = '69'


class ValidProductDateRangeCalculatorTests(SubManFixture):

    def setUp(self):
        SubManFixture.setUp(self)
        self.status = json.loads(INST_PROD_STATUS)['installedProducts']
        self.prod_status_cache = NonCallableMock()
        self.prod_status_cache.load_status = Mock(return_value=self.status)
        inj.provide(inj.PROD_STATUS_CACHE, self.prod_status_cache)
        self.calculator = ValidProductDateRangeCalculator(None)

    # If client asks for product status for something server doesn't
    # know is installed, this is very weird, but we will log and handle
    # gracefully:
    def test_installed_product_mismatch(self):
        self.assertTrue(self.calculator.calculate('NOTTHERE') is None)

    # Very old servers may not expose product date ranges:
    def test_missing_installed_status(self):
        for prod in self.status:
            prod.pop('startDate')
            prod.pop('endDate')
        for pid in (INST_PID_1, INST_PID_2, INST_PID_3):
            self.assertTrue(self.calculator.calculate(pid) is None)

    def test_product_with_status(self):
        # "startDate" : "2013-02-26T00:00:00.000+0000",
        # "endDate" : "2014-02-26T00:00:00.000+0000"
        date_range = self.calculator.calculate(INST_PID_1)
        self.assertEqual(datetime(2013, 2, 26, 0, 0, 0, 0, GMT()), date_range.begin())
        self.assertEqual(datetime(2014, 2, 26, 0, 0, 0, 0, GMT()), date_range.end())

    def test_product_without_status(self):
        self.assertTrue(self.calculator.calculate(INST_PID_3) is None)

    def test_unregistered(self):
        id_mock = NonCallableMock()
        id_mock.is_valid.return_value = False
        inj.provide(inj.IDENTITY, id_mock)
        self.calculator = ValidProductDateRangeCalculator(None)
        for pid in (INST_PID_1, INST_PID_2, INST_PID_3):
            self.assertTrue(self.calculator.calculate(pid) is None)
