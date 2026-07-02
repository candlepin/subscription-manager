import logging
import sys
from typing import Tuple, List

from rhsm import _certificate
from rhsm.config import get_config_parser
from subscription_manager.i18n import ugettext as _

"""
This module helps to negotiate PQC with candlepin server.
"""

log = logging.getLogger(__name__)


def get_signature_algorithms():
    """
    Get signature algorithms supported by the system.

    Returns a list of OID strings representing available signature algorithms,
    retrieved directly from OpenSSL via the C bindings.
    """
    try:
        return _certificate.get_signature_algorithms()
    except Exception as e:
        raise RuntimeError("Failed to get list of signature algorithms") from e


def get_public_key_algorithms():
    """
    Get public key algorithms supported by the system.

    Returns a list of OID strings representing available public key algorithms,
    retrieved directly from OpenSSL via the C bindings.
    """
    try:
        return _certificate.get_public_key_algorithms()
    except Exception as e:
        raise RuntimeError("Failed to get list of public key algorithms") from e


def get_crypto_capabilities() -> Tuple[List[str], List[str]]:
    """
    Determine the cryptographic algorithms supported by the system.

    Returns a tuple of (key_algorithms, signature algorithms) indicating the cryptographic
    algorithms supported by the system.

    If `rhsm.certificate_algorithms` is set to `current` in the config, returns populated lists
    of OIDs, enabling scheme negotiation with Candlepin, resulting in PQC certificates.

    If `rhsm.certificate_algorithms` is set to `legacy` in the config, returns empty arrays,
    preventing scheme negotiation in Candlepin, resulting in non-PQC certificates
    """
    cfg = get_config_parser()

    # Empty arrays indicate prevent scheme negotiation and should result in non-PQC certificates
    key_algorithms = []
    signature_algorithms = []

    certificate_algorithms = cfg.get("rhsm", "certificate_algorithms")
    if not cfg.is_value_valid("rhsm", "certificate_algorithms", certificate_algorithms):
        certificate_algorithms = cfg.get_default("rhsm", "certificate_algorithms")
        print(
            _("Using default value '{value}' for this run.").format(value=certificate_algorithms),
            file=sys.stderr,
        )

    if certificate_algorithms == "current":
        key_algorithms = get_public_key_algorithms()
        log.debug(f"The list of public key algorithms: {key_algorithms}")
        signature_algorithms = get_signature_algorithms()
        log.debug(f"The list of signature algorithms: {signature_algorithms}")
    elif certificate_algorithms == "legacy":
        log.debug("Using legacy cryptography algorithms for consumer and entitlement certificate")

    return key_algorithms, signature_algorithms
