# Stubs interface file for rhsm._certificate CPython module written in C. The C code is
# available at ./src/certificate.c. If you are editing the ./src/certificate.c file, you
# should also edit this file to be able to provide better type hinting in IDEs.

# TODO: Extend stubs of classes to provide better type hinting.

class X509: ...
class PrivateKey: ...
class OpenSSLCertificateLoadingError: ...

def get_public_key_algorithms(*args, **kwargs) -> list:
    """return a list of public key algorithms"""

def get_signature_algorithms(*args, **kwargs) -> list:
    """return a list of signature algorithms"""

def load(*args, **kwargs) -> None:
    """load a certificate from a file"""

def load_private_key(*args, **kwargs) -> None:
    """load a private key from a file"""
