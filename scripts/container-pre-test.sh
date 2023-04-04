#!/bin/bash

# Install essential packages
dnf --setopt install_weak_deps=False install -y \
  dnf-plugins-core git gcc cmake python3 python3-devel python3-pip

source /etc/os-release
# These repositories are required for the 'libdnf-devel' package.
# Fedora has it available out of the box.
# RHEL needs it to be enabled via 'subscription-manager repos'.
if [[ $ID == "centos" && $VERSION == "8" ]]; then
    dnf config-manager --enable powertools
fi
if [[ $ID == "centos" && $VERSION == "9" ]]; then
    dnf config-manager --enable crb
fi

# Install system, build and runtime packages
dnf --setopt install_weak_deps=False install -y \
  intltool dbus-daemon dbus-devel \
  python3-setuptools \
  openssl-devel glib2-devel libdnf-devel \
  python3-rpm python3-librepo python3-gobject python3-gobject python3-dbus \
  python3-dateutil python3-requests python3-iniparse python3-ethtool \
  glibc-langpack-en glibc-langpack-de glibc-langpack-ja

# Install branch specific packages
dnf --setopt instal_weak_deps=False install -y \
  gtk3-devel

# Install test packages
python3 -m pip install --upgrade pip wheel
python3 -m pip install -r test-requirements.txt

# Build the project
python3 setup.py build
python3 setup.py build_ext --inplace
