import logging

from rhsm import _certificate
from rhsm.config import get_config_parser
from rhsm.connection import CryptographicCapabilities

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


def get_crypto_capabilities() -> CryptographicCapabilities:
    """
    Build a CryptographicCapabilities from the certificate_algorithms config value.
    """
    cfg = get_config_parser()

    # Empty arrays indicate prevent scheme negotiation and should result in non-PQC certificates
    key_algorithms = []
    signature_algorithms = []

    certificate_algorithms = cfg.get("rhsm", "certificate_algorithms")
    if certificate_algorithms == "current":
        key_algorithms = get_public_key_algorithms()
        log.debug(f"The list of public key algorithms: {key_algorithms}")
        signature_algorithms = get_signature_algorithms()
        log.debug(f"The list of signature algorithms: {signature_algorithms}")
    elif certificate_algorithms == "legacy":
        log.debug("Using legacy cryptography algorithms for consumer and entitlement certificate")
    else:
        log.warning(
            f"Unknown value for 'rhsm.certificate_algorithms' in rhsm.conf: {certificate_algorithms}."
            " Falling back to legacy cryptographic algorithms."
        )

    return CryptographicCapabilities(
        key_algorithms=key_algorithms,
        signature_algorithms=signature_algorithms,
    )


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
