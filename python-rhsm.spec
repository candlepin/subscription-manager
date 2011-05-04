# If on Fedora 12 or RHEL 5 or earlier, we need to define these:
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif


Name: python-rhsm
Version: 0.95.5.4
Release: 1%{?dist}

Summary: A Python library to communicate with a Red Hat Unified Entitlement Platform
Group: Development/Libraries
License: GPLv2
# How to create the source tarball:
#
# git clone git://git.fedorahosted.org/git/candlepin.git/
# cd client/python-rhsm
# tito build --tag python-rhsm-%{name}-%{version}-%{release} --tgz
Source0: %{name}-%{version}.tar.gz
URL: http://fedorahosted.org/candlepin
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires: m2crypto
Requires: python-simplejson
Requires: python-iniparse
BuildArch: noarch

BuildRequires: python2-devel
BuildRequires: python-setuptools


%description 
A small library for communicating with the REST interface of a Red Hat Unified
Entitlement Platform. This interface is used for the management of system
entitlements, certificates, and access to content.

%prep
%setup -q -n python-rhsm-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc README

%dir %{python_sitelib}/rhsm

%{python_sitelib}/rhsm/*
%{python_sitelib}/rhsm-*.egg-info

%changelog
* Wed May 04 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 702078: firstboot fails after initial install on HP DL360 Gen8
  (cduryee@redhat.com)
- 694870: workaround a bug in httpslib.ProxyHttpsConnection
  (alikins@redhat.com)
- 691788: Fix bad check for missing order info. (dgoodwin@redhat.com)

* Wed Mar 30 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 668613: Add python-rhsm package

* Wed Mar 30 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 668613: Add python-rhsm package
