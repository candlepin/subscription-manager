#!/bin/bash
set -ux

# get to project root
cd ../../../

# Check for GitHub pull request ID and install build if needed.
# This is for the downstream PR jobs.
[ -z "${ghprbPullId+x}" ] || ./systemtest/copr-setup.sh

dnf --setopt install_weak_deps=False install -y \
    podman git-core python3-pip python3-pytest logrotate \
    cairo-gobject-devel gobject-introspection-devel \
    python3-gobject python3-devel

yum -y groupinstall 'Development Tools'

python3 -m venv venv
# shellcheck disable=SC1091
. venv/bin/activate

# Install requirements for integration tests
pip install -r integration-tests/requirements.txt

# configuration for the tests
cat <<EOF > settings.toml
[testing]
candlepin.host = "localhost"
candlepin.port = 8443
candlepin.insecure = true
candlepin.prefix = "/candlepin"
candlepin.username = "duey"
candlepin.password = "password"
candlepin.org = "donaldduck"
candlepin.activation_keys = ["act-key-01","act-key-02"]
candlepin.environment.names = ["env-name-01","env-name-02"]
candlepin.environment.ids =   ["env-id-01","env-id-02"]
EOF


# run local candlepin for testing purpose
./integration-tests/scripts/run-local-candlepin.sh

# create testing data in local candlepin
./integration-tests/scripts/post-activation-keys.sh
./integration-tests/scripts/post-environments.sh

# There is a problem with SELinux in current version of selinux-roles (for rhsm.service)
# it is a temporary fix
setenforce 0

# Run all integration tests. They will use 'testing' environment in configuration
ENV_FOR_DYNACONF=testing pytest --junit-xml=./junit.xml -v integration-tests
retval=$?

# Copy artifacts of integration tests
if [ -d "$TMT_PLAN_DATA" ]; then
  cp ./junit.xml "$TMT_PLAN_DATA/junit.xml"
fi

# Return exit code of integration tests
exit $retval
