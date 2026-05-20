from rhsm import _certificate

"""
This module helps to negotiate PQC with candlepin server.
"""


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
