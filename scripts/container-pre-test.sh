#!/bin/bash

# Install system, build and runtime packages
yum install -y \
  gtk3-devel python-ethtool \
  openssl-devel swig intltool

localedef -c -i en_US -f ISO-8859-1 en_US
localedef -c -i en_US -f UTF-8 en_US.UTF-8
localedef -c -i de_DE -f UTF-8 de_DE.UTF-8
localedef -c -i ja_JP -f UTF-8 ja_JP.UTF-8

# Install test packages
python -m pip install -r test-requirements.txt

# Build the project
python setup.py build
python setup.py build_ext --inplace
