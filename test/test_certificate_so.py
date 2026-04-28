# Copyright (c) 2026 Red Hat, Inc.
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

import unittest
import rhsm._certificate


class TestCertificateSO(unittest.TestCase):

    def helper_test_list_of_algorithms(self, algorithms):
        """
        The list of algorithms should contain OIDs of supported algorithms.
        """
        self.assertIsInstance(algorithms, list)
        self.assertGreater(len(algorithms), 0)
        for algo in algorithms:
            self.assertTrue(isinstance(algo, str))
            # The algorithm should be represented as OID
            self.assertRegex(algo, r"^[0-9]+(\.[0-9]+)+$")

    def test_get_public_key_algorithms(self):
        """
        Test that the public key algorithms are returned.
        The list should contain OIDs of supported algorithms.
        The list of OIDs could be different on different systems.
        """
        pub_key_algos = rhsm._certificate.get_public_key_algorithms()
        self.helper_test_list_of_algorithms(pub_key_algos)

    def test_get_signature_algorithms(self):
        """
        Test that the signature algorithms are returned.
        The list should contain OIDs of supported algorithms.
        The list of OIDs could be different on different systems.
        """
        signature_algos = rhsm._certificate.get_signature_algorithms()
        self.helper_test_list_of_algorithms(signature_algos)
