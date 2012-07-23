import unittest
import socket
from M2Crypto import SSL

import rhsm_display
rhsm_display.set_display()

from subscription_manager.gui import utils
import rhsm.connection as connection


class FakeLogger:
    def __init__(self):
        self.expected_msg = ""
        self.msg = None
        self.logged_exception = None

    def debug(self, buf):
        self.msg = buf

    def error(self, buf):
        self.msg = buf

    def exception(self, e):
        self.logged_exception = e

    def set_expected_msg(self, msg):
        self.expected_msg = msg


class FakeErrorWindow:
    def __init__(self, msg, parent=None):
        self.msg = msg


class FakeException(Exception):
    def __init__(self, msg=None, cert_path=None):
        self.msg = msg
        self.cert_path = cert_path


class HandleGuiExceptionTests(unittest.TestCase):

    # we are going with "hge" for handle_gui_exception

    def setUp(self):
        self.msg = "some thing to log home about"
        self.formatted_msg = "some thing else like: %s"
        self.msg_with_url = "https://www.example.com"
        self.msg_with_url_and_formatting = "https://www.example.com %s"
        self.msg_with_markup = """<span foreground="blue" size="100">Blue text</span> is <i>cool</i>!"""
        utils.log = FakeLogger()
        utils.errorWindow = FakeErrorWindow
        # set a mock logger

    def test_hge(self):
        e = FakeException()
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(e, self.msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_log_msg_none(self):
        e = FakeException()
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(e, self.msg, None, logMsg=None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_socket_error(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(socket.error(), self.msg, None)
        self.assertEqual(utils.log.expected_msg, self.msg)

    def test_hge_ssl_error(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(SSL.SSLError(), self.msg, None)
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

    def test_hge_restlib_exception_unformatted_msg_formatMsg_false(self):
        utils.log.set_expected_msg(self.msg)
        utils.handle_gui_exception(connection.RestlibException(421, "whatever"),
                                   self.msg, None,
                                   formatMsg=False)

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

    # if we handle this okay, we can probably remove the formatMsg tests
    def test_hge_restlib_exception_url_msg_with_formatting_formatMsg_false(self):
        utils.handle_gui_exception(connection.RestlibException(404, "page not found"),
                                   self.msg_with_url_and_formatting, None,
                                   formatMsg=False)

    def test_hge_restlib_exception_url_msg_500(self):
        utils.handle_gui_exception(connection.RestlibException(500, "internal server error"),
                                   self.msg_with_url, None, formatMsg=True)

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

    def test_hge_fake_exception_formatted_msg_formatMsg_false(self):
        utils.handle_gui_exception(FakeException(msg="whatever"),
                                   self.formatted_msg, None,
                                   formatMsg=False)

    def test_hge_fake_exception_fomatted_log_msg(self):
        utils.handle_gui_exception(FakeException(msg="bieber"),
                                   self.formatted_msg, None,
                                   logMsg=self.formatted_msg)
