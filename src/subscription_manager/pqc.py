import re
import subprocess

"""
This is POC of new functionality of subscription-manager. This module helps to negotiate
PQC with candlepin server.
"""


def run(cmd, shell=True, cwd=None):
    """
    Run a command.
    Return exitcode, stdout, stderr
    """

    proc = subprocess.Popen(
        cmd,
        shell=shell,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        errors="surrogateescape",
    )

    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr


# FIXME: We should get the list of OIDs from openssl library in the certificate.c. Parsing
#        output of "openssl list -public-key-algorithms" is something we should avoid.


def get_signature_algorithms():
    """
    Get signature algorithms supported by the system.
    """
    cmd = "openssl list -signature-algorithms"
    return_code, stdout, stderr = run(cmd)
    if return_code != 0:
        raise RuntimeError(f"Failed to get public key algorithms: {stderr}")
    lines = stdout.strip().splitlines()
    algorithms = []
    for i, line in enumerate(lines):
        line = line.strip()
        # Parse line like this:
        # { 2.16.840.1.101.3.4.3.31, id-slh-dsa-shake-256f, SLH-DSA-SHAKE-256f } @ default
        match = re.search(r"\{\s*([^,]+)", line)
        if match:
            algorithms.append(match.group(1).strip())
    return algorithms


def get_public_key_algorithms():
    """
    Get public key algorithms supported by the system.
    """
    cmd = "openssl list -public-key-algorithms"
    return_code, stdout, stderr = run(cmd)
    if return_code != 0:
        raise RuntimeError(f"Failed to get public key algorithms: {stderr}")
    lines = stdout.strip().splitlines()
    algorithms = []
    legacy = False
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("Legacy:"):
            legacy = True
            continue
        if line.startswith("Provided:"):
            legacy = False
            continue
        # Parse line like this:
        # IDs: { 2.16.840.1.101.3.4.3.21, id-slh-dsa-sha2-128f, SLH-DSA-SHA2-128f } @ default
        if not legacy:
            match = re.search(r"IDs: \{\s*([^,]+)", line)
            if match:
                algorithms.append(match.group(1).strip())
    return algorithms


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
