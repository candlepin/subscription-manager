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
    return _certificate.get_signature_algorithms()


def get_public_key_algorithms():
    """
    Get public key algorithms supported by the system.

    Returns a list of OID strings representing available public key algorithms,
    retrieved directly from OpenSSL via the C bindings.
    """
    return _certificate.get_public_key_algorithms()
