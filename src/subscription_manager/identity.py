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
import errno
import threading
from typing import Optional, TYPE_CHECKING

from rhsm.certificate import create_from_pem
from rhsm.config import get_config_parser
from subscription_manager.certdirectory import Path

from rhsmlib.services import config
from rhsm.certificate import CertificateException
from rhsm.certificate2 import CertificateLoadingError

if TYPE_CHECKING:
    from rhsm.certificate2 import EntitlementCertificate

conf = config.Config(get_config_parser())
log = logging.getLogger(__name__)


class ConsumerIdentity:
    """Consumer info and certificate information.

    Includes helpers for reading/writing consumer identity certificates
    from disk."""

    PATH = conf["rhsm"]["consumerCertDir"]
    KEY = "key.pem"
    CERT = "cert.pem"

    @staticmethod
    def keypath() -> str:
        return str(Path.join(ConsumerIdentity.PATH, ConsumerIdentity.KEY))

    @staticmethod
    def certpath() -> str:
        return str(Path.join(ConsumerIdentity.PATH, ConsumerIdentity.CERT))

    @classmethod
    def read(cls) -> "ConsumerIdentity":
        with open(cls.keypath()) as key_file:
            key: str = key_file.read()
        with open(cls.certpath()) as cert_file:
            cert: str = cert_file.read()
        return ConsumerIdentity(key, cert)

    @classmethod
    def exists(cls) -> bool:
        return os.path.exists(cls.keypath()) and os.path.exists(cls.certpath())

    @classmethod
    def existsAndValid(cls) -> bool:
        if cls.exists():
            try:
                cls.read()
                return True
            except Exception as e:
                log.warn("possible certificate corruption")
                log.error(e)
        return False

    def __init__(self, keystring, certstring):
        self.key = keystring
        # TODO: bad variables, cert should be the certificate object, x509 is
        # used elsewhere for the rhsm._certificate object of the same name.
        self.cert = certstring
        self.x509: EntitlementCertificate = create_from_pem(certstring)

    def getConsumerId(self) -> str:
        subject: dict = self.x509.subject
        return subject.get("CN")

    def getConsumerName(self) -> str:
        # FIXME Unresolved attribute
        altName = self.x509.alt_name
        # FIXME Do we still need to support 'old' format?
        #       The comment is from 2014, the line below from 2017
        # must account for old format and new
        return altName.replace("DirName:/CN=", "").replace("URI:CN=", "").split(", ")[-1]

    def getSerialNumber(self) -> int:
        return self.x509.serial

    def getConsumerOwner(self) -> Optional[str]:
        """Get the name of the organization of the consumer.

        The value is stored in the 'Subject Name' > 'O (Organization)' field
        of the consumer certificate.
        """
        subject: dict = self.x509.subject
        return subject.get("O")

    # TODO: we're using a Certificate which has it's own write/delete, no idea
    # why this landed in a parallel disjoint class wrapping the actual cert.
    def write(self) -> None:
        from subscription_manager import managerlib

        self.__mkdir()
        with open(self.keypath(), "w") as key_file:
            key_file.write(self.key)
        os.chmod(self.keypath(), managerlib.ID_CERT_PERMS)
        with open(self.certpath(), "w") as cert_file:
            cert_file.write(self.cert)
        os.chmod(self.certpath(), managerlib.ID_CERT_PERMS)

    def delete(self) -> None:
        path: str = self.keypath()
        if os.path.exists(path):
            os.unlink(path)
        path: str = self.certpath()
        if os.path.exists(path):
            os.unlink(path)

    def __mkdir(self) -> None:
        path: str = Path.abs(self.PATH)
        if not os.path.exists(path):
            os.mkdir(path)

    def __str__(self) -> str:
        return 'consumer: name="%s", uuid=%s' % (self.getConsumerName(), self.getConsumerId())


class Identity:
    """Wrapper for sharing consumer identity without constant reloading."""

    def __init__(self):
        self.consumer: Optional[ConsumerIdentity] = None
        self._lock = threading.Lock()
        self._name: Optional[str] = None
        self._uuid: Optional[str] = None
        self._owner: Optional[str] = None
        self._cert_dir_path: str = conf["rhsm"]["consumerCertDir"]
        self.reload()

    def reload(self) -> None:
        """Check for consumer certificate on disk and update our info accordingly."""
        log.debug("Loading consumer info from identity certificates.")
        with self._lock:
            try:
                self.consumer = self._get_consumer_identity()
            # XXX shouldn't catch the global exception here, but that's what
            # existsAndValid did, so this is better.
            except (CertificateException, CertificateLoadingError, IOError) as err:
                self.consumer = None
                err_msg: Exception = err
                msg = "Reload of consumer identity cert %s raised an exception with msg: %s" % (
                    ConsumerIdentity.certpath(),
                    err_msg,
                )
                if isinstance(err, IOError) and err.errno == errno.ENOENT:
                    log.debug(msg)
                else:
                    log.error(msg)

            if self.consumer is not None:
                self._name = self.consumer.getConsumerName()
                self._uuid = self.consumer.getConsumerId()
                self._owner = self.consumer.getConsumerOwner()
                # since Identity gets dep injected, lets look up
                # the cert dir on the active id instead of the global config
                self._cert_dir_path = self.consumer.PATH
            else:
                self._name = None
                self._uuid = None
                self._cert_dir_path = conf["rhsm"]["consumerCertDir"]

    def _get_consumer_identity(self) -> ConsumerIdentity:
        return ConsumerIdentity.read()

    # this name is weird, since Certificate.is_valid actually checks the data
    # and this is a thin wrapper
    def is_valid(self) -> bool:
        return self.uuid is not None

    @property
    def name(self) -> Optional[str]:
        with self._lock:
            _name = self._name
        return _name

    @property
    def uuid(self) -> Optional[str]:
        with self._lock:
            _uuid = self._uuid
        return _uuid

    @property
    def owner(self) -> Optional[str]:
        with self._lock:
            return self._owner

    @property
    def cert_dir_path(self) -> str:
        with self._lock:
            _cert_dir_path = self._cert_dir_path
        return _cert_dir_path

    @staticmethod
    def is_present() -> bool:
        return ConsumerIdentity.exists()

    def __str__(self) -> str:
        return "Consumer Identity name=%s uuid=%s" % (self.name, self.uuid)
