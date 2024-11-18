#!/bin/bash
set -ux

# get to project root
cd ../../../

# Check for GitHub pull request ID and install build if needed.
# This is for the downstream PR jobs.
[ -z "${ghprbPullId+x}" ] || ./systemtest/copr-setup.sh

dnf --setopt install_weak_deps=False install -y \
  podman git-core python3-pip python3-pytest logrotate

python3 -m venv venv
# shellcheck disable=SC1091
. venv/bin/activate

# Install requirements for integration tests
pip install -r integration-tests/requirements.txt

# Run all integration tests
pytest --junit-xml=./junit.xml -v integration-tests
retval=$?

# Copy artifacts of integration tests
if [ -d "$TMT_PLAN_DATA" ]; then
  cp ./junit.xml "$TMT_PLAN_DATA/junit.xml"
fi

# Return exit code of integration tests
exit $retval
