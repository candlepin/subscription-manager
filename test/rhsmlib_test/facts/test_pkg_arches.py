import unittest

from rhsmlib.facts import pkg_arches
from mock import patch


class TestSupportedArchesCollector(unittest.TestCase):

    @staticmethod
    def helper_dpkg_no_foreign(*args, **kwargs):
        if args[0][1] == "--print-architecture":
            return "amd64\n".encode("UTF-8")
        return "".encode("UTF-8")

    @staticmethod
    def helper_dpkg_foreign(*args, **kwargs):
        if args[0][1] == "--print-architecture":
            return "amd64\n".encode("UTF-8")
        elif args[0][1] == "--print-foreign-architectures":
            return "i386\n".encode("UTF-8")
        return "".encode("UTF-8")

    @patch("subprocess.check_output")
    def test_single_arch_on_debian(self, MockCheckOutput):
        collector = pkg_arches.SupportedArchesCollector(
            collected_hw_info={
                "distribution.name": "Debian"
            }
        )
        MockCheckOutput.side_effect = self.helper_dpkg_no_foreign
        fact = collector.get_all()
        self.assertEqual(fact["supported_architectures"], "amd64")

    @patch("subprocess.check_output")
    def test_single_arch_on_ubuntu(self, MockCheckOutput):
        collector = pkg_arches.SupportedArchesCollector(
            collected_hw_info={
                "distribution.name": "Ubuntu"
            }
        )
        MockCheckOutput.side_effect = self.helper_dpkg_no_foreign
        fact = collector.get_all()
        self.assertEqual(fact["supported_architectures"], "amd64")

    @patch("subprocess.check_output")
    def test_multi_arch_on_ubuntu(self, MockCheckOutput):
        collector = pkg_arches.SupportedArchesCollector(
            collected_hw_info={
                "distribution.name": "Debian"
            }
        )
        MockCheckOutput.side_effect = self.helper_dpkg_foreign
        fact = collector.get_all()
        self.assertEqual(fact["supported_architectures"], "amd64,i386")

    @patch("subprocess.check_output")
    def test_multi_arch_on_debian(self, MockCheckOutput):
        collector = pkg_arches.SupportedArchesCollector(
            collected_hw_info={
                "distribution.name": "Ubuntu"
            }
        )
        MockCheckOutput.side_effect = self.helper_dpkg_foreign
        fact = collector.get_all()
        self.assertEqual(fact["supported_architectures"], "amd64,i386")

    @patch("subprocess.check_output")
    def test_none_arch_on_redhat(self, MockCheckOutput):
        collector = pkg_arches.SupportedArchesCollector(
            collected_hw_info={
                "distribution.name": "RedHat"
            }
        )
        MockCheckOutput.side_effect = self.helper_dpkg_no_foreign
        fact = collector.get_all()
        self.assertTrue("supported_architectures" not in fact)
