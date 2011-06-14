import unittest

from subscription_manager import logutil


# we don't actually use these by default, they
# just exist for debuging, but I might as well test them
class TestTrace(unittest.TestCase):
    def test_trace_me(self):
        bt = logutil.trace_me()
        # not much to verify here
        assert len(bt) > 0

    def test_trace_me_more(self):
        bt = logutil.trace_me_more()
        assert len(bt) > 0


class TestLogutil(unittest.TestCase):
    def test_get_handler(self):
        logutil._get_handler()

    def test_init_logger(self):
        logutil.init_logger()

    def test_init_logger_for_yum(self):
        logutil.init_logger_for_yum()
