#!/usr/bin/bash -eux
dnf install -y dnf-plugins-core

# Determine the repo needed from copr
source /etc/os-release

if [ "$ID" == "centos" ]; then
  ID='centos-stream'
fi
VERSION_MAJOR=$(echo "${VERSION_ID}" | cut -d '.' -f 1)
COPR_REPO="${ID}-${VERSION_MAJOR}-$(uname -m)"

# Install subscription-manager from COPR repository
dnf remove -y --noautoremove subscription-manager
dnf copr -y enable packit/candlepin-subscription-manager-"${ghprbPullId}" "${COPR_REPO}"
dnf install -y subscription-manager --disablerepo=* --enablerepo=*subscription-manager*
