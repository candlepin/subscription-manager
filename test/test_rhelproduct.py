
import stubs

from subscription_manager import rhelproduct

from fixture import SubManFixture


# matches:
#  rhel-6
# not matches
#  rhel-6-server-highavailibity
#  rhel-6-computenode-hpn
#  rhel-6-hpn
#  rhel-6-server-resilientstorage
#  rhel-6-resilientstorage
class TestRHELProductMatcher(SubManFixture):

    matches = ["rhel-6,rhel-6-client",
               "rhel-6,rhel-6-client",
               "rhel-6,rhel-6-computenode",
               "rhel-6,rhel-6-server",
               "rhel-6,rhel-6-ibm-power",
               "rhel-6,rhel-6-ibm-system-z",
               "rhel-6,rhel-6-server",
               "rhel-6,rhel-6-workstation",
               "rhel-6,rhel-6-workstation",
               "rhel-11",
               "rhel-6,rhel-6-someotherthing",
               "rhel-11,rhel-11-something"]

    not_matches = ["rhel-5-server-scalablefilesystem,rhel-5-scalablefilesystem",
                   "rhel-5-server-clusterstorage,rhel-5-clusterstorage",
                   "rhel-6-server-highavailibity",
                   "rhel-6-server-loadbalancer,rhel-6-loadbalancer",
                   "rhel-6-ibm-system-z",
                   "rhel-somethingelse",
                   "rhel",
                   "rhel-rhel-rhelly-rhel",
                   "rhel-",
                   "rhev-3",
                   "what-is-this-rhel-6",
                   "not-rhel-6",
                   "stillnotrhel-6",
                   "rhel-6-rhel-6",
                   "el-6",
                   "rhel-6.1",
                   "rhel-11-but-this-rhel-goes-to-11",
                   "rhel-11.11",
                   "fedora-20",
                   "awsomeos-11",
                   "6"]

    def test_matches(self):
        for tag in self.matches:
            self._assert_is_rhel(tag)

    def test_not_matches(self):
        for tag in self.not_matches:
            self._assert_is_not_rhel(tag)

    def _assert_is_rhel(self, tags):
        matcher = self._build_matcher(tags)
        is_rhel = matcher.is_rhel()
        if not is_rhel:
            self.fail("RHELProductMatcher fail: %s is a rhel product tag but matcher failed" % tags)

    def _assert_is_not_rhel(self, tags):
        matcher = self._build_matcher(tags)
        is_rhel = matcher.is_rhel()
        if is_rhel:
            self.fail("RHELProductMatcher fail: %s is NOT a rhel product tag but matcher did not fail" % tags)

    def _build_matcher(self, tags):
        # NOTE:  Matcher only looks at tags atm
        product = stubs.StubProduct("69", "Red Hat Enterprise Linux Server",
                                    version="6.2",
                                    provided_tags=tags)

        matcher = rhelproduct.RHELProductMatcher(product)
        return matcher
