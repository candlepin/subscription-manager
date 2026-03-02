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
        if line.startswith("IDs: {") and not legacy:
            oid = line.split("{")[1].split(",")[0]
            algorithms.append(oid.strip())
    return algorithms


def __smoke_test__():
    """
    Smoke testing of get_public_key_algorithms()
    """
    algorithms = get_public_key_algorithms()
    print("Supported public key algorithms:")
    for algorithm in algorithms:
        print(f"- {algorithm}")


if __name__ == "__main__":
    __smoke_test__()
