# If on Fedora 12 or RHEL 5 or earlier, we need to define these:
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

# Use python-simplejson on RHEL 5 as there is no json module in Python 2.4.
# On RHEL 6, we'll use it if it's installed (see ourjson.py).
# simplejson is not available in RHEL 7 at all.
%global use_simplejson (0%{?rhel} && 0%{?rhel} == 5)

# on non-EOL Fedora and RHEL 7, let's not use m2crypto
%global use_m2crypto (0%{?fedora} < 23 && 0%{?rhel} < 7)

%global _hardened_build 1
%{!?__global_ldflags: %global __global_ldflags -Wl,-z,relro -Wl,-z,now}

Name: python-rhsm
Version: 1.19.10
Release: 1%{?dist}

Summary: A Python library to communicate with a Red Hat Unified Entitlement Platform
Group: Development/Libraries
License: GPLv2
# How to create the source tarball:
#
# git clone git://git.fedorahosted.org/git/python-rhsm.git/
# cd client/python-rhsm
# tito build --tag python-rhsm-$VERSION-$RELEASE --tgz
Source0: %{name}-%{version}.tar.gz
URL: http://www.candlepinproject.org
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%if %use_m2crypto
%if 0%{?sles_version}
Requires: python-m2crypto
%else
Requires: m2crypto
%endif
%endif
Requires: python-iniparse
Requires: rpm-python
Requires: python-dateutil
%if %use_simplejson
Requires: python-simplejson
%endif
Requires: python-rhsm-certificates = %{version}-%{release}

%if 0%{?sles_version}
BuildRequires: python-devel >= 2.6
%else
BuildRequires: python2-devel
%endif
BuildRequires: python-setuptools
BuildRequires: openssl-devel


%description
A small library for communicating with the REST interface of a Red Hat Unified
Entitlement Platform. This interface is used for the management of system
entitlements, certificates, and access to content.


%package certificates
Summary: Certificates required to communicate with a Red Hat Unified Entitlement Platform
Group: Development/Libraries

%description certificates
This package contains certificates required for communicating with the REST interface
of a Red Hat Unified Entitlement Platform, used for the management of system entitlements
and to receive access to content. Please note this package does not have a dependency on
Python. The name instead reflects its relationship to python-rhsm.

%prep
%setup -q -n python-rhsm-%{version}

%build
# create a version.py with the rpm version info
PYTHON_RHSM_VERSION=%{version} PYTHON_RHSM_RELEASE=%{release} CFLAGS="%{optflags}" LDFLAGS="%{__global_ldflags}" %{__python} setup.py build

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

%dir %{python_sitearch}/rhsm

%{python_sitearch}/rhsm/*
%{python_sitearch}/rhsm-*.egg-info

%files certificates
%attr(755,root,root) %dir %{_sysconfdir}/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm/ca

%attr(644,root,root) %{_sysconfdir}/rhsm/ca/*.pem

%changelog
* Fri Sep 01 2017 Kevin Howell <khowell@redhat.com> 1.19.10-1
- 1481384: Do not update redhat.repo at RateLimitExceededException
  (jhnidek@redhat.com)

* Wed Jun 07 2017 Kevin Howell <khowell@redhat.com> 1.19.9-1
- 1444453: Have gettext return unicode instead of bytes. (awood@redhat.com)
- 1457197: Env. variable no_proxy=* is not ignored (jhnidek@redhat.com)

* Tue May 30 2017 Kevin Howell <khowell@redhat.com> 1.19.8-1
- 1443164: no_proxy match the host name when *.redhat.com is used
  (jhnidek@redhat.com)

* Wed May 24 2017 Kevin Howell <khowell@redhat.com> 1.19.7-1
- 1443159: Added default value for splay configuration (jhnidek@redhat.com)
- 1451166: Fix Host header when using proxy (khowell@redhat.com)

* Tue May 02 2017 Kevin Howell <khowell@redhat.com> 1.19.6-1
- 1426343: fixed rct to display cert without subjectAltName.
  (jhnidek@redhat.com)
- Add Update subscriptions pools (tcoufal@redhat.com)
- Add support to list future subscription pools (tcoufal@redhat.com)

* Mon Apr 17 2017 Kevin Howell <khowell@redhat.com> 1.19.5-1
- 1432990: Better message for bad CA cert (wpoteat@redhat.com)

* Mon Apr 10 2017 Kevin Howell <khowell@redhat.com> 1.19.4-1
- 1438552: Allows releases to be listed through a proxy (csnyder@redhat.com)
- 1420533: Add no_proxy option to API, config, UI (khowell@redhat.com)

* Fri Mar 31 2017 Kevin Howell <khowell@redhat.com> 1.19.3-1
- 1435475: Support older versions of M2Crypto (awood@redhat.com)
- 1427069: Prioritize content from Basic entitlements (khowell@redhat.com)

* Mon Mar 13 2017 Kevin Howell <khowell@redhat.com> 1.19.2-1
- 1423443: Handle IndexError during m2crypto request (khowell@redhat.com)
- Move python-rhsm into subdirectory (khowell@redhat.com)

* Wed Jan 25 2017 Alex Wood <awood@redhat.com> 1.19.1-1
- Adjust our C bindings for OpenSSL v1.1 API. (awood@redhat.com)
- Make python-rhsm Python-3 compatible (khowell@redhat.com)

* Thu Jan 19 2017 Alex Wood <awood@redhat.com> 1.19.0-1
- Bump version to 1.19 (adarshvritant@gmail.com)
- Adds new super class BaseRhsmLib that exposes request results.
  (awood@redhat.com)

* Fri Dec 09 2016 Vritant Jain <adarshvritant@gmail.com> 1.18.6-1
- 1400719: Proxy host not available for release command (wpoteat@redhat.com)
- 1397201: Expose classes in m2crypto wrapper (khowell@redhat.com)

* Fri Nov 25 2016 Vritant Jain <adarshvritant@gmail.com> 1.18.5-1
- 1396405: Use an int for port on connections (csnyder@redhat.com)
- 1393010: Correlate request ID, method and handler in logs
  (csnyder@redhat.com)
- 1394776: Fix port, insecure, and handler options on M2Crypto wrapper
  (csnyder@redhat.com)
- 1394351: Add httplib constants to m2cryptohttp (khowell@redhat.com)
- 1390688: Add missing socket import (khowell@redhat.com)
- Reduce usage of m2crypto (#184) (kevin@kahowell.net)

* Sun Oct 16 2016 Vritant Jain <adarshvritant@gmail.com> 1.18.4-1
- Added 6.9 releaser (adarshvritant@gmail.com)

* Sun Oct 16 2016 Vritant Jain <adarshvritant@gmail.com> 1.18.3-1
- 1320371: Fix case of retry-after header handling (khowell@redhat.com)
- Fedora 22 is end-of-life. (awood@redhat.com)
- 1311429: Honor no_proxy environment variable (khowell@redhat.com)

* Fri Sep 16 2016 Alex Wood <awood@redhat.com> 1.18.2-1
- 1176219: Raise ProxyException in Restlib (khowell@redhat.com)
- 1367243: Handle RestlibException 404 in refresh (khowell@redhat.com)
- 1367243: Fix 404 check in regen entitlement funcs (khowell@redhat.com)
- Revert "1367243: Fix 404 check in regen entitlement funcs"
  (khowell@redhat.com)
- 1367243: Fix 404 check in regen entitlement funcs (khowell@redhat.com)
- Ensure both cert regen methods succeed despite BadStatusLine from server
  (csnyder@redhat.com)
- Update fix to include BadStatusLine responses from the server
  (csnyder@redhat.com)
- 1366301: Entitlement regeneration no longer propagates server errors
  (crog@redhat.com)
- 1365280: Update default_log_level to INFO (csnyder@redhat.com)
- 1334916: Add rhsm.conf logging section defaults (csnyder@redhat.com)
- 1360909: Added functionality for regenerating entitlement certificates
  (crog@redhat.com)
- 1315901: Exception handling for PEM cert read (wpoteat@redhat.com)

* Fri Jul 15 2016 Alex Wood <awood@redhat.com> 1.18.1-1
- Bump version to 1.18 (vrjain@redhat.com)

* Thu Jun 30 2016 Vritant Jain <vrjain@redhat.com> 1.17.5-1
- 1104332: Separate out the rhsm certs into a separate RPM (vrjain@redhat.com)

* Tue Jun 21 2016 Vritant Jain <vrjain@redhat.com> 1.17.4-1
- 1346417: Allow users to set socket timeout. (awood@redhat.com)
- Fix Flake8 Errors (bcourt@redhat.com)
- Add Fedora 24 to the branch list. (awood@redhat.com)
- Added basic SLES compatibilty. Tested against SLES 11 SP3
  (darinlively@gmail.com)

* Thu May 12 2016 Darin Lively <darinlively@gmail.com> 1.17.3-0
- Added basic SLES build compatibilty

* Mon Apr 25 2016 Vritant Jain <vrjain@redhat.com> 1.17.2-1
- Added 7.3 releaser (vrjain@redhat.com)
- Updated UEPConnection.getProduct to explicitly reference product UUID
  (crog@redhat.com)

* Mon Feb 01 2016 Christopher Snyder <csnyder@redhat.com> 1.17.1-1
- Bump version to 1.17.0 (csnyder@redhat.com)

* Tue Jan 19 2016 Christopher Snyder <csnyder@redhat.com> 1.16.6-1
- 1297337: change server strings to new default (wpoteat@redhat.com)

* Wed Jan 06 2016 Christopher Snyder <csnyder@redhat.com> 1.16.5-1
- 1271158: Updates documentation to better explain when exceptions are thrown
  (csnyder@redhat.com)
- 1272203: Default used in place of empty config entry (wpoteat@redhat.com)
- 1284683: Entitlement certificate path checking allows for listing files
  (wpoteat@redhat.com)
- Fedora 21 is end of life. (awood@redhat.com)

* Fri Dec 04 2015 Alex Wood <awood@redhat.com> 1.16.4-1
- HypervisorCheckIn now accepts options as a keyword argument,
  options.reporter_id is now sent if provided (csnyder@redhat.com)

* Tue Dec 01 2015 Christopher Snyder <csnyder@redhat.com> 1.16.3-1
- Added release target for RHEL 6.8 (crog@redhat.com)
- 1198178: Adds wrapper method to allow removal of entitlements by pool id
  (csnyder@redhat.com)
- Expand the docs and comments about GoneException. (alikins@redhat.com)
- Adieu dgoodwin. (awood@redhat.com)

* Wed Sep 02 2015 Alex Wood <awood@redhat.com> 1.16.2-1
- Adds RateLimitExceededException which is raised in response to 429 from the
  remote host (csnyder@redhat.com)
- 1242057: This cert is no longer used and can be removed (wpoteat@redhat.com)

* Thu Aug 13 2015 Alex Wood <awood@redhat.com> 1.16.1-1
- 1247890: KeyErrors are now caught when checking manager capabilities
  (csnyder@redhat.com)
- Add user-agent to rhsm requests. (alikins@redhat.com)

* Thu Jul 23 2015 Alex Wood <awood@redhat.com> 1.16.0-1
- Bump to version 1.16 (crog@redhat.com)

* Fri Jul 10 2015 Chris Rog <crog@redhat.com> 1.15.4-1
- 

* Tue Jul 07 2015 Adrian Likins <alikins@redhat.com> 1.15.3-1
- Define global_ld_flags when not already defined. (awood@redhat.com)
- Adding tests for 202s from alikins/AsyncBind (csnyder@redhat.com)
- Updates to accomodate candlepin/virt-who/csnyder/new_report_api
  (csnyder@redhat.com)
- Adding jobStatus helper methods from alikins/AsyncBind (csnyder@redhat.com)
- HypervisorCheckIn now uses the new API, if available (csnyder@redhat.com)

* Mon Jun 22 2015 Chris Rog <crog@redhat.com> 1.15.2-1
- Added releaser configuration for RHEL 7.2 (crog@redhat.com)
- Use non-deprecated Tito properties. (awood@redhat.com)

* Thu Jun 11 2015 Alex Wood <awood@redhat.com> 1.15.1-1
- Move Python.h include to be first include (alikins@redhat.com)
- 1092564: Provide LDFLAGS to setup.py to enable hardened build.
  (awood@redhat.com)
- Bump version to 1.15 (wpoteat@redhat.com)
- Do not process proxy environment variables if host is in no_proxy
  (martin.matuska@axelspringer.de)

* Tue Jun 02 2015 William Poteat <wpoteat@redhat.com> 1.14.3-1
- 1225600: Default config entry needs to include the substitution string
  (wpoteat@redhat.com)
- Add F22 to Fedora branches. (awood@redhat.com)

* Thu Feb 26 2015 Alex Wood <awood@redhat.com> 1.14.2-1
- 1195446: Only set global socket timeout on RHEL 5. (alikins@redhat.com)
- Cleanup up connection logging. (alikins@redhat.com)

* Fri Feb 06 2015 Devan Goodwin <dgoodwin@rm-rf.ca> 1.14.1-1
- 976855: build_py now populates version.py with ver (alikins@redhat.com)
- 1187587: Correct project URL in spec file. (awood@redhat.com)
* Fri Jan 09 2015 William Poteat <wpoteat@redhat.com> 1.13.10-1
- Add custom JSON encoding for set objects. (awood@redhat.com)
- Update SSL context options to follow the M2Crypto standard idiom.
  (awood@redhat.com)

* Wed Jan 07 2015 Devan Goodwin <dgoodwin@rm-rf.ca> 1.13.9-1
- Allow clients to report product tags. (awood@redhat.com)

* Fri Nov 21 2014 William Poteat <wpoteat@redhat.com> 1.13.8-1
- 

* Fri Nov 07 2014 Unknown name <wpoteat@redhat.com> 1.13.7-1
- 

* Thu Oct 23 2014 Alex Wood <awood@redhat.com> 1.13.6-1
- 1153375: Support TLSv1.2 and v1.1 by default. (alikins@redhat.com)
- Set CA PEM files permissions to 644. (awood@redhat.com)

* Thu Oct 16 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.13.5-1
- Renamed the "containstext" parameter to "matches." (crog@redhat.com)

* Thu Oct 16 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.13.4-1
- Added support for contains_text to UEPConnection.getPoolsList
  (crog@redhat.com)

* Fri Oct 03 2014 Alex Wood <awood@redhat.com> 1.13.3-1
- Make more use of setup.py. (alikins@redhat.com)

* Sun Sep 07 2014 Alex Wood <awood@redhat.com> 1.13.2-1
- Remove a 2.6ism that slipped in. (awood@redhat.com)

* Thu Sep 04 2014 Alex Wood <awood@redhat.com> 1.13.1-1
- version bump (jesusr@redhat.com)

* Fri Jul 25 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.5-1
- 1120431: Support for complex path matching. (bkearney@redhat.com)

* Thu Jul 03 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.4-1
- Add required bz flags to tito releasers. (dgoodwin@redhat.com)
- Remove pyqver verbose flag. (alikins@redhat.com)
- Use tox.ini to setup pep8 for 'make stylish' (alikins@redhat.com)
- Update pyqver setup. Set min version of 2.7. (alikins@redhat.com)
- Add libcrypto to list of libs to link to. (bcourt@redhat.com)

* Mon Jun 16 2014 Michael Stead <mstead@redhat.com> 1.12.3-1
- Add 6.6/7.1 release targets. (dgoodwin@redhat.com)
- Add a key_path() to EntitlementCertificate (alikins@redhat.com)

* Tue Jun 10 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.12.2-1
- Detect when operating in container mode and load host system's config.
  (dgoodwin@redhat.com)
- Convert doc strings to sphinx/restructuredtext (alikins@redhat.com)
- Add setup for using sphinx for docs. (alikins@redhat.com)

* Thu Jun 05 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.1-1
- bump version to 1.12 (jesusr@redhat.com)
- Add connection method to get available releases (mstead@redhat.com)

* Mon May 26 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.11.5-1
- 1090350: fix time drift detection (ckozak@redhat.com)
- 1096676: Use simplejson on RHEL 5. (dgoodwin@redhat.com)
- 1094492: Alternate Subject needs different type that allows more characters.
  (wpoteat@redhat.com)

* Mon Apr 28 2014 ckozak <ckozak@redhat.com> 1.11.4-1

* Thu Apr 10 2014 Alex Wood <awood@redhat.com> 1.11.3-1
- Specifically check for brand_name/brand_type="" (alikins@redhat.com)
- Support new apis for guests and hypervisors (ckozak@redhat.com)

* Thu Mar 20 2014 Alex Wood <awood@redhat.com> 1.11.2-1
- Add attributes for brand_name (alikins@redhat.com)

* Thu Feb 27 2014 Alex Wood <awood@redhat.com> 1.11.1-1
- rev version to 1.11.1 (ckozak@redhat.com)
- removed rhel7 releaser (ckozak@redhat.com)

* Mon Feb 03 2014 ckozak <ckozak@redhat.com> 1.10.12-1
- Add request_certs option to getEntitlementList() call (vitty@redhat.com)

* Wed Jan 22 2014 ckozak <ckozak@redhat.com> 1.10.11-1
- Fedora 18 is at end of life. (awood@redhat.com)

* Mon Jan 06 2014 ckozak <ckozak@redhat.com> 1.10.10-1
- make sure server supports guestId data (ckozak@redhat.com)

* Tue Dec 17 2013 ckozak <ckozak@redhat.com> 1.10.9-1
- Removing entitlement cert and key from getEntitlementList (ckozak@redhat.com)
- respect http(s)_proxy env variable for proxy information (jesusr@redhat.com)

* Wed Nov 27 2013 jesus m. rodriguez <jmrodri@gmail.com> 1.10.8-1
- Add the method to retrieve all the subscriptions for an owner (wpoteat@redhat.com)

* Thu Nov 14 2013 ckozak <ckozak@redhat.com> 1.10.7-1
- getOwnerInfo introduced (vitty@redhat.com)

* Thu Nov 07 2013 ckozak <ckozak@redhat.com> 1.10.6-1
- Fix a crash that occurs when rhsm.conf is missing (ckozak@redhat.com)
- Correct implementation of __eq__ for Content objects. (awood@redhat.com)
- Log ca_dir and loaded ca pems on one line. (alikins@redhat.com)
- Add default full_refresh_on_yum option. (awood@redhat.com)
- Send empty JSON list when deleting all overrides. (awood@redhat.com)
- Add __hash__ method to Content classes. (awood@redhat.com)
- Add method to get all content overrides for a consumer (mstead@redhat.com)
- Add methods to set and delete content overrides. (awood@redhat.com)
- 1008808: json ValueErrors have no .msg attribute (alikins@redhat.com)

* Fri Oct 25 2013 ckozak <ckozak@redhat.com> 1.10.5-1
- 1006748: replace simplejson with 'ourjson' (alikins@redhat.com)
- Log the new requestUuid from candlepin if it is present in the response.
  (dgoodwin@redhat.com)

* Fri Oct 25 2013 ckozak <ckozak@redhat.com>
- 1006748: replace simplejson with 'ourjson' (alikins@redhat.com)
- Log the new requestUuid from candlepin if it is present in the response.
  (dgoodwin@redhat.com)

* Wed Oct 02 2013 ckozak <ckozak@redhat.com> 1.10.3-1
- Merge pull request #89 from candlepin/alikins/flex_branding
  (c4kofony@gmail.com)
- Change brand attr 'os' to 'brand_type' (alikins@redhat.com)
- s/os_name/os (alikins@redhat.com)
- add support for 'os_name' productid attribute (alikins@redhat.com)

* Thu Sep 12 2013 Alex Wood <awood@redhat.com> 1.10.2-1
- 998033: Handle 401 and 403 with no response body (alikins@redhat.com)
- Ignore json errors in validate_response (alikins@redhat.com)
- Add unit tests for Restlib.validate_response (alikins@redhat.com)
- 1000145: Fix deprecated exception message warning. (dgoodwin@redhat.com)

* Thu Aug 22 2013 Alex Wood <awood@redhat.com> 1.10.1-1
- 997194: fix interpolation of default values (ckozak@redhat.com)
- bump version to 1.10.x (jesusr@redhat.com)
- remove 6.5 releaser (jesusr@redhat.com)

* Wed Aug 14 2013 jesus m. rodriguez <jesusr@redhat.com> 1.9.2-1
- remove rhel 5.9, 5.10, 6.3, 6.4 (jesusr@redhat.com)
- Fedora 17 is at end of life. (awood@redhat.com)

* Wed Jul 31 2013 Alex Wood <awood@redhat.com> 1.9.1-1
- fix config failure (ckozak@redhat.com)
- 988476, 988085: fix default hostname, remove excess config list output
  (ckozak@redhat.com)
- rev master to 1.9.x (alikins@redhat.com)
- add compliance date option (ckozak@redhat.com)

* Fri Jul 12 2013 Adrian Likins <alikins@redhat.com> 1.8.14-1
- certs check warning period (ckozak@redhat.com)

* Fri Jun 21 2013 Adrian Likins <alikins@redhat.com> 1.8.13-1
- Added autoheal option to updateConsumer (cschevia@redhat.com)

* Fri May 31 2013 jesus m. rodriguez <jesusr@redhat.com> 1.8.12-1
- Update the releasers with a 6.3 (bkearney@redhat.com)
- 967566: Enhance the ssl bindings to expose the issuer. (bkearney@redhat.com)
- Update the dist-git releasers (bkearney@redhat.com)

* Fri May 10 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.11-1
- Don't attach a question mark to the request if not necessary.
  (awood@redhat.com)
- Sanitize consumerId input. (awood@redhat.com)
- Add more test cases for Content.arches (alikins@redhat.com)
- add 'arches' list of arches to Content object (alikins@redhat.com)
- Add optional consumer to getPool. (awood@redhat.com)

* Tue May 07 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.10-1
- Added core limit to entitlement object. (mstead@redhat.com)
- Codestyle cleanup. (alikins@redhat.com)

* Thu Apr 18 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.9-1
- add note about check_path squashing '//' in paths (alikins@redhat.com)
- normalizing path before checking (jsherril@redhat.com)
- two new candlepin API methods (cduryee@redhat.com)
- remove redundant \'s and slight formatting cleanup (alikins@redhat.com)
- replace if "a == None" calls with if a is None (alikins@redhat.com)
- Additional methods for working with owners (cduryee@redhat.com)

* Wed Mar 27 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.8-1
- no 'json' module in rhel5, use simplejson instead (alikins@redhat.com)
- Adding plugin directory config option. (awood@redhat.com)

* Thu Mar 07 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.7-1
- 912776: Improve error message (wpoteat@redhat.com)
- Add a method to get compliance status for a consumer. (awood@redhat.com)

* Mon Mar 04 2013 William Poteat <wpoteat@redhat.com> 1.8.6-1
- Add a get_int method to RhsmConfigParser (alikins@redhat.com)

* Tue Feb 19 2013 Alex Wood <awood@redhat.com> 1.8.5-1
- 908671: Adding pool id to entitlement certificate. (awood@redhat.com)

* Tue Feb 19 2013 Alex Wood <awood@redhat.com>
- 908671: Adding pool id to entitlement certificate. (awood@redhat.com)

* Thu Feb 14 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.3-1
- 907536: Don't send body if it's just "" (alikins@redhat.com)
- 882459: Change --heal-interval to --attach-interval in rhsmcertd
  (wpoteat@redhat.com)

* Thu Jan 31 2013 Bryan Kearney <bkearney@redhat.com> 1.8.2-1
- Add a default value for the report_package_profile setting
  (bkearney@redhat.com)
- Remove F16 releasers, add F18. (dgoodwin@redhat.com)

* Thu Jan 24 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.1-1
- Do not retrieve the value unless the match is valid (bkearney@redhat.com)
- Only look for a single item as it is quicker and all we care about is zero or
  not zero (bkearney@redhat.com)
- Several small tweaks: (bkearney@redhat.com)
- Store off the len of the oid to save recalculating it more that once
  (bkearney@redhat.com)
- certificate.match will now only accept oids. (bkearney@redhat.com)
- Remove the use of exceptions to denote a return value of false.
  (bkearney@redhat.com)
- The email.utils module was named email.Utils in RHEL5 (bkearney@redhat.com)
- Make stylish issues resolved (bkearney@redhat.com)
- 772936: Warn the user when clock skew is detected. (bkearney@redhat.com)
- Improve logging for rhsmcertd scenarios (wpoteat@redhat.com)
- 845622: If an identity certificate has expired, there should be a friendly
  error message (wpoteat@redhat.com)
- Add international text to test automatic JSON encoding. (awood@redhat.com)
- 880070: Adding unicode encoding hook for simplejson. (awood@redhat.com)
- 848836: Remove trailing / from the handler in UEPConnection
  (bkearney@redhat.com)
- 884259: If LANG is unset, do not attempt to send up a default locale in
  redeem call (bkearney@redhat.com)

* Tue Nov 20 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.0-1
- Reversioning to 1.8.x stream.

* Mon Nov 19 2012 Adrian Likins <alikins@redhat.com> 1.1.6-1
- Making product and order info optional for a v3 EntitlementCertificate, since
  the server side will never have that data. (mhrivnak@redhat.com)
- Adding path authorization checking for both v1 and v3 entitlement
  certificates (mhrivnak@redhat.com)

* Fri Nov 16 2012 Adrian Likins <alikins@redhat.com> 1.1.5-1
- Added ram_limit to certificate Order (mstead@redhat.com)

* Thu Nov 01 2012 Adrian Likins <alikins@redhat.com> 1.1.4-1
- fixing a bug where certificates with carriage returns could not be parsed.
  (mhrivnak@redhat.com)
- 790481: Send up headers with the subscription-manager and python-rhsm version
  info. (bkearney@redhat.com)

* Wed Oct 10 2012 Adrian Likins <alikins@redhat.com> 1.1.3-1
- 863961: add test case for id cert default version (alikins@redhat.com)
- 857426: Do not pass None when body is empty collection (mstead@redhat.com)
- 863961: set a default version for id certs (alikins@redhat.com)
- 859652: Subscribe with service level being ignored (wpoteat@redhat.com)

* Tue Sep 25 2012 Adrian Likins <alikins@redhat.com> 1.1.2-1
- add 6.4 releaser (alikins@redhat.com)

* Wed Sep 19 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.1.1-1
- Read certv3 detached format (jbowes@redhat.com)
- Read file content types from certificates (mstead@redhat.com)

* Wed Aug 29 2012 Alex Wood <awood@redhat.com> 1.0.7-1
- 851644: Only use the cert file if it exists (bkearney@redhat.com)

* Tue Aug 28 2012 Alex Wood <awood@redhat.com> 1.0.6-1
- 848742: support arbitrary bit length serial numbers (jbowes@redhat.com)
- Stop doing F15 Fedora builds, add EL5 public builds. (dgoodwin@redhat.com)

* Thu Aug 09 2012 Alex Wood <awood@redhat.com> 1.0.5-1
- add versionlint, requires pyqver (alikins@redhat.com)
- Adding subject back to new certs (mstead@redhat.com)
- 842885: add __str__ to NetworkException, ala  #830767 (alikins@redhat.com)
- 830767: Add __str__ method to RemoteServerException. (awood@redhat.com)
- Fix None product architectures. (dgoodwin@redhat.com)
- Remove deprecated use of DateRange.has[Date|Now] (jbowes@redhat.com)
- mark hasDate as deprecated as well (alikins@redhat.com)

* Wed Jul 25 2012 Alex Wood <awood@redhat.com> 1.0.4-1
- Remove unused stub method. (dgoodwin@redhat.com)
- Cleanup entitlement cert keys on delete. (dgoodwin@redhat.com)
- Drop unused quantity and flex quantity from Content. (dgoodwin@redhat.com)
- Make CertFactory and Extensions2 classes private. (dgoodwin@redhat.com)
- RHEL5 syntax fixes. (dgoodwin@redhat.com)
- Handle empty pem strings when creating certs. (dgoodwin@redhat.com)
- Remove Base64 decoding. (dgoodwin@redhat.com)
- Fix failing subjectAltName nosetest (jbowes@redhat.com)
- Fix up remaining compiler warnings (jbowes@redhat.com)
- Fix up memory leaks (jbowes@redhat.com)
- clean up some C module compiler warnings (jbowes@redhat.com)
- Fix get_all_extensions (jbowes@redhat.com)
- C module formatting fixups (jbowes@redhat.com)
- Add as_pem method to C module (jbowes@redhat.com)
- Revert Extensions object to old state, add new sub-class.
  (dgoodwin@redhat.com)
- Spec file changes for C module (jbowes@redhat.com)
- Get nosetests running (jbowes@redhat.com)
- tell setup.py to use nose (jbowes@redhat.com)
- get certv2 tests passing (jbowes@redhat.com)
- Move methods onto X509 class in C cert reader (jbowes@redhat.com)
- Add method to get all extensions in a dict (jbowes@redhat.com)
- Add POC C based cert reader (jbowes@redhat.com)
- Remove use of str.format for RHEL5. (dgoodwin@redhat.com)
- Remove some python2.6'ism (trailing if's) (alikins@redhat.com)
- add "version_check" target that runs pyqver (alikins@redhat.com)
- Fix error reporting on bad certs. (dgoodwin@redhat.com)
- Remove number from order/account fields. (dgoodwin@redhat.com)
- Style fixes. (dgoodwin@redhat.com)
- Certv2 cleanup. (dgoodwin@redhat.com)
- Cleanup bad padding/header cert testing. (dgoodwin@redhat.com)
- New method of parsing X509 extensions. (dgoodwin@redhat.com)
- Better cert type detection. (dgoodwin@redhat.com)
- Deprecate the old certificate module classes. (dgoodwin@redhat.com)
- Rename order support level to service level. (dgoodwin@redhat.com)
- Convert product arch to multi-valued. (dgoodwin@redhat.com)
- Add factory methods to certificate module. (dgoodwin@redhat.com)
- Parse V2 entitlement certificates. (dgoodwin@redhat.com)
- Add missing os import. (dgoodwin@redhat.com)
- Improve certificate2 error handling. (dgoodwin@redhat.com)
- Remove V1 named classes. (dgoodwin@redhat.com)
- Add cert is_expired method. (dgoodwin@redhat.com)
- Fix cert path issue. (dgoodwin@redhat.com)
- Major/minor attributes not available in 5.4 (mstead@redhat.com)
- 834108: Set the default connection timeout to 1 min. (jbowes@redhat.com)
- Add default values to certificate2 Order class. (dgoodwin@redhat.com)
- Define identity certificates explicitly. (dgoodwin@redhat.com)
- Add identity cert support to certificate2 module. (dgoodwin@redhat.com)
- Add file writing/deleting for new certificates. (dgoodwin@redhat.com)
- Add product info to certificate2 module. (dgoodwin@redhat.com)
- Add content info to certificate2 module. (dgoodwin@redhat.com)
- Add order info to certificate2 module. (dgoodwin@redhat.com)
- Port basic certificate data into new module. (dgoodwin@redhat.com)
- Add certificate2 module and cert creation factory. (dgoodwin@redhat.com)

* Thu Jun 28 2012 Alex Wood <awood@redhat.com> 1.0.3-1
- Update copyright dates (jbowes@redhat.com)
- 825952: Error after deleting consumer at server (wpoteat@redhat.com)

* Thu Jun 07 2012 Alex Wood <awood@redhat.com> 1.0.2-1
- add upstream server var to version obj (cduryee@redhat.com)
- 822057: wrap ContentConnection port in safe_int (cduryee@redhat.com)
- 822965: subscription-manager release does not work with proxies
  (cduryee@redhat.com)
- 806958: BadCertificateException not displaying properly. (awood@redhat.com)
- 822965: release verb does not work with proxies (cduryee@redhat.com)
- Add config for "checkcommits" (alikins@redhat.com)
- Include various Makefile improvements from subscription-manager
  (alikins@redhat.com)
- Upload el6 yum packages to another dir for compatability.
  (dgoodwin@redhat.com)

* Wed May 16 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.0.1-1
- Add default constants for RHN connections. (dgoodwin@redhat.com)
- 813296: Remove check for candlepin_version (jbowes@redhat.com)
- Remove module scope eval of config properties (alikins@redhat.com)
- Add call to get Candlepin status. (awood@redhat.com)
- Added access to python-rhsm/sub-man versions. (mstead@redhat.com)

* Thu Apr 26 2012 Michael Stead <mstead@redhat.com> 1.0.0-1
- Updated version due to 6.3 branching. (mstead@redhat.com)

* Wed Apr 04 2012 Michael Stead <mstead@redhat.com> 0.99.8-1
- 807721: Setting missing default values (mstead@redhat.com)

* Fri Mar 23 2012 Michael Stead <mstead@redhat.com> 0.99.7-1
- 803773: quote international characters in activation keys before sending to
  server (cduryee@redhat.com)
- PEP8 fixes. (mstead@redhat.com)

* Wed Mar 14 2012 Michael Stead <mstead@redhat.com> 0.99.6-1
- Add ContentConnection to support rhsm "release" command (alikins@redhat.com)
- Allow unsetting the consumer service level. (dgoodwin@redhat.com)

* Tue Mar 06 2012 Michael Stead <mstead@redhat.com> 0.99.5-1
- 744654: Any bad value from the config file, when converting to an int, causes
  a traceback. (bkearney@redhat.com)
- Add support for dry-run autobind requests. (dgoodwin@redhat.com)
- Build for Fedora 17. (dgoodwin@redhat.com)

* Wed Feb 22 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 0.99.4-1
- Add support for updating consumer service level. (dgoodwin@redhat.com)
- Add call to list service levels for an org. (dgoodwin@redhat.com)
- Add GoneException for deleted consumers (jbowes@redhat.com)

* Fri Jan 27 2012 Michael Stead <mstead@redhat.com> 0.99.3-1
- 785247: Update releasers.conf for RHEL6.3 (mstead@redhat.com)
- Stop building for F14. (dgoodwin@redhat.com)

* Thu Jan 12 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 0.99.2-1
- 768983: When consuming a future subsciption, the repos --list should be empty
  (wpoteat@redhat.com)
- 720360: Write *-key.pem files out with 0600 permissions. (awood@redhat.com)
- 754425: Remove grace period logic (cduryee@redhat.com)

* Mon Dec 12 2011 William Poteat <wpoteat@redhat.com> 0.98.7-1
- 766895: Added hypervisorCheckIn call to allow sending a mapping of host/guest ids for
  creation/update. (mstead@redhat.com)

* Tue Dec 06 2011 William Poteat <wpoteat@redhat.com> 0.98.5-1
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

