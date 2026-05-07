from rhsm import _certificate

"""
This is POC of new functionality of subscription-manager. This module helps to negotiate
PQC with candlepin server.
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


def get_pub_key_and_sign_algorithms():
    """
    Returns a list containing supported public key and signature algorithms.
    """
    pub_key_algorithms = get_public_key_algorithms()
    sig_algorithms = get_signature_algorithms()
    all_algorithms = set(pub_key_algorithms).union(set(sig_algorithms))
    return list(all_algorithms)


def __smoke_test__():
    """
    Smoke testing of get_public_key_algorithms()
    """
    pub_key_algorithms = get_public_key_algorithms()
    sig_algorithms = get_signature_algorithms()
    print("Supported public key & signature algorithms:")
    for algorithm in pub_key_algorithms:
        if algorithm in sig_algorithms:
            print(f"- {algorithm} (sig+pub)")
        else:
            print(f"- {algorithm} (pub only)")
    for algorithm in sig_algorithms:
        if algorithm not in pub_key_algorithms:
            print(f"- {algorithm} (sig only)")


if __name__ == "__main__":
    __smoke_test__()
