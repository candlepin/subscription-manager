# If on Fedora 12 or RHEL 5 or earlier, we need to define these:
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif


Name: python-rhsm
Version: 0.99.1
Release: 1%{?dist}

Summary: A Python library to communicate with a Red Hat Unified Entitlement Platform
Group: Development/Libraries
License: GPLv2
# How to create the source tarball:
#
# git clone git://git.fedorahosted.org/git/python-rhsm.git/
# cd client/python-rhsm
# tito build --tag python-rhsm-%{version}-%{release} --tgz
Source0: %{name}-%{version}.tar.gz
URL: http://fedorahosted.org/candlepin
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires: m2crypto
Requires: python-simplejson
Requires: python-iniparse
BuildArch: noarch

BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires:  rpm-python

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
mkdir -p %{buildroot}%{_sysconfdir}/rhsm/ca
install etc-conf/ca/*.pem %{buildroot}%{_sysconfdir}/rhsm/ca

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc README

%dir %{python_sitelib}/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm/ca

%{python_sitelib}/rhsm/*
%{python_sitelib}/rhsm-*.egg-info
%attr(640,root,root) %{_sysconfdir}/rhsm/ca/*.pem

%changelog
* Mon Dec 12 2011 William Poteat <wpoteat@redhat.com> 0.98.7-1
- 766895: Added hypervisorCheckIn call to allow sending a mapping of host/guest ids for
  creation/update. (mstead@redhat.com)

* Wed Dec 07 2011 William Poteat <wpoteat@redhat.com> 0.98.6-1

* Tue Dec 06 2011 William Poteat <wpoteat@redhat.com> 0.98.5-1
- 
+- 754366: workaround a bug in httpslib.ProxyHttpsConnection
+  (alikins@redhat.com)

* Tue Dec 06 2011 William Poteat <wpoteat@redhat.com> 0.98.4-1
- 754366: workaround a bug in httpslib.ProxyHttpsConnection
  (alikins@redhat.com)

* Thu Nov 17 2011 William Poteat <wpoteat@redhat.com> 0.98.3-1
- 752854: Fixing error in iniparser around unpacking of a dictionary for
  default values. (awood@redhat.com)
- 708362: remove entitlement keys on delete as well (alikins@redhat.com)
- 734114: registering with --org="foo bar" throws a NetworkException instead of
  a RestlibException (awood@redhat.com)

* Fri Oct 28 2011 William Poteat <wpoteat@redhat.com> 0.98.2-1
- 749853: backport new python-rhsm API calls present in 6.2 for 5.8
  (cduryee@redhat.com)
- rev python-rhsm version to match sub-mgr (cduryee@redhat.com)
- point master to rhel5 builder (cduryee@redhat.com)
- fix python syntax for older versions (jbowes@redhat.com)
- Fix yum repo location for EL6. (dgoodwin@redhat.com)

* Mon Oct 17 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.97.1-1
- 746241: UEPConnection.updateConsumer now passes empty list in POST request
  (mstead@redhat.com)
- 737935: overcome 255 char limit in uuid list (cduryee@redhat.com)
* Tue Sep 13 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.12-1
- Add makefile and targets for coverage and "stylish" checks
  (alikins@redhat.com)
- Add tests for config parsing (cduryee@redhat.com)
- 736166: move certs from subscription-manager to python-rhsm
  (cduryee@redhat.com)

* Wed Sep 07 2011 James Bowes <jbowes@redhat.com> 0.96.11-1
- add future date bind (jesusr@redhat.com)
- 735226: allow Keys to validate themselves (bkearney@redhat.com)
- Add getVirtOnly() (cduryee@redhat.com)

* Wed Aug 24 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.10-1
- Submit a Content-Length when body of request is empty. (dgoodwin@redhat.com)
- Support installed products when registering. (dgoodwin@redhat.com)
- Add ability to update a consumer's installed products list.
  (dgoodwin@redhat.com)
- Support for new bind method (cduryee@redhat.com)

* Wed Aug 17 2011 James Bowes <jbowes@redhat.com> 0.96.9-1
- self.sanitize, and add support for quote_plus. (cduryee@redhat.com)
- Enhance the insecure mode to not do peer checks. (bkearney@redhat.com)
- Wrap urllib.quote in a helper method to cast int to str as needed.
  (cduryee@redhat.com)
- 728266: Unsubscribe from subscription manager GUI is broken
  (cduryee@redhat.com)
- Remove quantity for bind by product. (dgoodwin@redhat.com)
* Wed Aug 03 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.8-1
- 719378: Encode whitespace in urls (bkearney@redhat.com)
- Change package profile upload url. (dgoodwin@redhat.com)

* Wed Jul 13 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.7-1
- Logging cleanup. (dgoodwin@redhat.com)
- Remove unused add_ssl_certs method. (dgoodwin@redhat.com)
- Load supported resources when UEPConnection is instantiated.
  (dgoodwin@redhat.com)
- Send package profile. (dgoodwin@redhat.com)
- Allow testing if package profiles equal one another. (dgoodwin@redhat.com)
- Support creating package profile from a file descriptor.
  (dgoodwin@redhat.com)
- Allow the attributes to be None for username and password in consumer
  selction. (bkearney@redhat.com)
- Add a Package object. (dgoodwin@redhat.com)

* Wed Jul 06 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.6-1
- Add support for new Katello error responses. (dgoodwin@redhat.com)
- Log the response when there's an issue parsing error JSON.
  (dgoodwin@redhat.com)
- Add support for registration to Katello environments. (dgoodwin@redhat.com)
- Don't send an http body if we don't have one. (jbowes@redhat.com)
- Add call to list environments. (dgoodwin@redhat.com)
- Do not load CA certs if in insecure mode. (dgoodwin@redhat.com)
- Cache supported resources after establishing connection.
  (dgoodwin@redhat.com)

* Fri Jun 24 2011 Devan Goodwin <dgoodwin@redhat.com> 0.96.5-1
- Fix backward compatability with old use of getPoolsList.
  (dgoodwin@redhat.com)
- Remove one built in type issue. (bkearney@redhat.com)
- Removed unused Bundle class (alikins@redhat.com)
- quantity for subscription (wottop@dhcp231-152.rdu.redhat.com)
- Add the activation key call, and remove subscription tokens
  (bkearney@redhat.com)
- Improve the doco, referencing the candlepin site. (bkearney@redhat.com)
- Improve the defualt values for the config (bkearney@redhat.com)
- Fix bug with owner specification during registration. (dgoodwin@redhat.com)

* Wed Jun 08 2011 Bryan Kearney <bkearney@redhat.com> 0.96.4-1
- Adding profile module and updating spec (pkilambi@redhat.com)
- Added stacking Id to the certificate (wottop@dhcp231-152.rdu.redhat.com)
- Changed call to CP for owner list (wottop@dhcp231-152.rdu.redhat.com)
- added getOwners function for use with 'list --owners'
  (wottop@dhcp231-152.rdu.redhat.com)
- change (wottop@dhcp231-152.rdu.redhat.com)
- Added the owner entered in the cli to the post for register
  (wottop@dhcp231-152.rdu.redhat.com)
- altered pool query to use both owner and consumer
  (wottop@dhcp231-152.rdu.redhat.com)
- Added getOwner(consumerid) function (wottop@dhcp231-152.rdu.redhat.com)

* Wed May 11 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.3-1
- 700601: Don't set the Accept-Language if we don't have a valid locale
  (alikins@redhat.com)
- 692210: remove a non critical warning message that is spamming the logs
  (alikins@redhat.com)
- 691788: Fix bad check for missing order info. (dgoodwin@redhat.com)
- Add a version of get_datetime from M2Crypto since it isnt avail on RHEL 5.7
  (alikins@redhat.com)
- Use older strptime call format (cduryee@redhat.com)
- 683550: fix parsing empty cert extensions (jbowes@redhat.com)
- Add support for content tagging. (dgoodwin@redhat.com)
- Use tlsv1 instead of sslv3, for fips compliance (cduryee@redhat.com)

* Mon Feb 14 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.2-1
- Setup configuration for Fedora git builds. (dgoodwin@rm-rf.ca)

* Fri Feb 04 2011 Devan Goodwin <dgoodwin@redhat.com> 0.96.1-1
- 674078: send a full iso 8601 timestamp for activeOn pools query
  (jbowes@repl.ca)

* Tue Feb 01 2011 Devan Goodwin <dgoodwin@redhat.com> 0.95.2-1
- Add content metadata expire to certificate class. (dgoodwin@redhat.com)

* Fri Jan 28 2011 Chris Duryee (beav) <cduryee@redhat.com>
- Add new extensions to order (jbowes@redhat.com)
- remove shebang from certificate.py for rpmlint (jbowes@redhat.com)
- Adding activateMachine to connection api. (jharris@redhat.com)
- 668814: break out 404 and 500s into a different error (cduryee@redhat.com)
- Initialized to use tito. (jbowes@redhat.com)
- bump version (jbowes@redhat.com)

* Wed Jan 12 2011 jesus m. rodriguez <jesusr@redhat.com> 0.94.13-1
- 667829: handle proxy config options being absent from rhsm.conf (alikins@redhat.com)

* Fri Jan 07 2011 Devan Goodwin <dgoodwin@redhat.com> 0.94.12-1
- Related: #668006
- Remove a missed translation. (dgoodwin@redhat.com)
- Fix logger warning messages. (dgoodwin@redhat.com)


* Tue Dec 21 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.10-1
- Related: #661863
- Add certificate parsing library. (dgoodwin@redhat.com)
- Fix build on F12/RHEL5 and earlier. (dgoodwin@redhat.com)

* Fri Dec 17 2010 jesus m. rodriguez <jesusr@redhat.com> 0.94.9-1
- add comment on how to generate source tarball (jesusr@redhat.com)

* Fri Dec 17 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.8-1
- Adding GPLv2 license file. (dgoodwin@redhat.com)

* Fri Dec 17 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.7-1
- Related: #661863
- Add buildrequires for python-setuptools.

* Thu Dec 16 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.4-1
- Add python-rhsm tito.props. (dgoodwin@redhat.com)

* Thu Dec 16 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.3-1
- Refactor logging. (dgoodwin@redhat.com)
- Add a small README. (dgoodwin@redhat.com)

* Tue Dec 14 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.2-1
- Remove I18N code. (dgoodwin@redhat.com)
- Spec cleanup. (dgoodwin@redhat.com)
- Cleaning out unused log parsing functions (jharris@redhat.com)
- More tolerant with no rhsm.conf in place. (dgoodwin@redhat.com)
- Switch to python-iniparse. (alikins@redhat.com)

* Fri Dec 10 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.1-1
- Initial package tagging.

