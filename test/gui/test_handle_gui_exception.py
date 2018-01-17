from __future__ import print_function, division, absolute_import

try:
    import unittest2 as unittest
except ImportError:
    import unittest
from mock import patch

import socket
from rhsm.https import ssl

from subscription_manager.gui import utils
from test.fixture import FakeException, FakeLogger

import rhsm.connection as connection
from nose.plugins.attrib import attr


class FakeErrorWindow(object):
    def __init__(self, msg, parent=None):
        self.msg = msg


@attr('gui')
@patch('subscription_manager.gui.utils.log', FakeLogger())
@patch('subscription_manager.gui.utils.show_error_window', FakeErrorWindow)
class HandleGuiExceptionTests(unittest.TestCase):

    # we are going with "hge" for handle_gui_exception

    def setUp(self):
        self.msg = "some thing to log home about"
        self.formatted_msg = "some thing else like: %s"
        self.msg_with_url = "https://www.example.com"
        self.msg_with_url_and_formatting = "https://www.example.com %s"
        self.msg_with_markup = """<span foreground="blue" size="100">Blue text</span> is <i>cool</i>!"""

    def test_hge(self):
        e = FakeException()
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(e, self.msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_log_msg_none(self):
        e = FakeException()
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(e, self.msg, None, log_msg=None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_socket_error(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(socket.error(), self.msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_ssl_error(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(ssl.SSLError(), self.msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_network_exception(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(connection.NetworkException(1337),
                                   self.msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_remote_server_exception(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(connection.RemoteServerException(1984),
                                   self.msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_restlib_exception_unformatted_msg(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(connection.RestlibException(421, "whatever"),
                                   self.msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_restlib_exception_unformatted_msg_format_msg_false(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(connection.RestlibException(421, "whatever"),
                                   self.msg, None,
                                   format_msg=False)

    def test_hge_restlib_exception_formated_msg(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(connection.RestlibException(409, "very clean"),
                                   self.formatted_msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_restlib_exception_url_msg(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(connection.RestlibException(404, "page not found"),
                                   self.msg_with_url, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    # if we handle this okay, we can probably remove the format_msg tests
    def test_hge_restlib_exception_url_msg_with_formatting_format_msg_false(self):
        utils.handle_gui_exception(connection.RestlibException(404, "page not found"),
                                   self.msg_with_url_and_formatting, None,
                                   format_msg=False)

    def test_hge_restlib_exception_url_msg_500(self):
        utils.handle_gui_exception(connection.RestlibException(500, "internal server error"),
                                   self.msg_with_url, None, format_msg=True)

    def test_hge_bad_certificate(self):
        utils.handle_gui_exception(connection.BadCertificateException("/road/to/nowhere"),
                                   self.msg, None)

    def test_hge_fake_exception_url_msg(self):
        utils.handle_gui_exception(FakeException(msg="hey https://www.exmaple.com"),
                                   self.msg, None)

    def test_hge_fake_exception_no_url_msg(self):
        utils.handle_gui_exception(FakeException(msg="< what?>"),
                                   self.msg, None)

    def test_hge_fake_exception_formatted_msg(self):
        utils.handle_gui_exception(FakeException(msg="something"),
                                   self.formatted_msg, None)

    def test_hge_fake_exception_formatted_msg_format_msg_false(self):
        utils.handle_gui_exception(FakeException(msg="whatever"),
                                   self.formatted_msg, None,
                                   format_msg=False)

    def test_hge_fake_exception_fomatted_log_msg(self):
        utils.handle_gui_exception(FakeException(msg="bieber"),
                                   self.formatted_msg, None,
                                   log_msg=self.formatted_msg)
