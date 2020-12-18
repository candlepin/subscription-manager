RHSM & Cloud
============

This package contains modules for detecting cloud providers and collecting cloud metadata. These
metadata then can be for example reported in system facts. Currently three main cloud providers
are supported: Amazon Web Services, Microsoft Azure and Google Cloud Platform. If you want to add
support for another cloud provider, then add subclasses of CloudCollector and CloudDetector to
some module in providers sub-package and modify list of supported classes in utils.py 