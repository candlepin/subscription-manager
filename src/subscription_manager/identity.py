#
# Copyright (c) 2013 Red Hat, Inc.
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

import logging
import os

from rhsm.certificate import create_from_pem, CertificateException
from rhsm.config import initConfig
from subscription_manager.certdirectory import Path

CFG = initConfig()

log = logging.getLogger(__name__)


class IdentityCertCorruptionException(CertificateException):
    """ This exception is meant to be used when there is suspected corruption
        of the ConsumerIdentity. """


class ConsumerIdentity:
    """Consumer info and certificate information.

    Includes helpers for reading/writing consumer identity certificates
    from disk."""

    PATH = CFG.get('rhsm', 'consumerCertDir')
    KEY = 'key.pem'
    CERT = 'cert.pem'

    @staticmethod
    def keypath():
        return str(Path.join(ConsumerIdentity.PATH, ConsumerIdentity.KEY))

    @staticmethod
    def certpath():
        return str(Path.join(ConsumerIdentity.PATH, ConsumerIdentity.CERT))

    @classmethod
    def read(cls):
        f = open(cls.keypath())
        key = f.read()
        f.close()
        f = open(cls.certpath())
        cert = f.read()
        f.close()
        return ConsumerIdentity(key, cert)

    @classmethod
    def exists(cls):
        return (os.path.exists(cls.keypath()) and
                os.path.exists(cls.certpath()))

    @classmethod
    def existsAndValid(cls):
        return cls.exists() and cls.valid()

    @classmethod
    def accessible(cls):
        if not os.access(cls.certpath(), os.R_OK):
            log.warn('Insufficient permissions to access cert file: %s' % cls.certpath())
            return False
        if not os.access(cls.keypath(), os.R_OK):
            log.warn('Insufficient permissions to access key file: %s' % cls.keypath())
            return False
        return True

    @classmethod
    def valid(cls):
        try:
            cls.read()
            return True
        except CertificateException as e:
            log.warn('possible certificate corruption')
            log.error(e)
            # Leave it to the caller to handle the exception
            # so that they have to opportunity to display it nicely
            # to the user (if appropriate)
        except IOError as e:
            log.warn('One of the consumer certificates could not be read')
            log.error(e)
            raise
        # XXX: I do not like catch-all excepts
        except Exception as e:
            log.warn('possible certificate corruption')
            log.error(e)
        return False

    def __init__(self, keystring, certstring):
        self.key = keystring
        # TODO: bad variables, cert should be the certificate object, x509 is
        # used elsewhere for the rhsm._certificate object of the same name.
        self.cert = certstring
        self.x509 = create_from_pem(certstring)

    def getConsumerId(self):
        subject = self.x509.subject
        return subject.get('CN')

    def getConsumerName(self):
        altName = self.x509.alt_name
        # must account for old format and new
        return altName.replace("DirName:/CN=", "").replace("URI:CN=", "")

    def getSerialNumber(self):
        return self.x509.serial

    # TODO: we're using a Certificate which has it's own write/delete, no idea
    # why this landed in a parallel disjoint class wrapping the actual cert.
    def write(self):
        from subscription_manager import managerlib
        self.__mkdir()
        f = open(self.keypath(), 'w')
        f.write(self.key)
        f.close()
        os.chmod(self.keypath(), managerlib.ID_CERT_PERMS)
        f = open(self.certpath(), 'w')
        f.write(self.cert)
        f.close()
        os.chmod(self.certpath(), managerlib.ID_CERT_PERMS)

    def delete(self):
        path = self.keypath()
        if os.path.exists(path):
            os.unlink(path)
        path = self.certpath()
        if os.path.exists(path):
            os.unlink(path)

    def __mkdir(self):
        path = Path.abs(self.PATH)
        if not os.path.exists(path):
            os.mkdir(path)

    def __str__(self):
        return 'consumer: name="%s", uuid=%s' % \
            (self.getConsumerName(),
             self.getConsumerId())


class Identity(object):
    """Wrapper for sharing consumer identity without constant reloading."""
    def __init__(self):
        # This attribute will be raised on access to any attribute that relies
        # on the underlying ConsumerIdentity to exist and be valid and
        # accessible OR to be nonexistent
        self.reload_exception = None
        self._reset()
        self.reload()

    @property
    def consumer(self):
        if self.reload_exception:
            raise self.reload_exception
        return self._consumer

    @consumer.setter
    def consumer(self, value):
        self._consumer = value

    @property
    def name(self):
        if self.reload_exception:
            raise self.reload_exception
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def uuid(self):
        if self.reload_exception:
            raise self.reload_exception
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        self._uuid = value

    @property
    def cert_dir_path(self):
        if self.reload_exception:
            raise self.reload_exception
        return self._cert_dir_path

    @cert_dir_path.setter
    def cert_dir_path(self, value):
        self._cert_dir_path = value

    def reload(self):
        """Check for consumer certificate on disk and update our info accordingly."""
        log.debug("Loading consumer info from identity certificates.")
        self._clear_reload_exception()
        try:
            # uh, weird
            # FIXME: seems weird to wrap this stuff
            if ConsumerIdentity.exists() and ConsumerIdentity.accessible():
                if not ConsumerIdentity.valid():
                    raise IdentityCertCorruptionException()
                self.consumer = self._get_consumer_identity()
                self.name = self.consumer.getConsumerName()
                self.uuid = self.consumer.getConsumerId()
                # since Identity gets dep injected, lets look up
                # the cert dir on the active id instead of the global config
                self.cert_dir_path = self.consumer.PATH
            else:
                self._reset()
        # XXX shouldn't catch the global exception here, but that's what
        # existsAndValid did, so this is better.
        except Exception, e:
            log.debug("Reload of consumer identity cert %s raised an exception with msg: %s",
                      ConsumerIdentity.certpath(), e)
            # Save whatever exception got thrown to raise later when we use
            # one of the attributes of this object that are populated by this
            # method.
            # This is being done to allow exceptions relating to access to the
            # identity certs and such to bubble up and be handled gracefully by
            # users of this object.
            self.reload_exception = e
            self._reset()

    def _reset(self):
        self.consumer = None
        self.name = None
        self.uuid = None
        self.cert_dir_path = CFG.get('rhsm', 'consumerCertDir')

    def _clear_reload_exception(self):
        if self.reload_exception:
            log.debug('Clearing stored reload exception: %s', self.reload_exception)
            self.reload_exception = None

    def _get_consumer_identity(self):
        return ConsumerIdentity.read()

    # this name is weird, since Certificate.is_valid actually checks the data
    # and this is a thin wrapper
    def is_valid(self):
        return self.uuid is not None

    def getConsumerName(self):
        return self.name

    def getConsumerId(self):
        return self.uuid

    # getConsumer is kind of vague, and this is just here to
    # the cert object
    def getConsumerCert(self):
        return self.consumer

    def __str__(self):
        return "Consumer Identity name=%s uuid=%s" % (self.name, self.uuid)
