
import fixture

from subscription_manager import api

# very rudimentary test of api module. Just
# verifing it imports basically.

class TestApi(fixture.SubManFixture):
    def test(self):
        self.assertTrue(hasattr(api, 'base_plugin'))
        self.assertTrue(hasattr(api, 'ActionReport'))
