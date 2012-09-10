
import mock

# Simple test fixture that sets up some widely used mocks


def setUp():
    # mock  ClassicCheck to false, tests can re mock if need be.
    # This avoids reading the file off the filesystem
    rhn_check_patcher = mock.patch('subscription_manager.classic_check.ClassicCheck')
    rhn_check_mock = rhn_check_patcher.start()
    rhn_check_mock_instance = rhn_check_mock.return_value
    rhn_check_mock_instance.is_registered_with_classic.return_value = False
