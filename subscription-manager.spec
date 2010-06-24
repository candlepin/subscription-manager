Name: subscription-manager      
Version: 0.64
Release: 1%{?dist}
Summary: Supported tools and libraries for subscription and repo Management       
Group:   System Environment/Base         
License: GPLv2 
Source0: %{name}-%{version}.tar.gz
URL:     https://engineering.redhat.com/trac/subscription-manager 
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires: python-dmidecode
Requires:  python-ethtool 
Requires:  python-simplejson
Requires:  python-iniparse
Requires:  m2crypto 
Requires:  PyXML 
Requires: yum >= 3.2.19-15
Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
BuildRequires: python-devel
BuildRequires: gettext
BuildRequires: intltool

%description
Subscription Manager package provides programs and libraries to allow users 
to manager subscriptions/yumrepos from Red Hat entitlement or deployment 
Platform.

%package -n subscription-manager-gnome
Summary: A GUI interface to manage Red Hat product subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}
Requires: pygtk2 pygtk2-libglade gnome-python2 gnome-python2-canvas
Requires: usermode-gtk
Requires: subscription-manager

%description -n subscription-manager-gnome
This package contains a GTK+ graphical interface for configuring and 
registering a system with a Red Hat Entitlement platform and manage 
subscriptions.


%prep
%setup -q

%build
make -f Makefile

%install
rm -rf $RPM_BUILD_ROOT
make -f Makefile install VERSION=%{version}-%{release} PREFIX=$RPM_BUILD_ROOT MANPATH=%{_mandir}

%post -n subscription-manager-gnome
touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :

%postun -n subscription-manager-gnome
if [ $1 -eq 0 ] ; then
    touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%posttrans -n subscription-manager-gnome
gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)

# dirs
%dir %{_datadir}/rhsm
%dir %{_datadir}/rhsm/gui
%dir %{_datadir}/rhsm/gui/data
%dir %{_datadir}/rhsm/gui/data/icons

#files
%{_datadir}/rhsm/__init__.py*
%{_datadir}/rhsm/connection.py*
%{_datadir}/rhsm/managercli.py*
%{_datadir}/rhsm/managerlib.py*
%{_datadir}/rhsm/repolib.py*
/usr/lib/yum-plugins/rhsmplugin.py*
%{_datadir}/rhsm/certificate.py*
%{_datadir}/rhsm/certmgr.py*
%{_datadir}/rhsm/certlib.py*
%{_datadir}/rhsm/hwprobe.py*
%{_datadir}/rhsm/config.py*
%{_datadir}/rhsm/constants.py*
%{_datadir}/rhsm/logutil.py*
%{_datadir}/rhsm/lock.py*
%{_datadir}/rhsm/facts.py*
#%{_datadir}/rhsm/rhsmcertd.*
%attr(755,root,root) %{_sbindir}/subscription-manager-cli
%attr(755,root,root) %dir %{_var}/log/rhsm
%attr(755,root,root) %{_bindir}/rhsmcertd
%attr(755,root,root) %{_sysconfdir}/init.d/rhsmcertd

# config files
%config(noreplace) %attr(644,root,root) /etc/rhsm/rhsm.conf
%attr(644,root,root) /etc/yum/pluginconf.d/rhsmplugin.conf

%doc
%{_mandir}/man8/subscription-manager-cli.8*

%files -n subscription-manager-gnome
%defattr(-,root,root,-)
%{_datadir}/rhsm/gui/__init__.py* 
%{_datadir}/rhsm/gui/managergui.py*  
%{_datadir}/rhsm/gui/messageWindow.py*  
%{_datadir}/rhsm/gui/progress.py* 
%{_datadir}/rhsm/gui/data/standaloneH.glade  
%{_datadir}/rhsm/gui/data/subsgui.glade  
%{_datadir}/rhsm/gui/data/subsMgr.glade
%{_datadir}/rhsm/gui/data/progress.glade
%{_datadir}/rhsm/gui/data/icons/subsmgr-empty.png
%{_datadir}/rhsm/gui/data/icons/subsmgr-full.png
%{_datadir}/icons/hicolor/16x16/apps/subsmgr.png
%attr(755,root,root) %{_sbindir}/subscription-manager-gui


%post
chkconfig --add rhsmcertd
/sbin/service rhsmcertd start

%preun
if [ $1 = 0 ] ; then
   /sbin/service rhsmcertd stop >/dev/null 2>&1
   /sbin/chkconfig --del rhsmcertd
fi

%changelog
* Thu Jun 24 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.64-1
- Adding in 'unlimited' quantity support. (jharris@redhat.com)
- Candlepin connection library updates. (dgoodwin@redhat.com)
- Allow the user to sepcify a type at registration (bkearney@redhat.com)
- Force username and password to always be required on register
  (bkearney@redhat.com)
- more alignment changes on reg token screen (pkilambi@redhat.com)
- fxing alignment issues on reg token screen and fix for other tab content
  (pkilambi@redhat.com)
- removing raise (pkilambi@redhat.com)
- fixing unregistered case to load cert import (pkilambi@redhat.com)
- load match object intead of other by default (pkilambi@redhat.com)
- compare by productId for other tab as well (pkilambi@redhat.com)
- compare matched and compatible by productId (pkilambi@redhat.com)
- comare matched package list with productids (pkilambi@redhat.com)
- changing the matched bucket to use productId for matching
  (pkilambi@redhat.com)
- Hide the incompatible pools tab by default and make it a config option
  (pkilambi@redhat.com)
- Teach the gui to send up email/lang during token activation, too
  (jbowes@redhat.com)
- Update cli option names for regtoken activation to match api
  (jbowes@redhat.com)
- Teach the cli to send up email/lang on regtoken activation
  (jbowes@redhat.com)
- Swap OrderNumber and SerialNumber fields for formatting in list --consumed
  (adrian@alikins.usersys.redhat.com)
- Adding some changes to disable horizontal scrolling and align the columns
  appropriately (pkilambi@redhat.com)
- fix the display order for contract info (pkilambi@redhat.com)
- 602258 - represent subscription data as productId instead of sku
  (pkilambi@redhat.com)

* Wed Jun 09 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.63-1
- Resolves: #589626
- Adding accessibility string for widgets for automation support
  (pkilambi@redhat.com)
- updating spec to include new files (pkilambi@prad.rdu.redhat.com)
- Add support for a /etc/rhsn/facts/*.facts files that can define additional
  facts (adrian@alikins.usersys.redhat.com)
- test (pkilambi@redhat.com)
- adding some todos for later (pkilambi@redhat.com)
- get the other tab to populate entitlements (pkilambi@redhat.com)
- rename oder with contract (pkilambi@redhat.com)
- fixing progress dialog path (pkilambi@redhat.com)
- minor fixed (pkilambi@redhat.com)
- Adding order info to list call (pkilambi@redhat.com)

* Tue Jun 01 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.61-1
- Resolves: #591247
- clean up (pkilambi@redhat.com)
- Revert "Add uep wrapper where async logic will live" (pkilambi@redhat.com)
- Revert "Hook up register/unregister to be async" (pkilambi@redhat.com)
- if we get an error from IT lets show it instead of generic error for reg
  token activation (pkilambi@redhat.com)
- removing test checks (pkilambi@redhat.com)
- Hook up register/unregister to be async (jbowes@redhat.com)
- Add uep wrapper where async logic will live (jbowes@redhat.com)
- error message is now a popup (pkilambi@redhat.com)
- Load gui resources relative to the python code (to run from src)
  (jbowes@redhat.com)
- Append consistant python path (jbowes@redhat.com)
- Add .gitignore (jbowes@redhat.com)
- Adding Order info to cli and gui (pkilambi@redhat.com)
- Convert to using candlepin's jackson formatted json (jbowes@redhat.com)
- Fix OID ending in 10+.  Add Order.getContract(). (jortel@redhat.com)
- Changing the Add subscriptions screen to bucketize entitlements into
  categories and use a tabbed interface (pkilambi@redhat.com)
- Changing name of referenced variable to regnum (calfonso@redhat.com)
- test (pkilambi@redhat.com)
- test (pkilambi@redhat.com)
- fix autosubscribe to user right consumer (pkilambi@redhat.com)

* Tue May 11 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.60-1
- Resolves: #591247 - format the dat correctly for gui add
- send in product hash as part of autobind  
- Format the cli print to be sequential instead of a table form. This makes the
  output more reliable (pkilambi@redhat.com)
- Fix rhsmcertd not sleeping properly.  Add Bundle class for combining key &
  cert next sprint. (jortel@redhat.com)
- unsubscribe uses serial number directly from subscription info per subscribed
  product (pkilambi@redhat.com)
- Change unsubscribe to use serial number instead of product names
  (pkilambi@redhat.com)

* Mon May 10 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.55-1
- Resolves:  #590094 - encode translated error strings before displaying
  (pkilambi@redhat.com)

* Fri May 07 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.54-1
- Resolves: #584510
- Adding a progress bar to Apply subscriptions process (pkilambi@redhat.com)

* Thu May 06 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.52-1
- Resolves: #589626 - unregister now removes stale entitlement certs from the clients (pkilambi@redhat.com)

* Wed May 05 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.51-1
- Resolves: #585193, #587647, #584440, #586462, #588408
- 585193, 587647 - Handle Non-Network case Gracefully
- 584440 - Validate manually uploaded entitlement certs
- 586462 - strip out http connection stuff and default all connections through
  ssl (pkilambi@redhat.com)
- 588408 - re initialize CP instance with consumer certs post registration
  (pkilambi@redhat.com)
- fixing registration to not load certs while creating a cp instance
  (pkilambi@redhat.com)
- 588389: Ensure list of expired products is unique. (jortel@redhat.com)

* Fri Apr 30 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.48-1
- Resolves: #586388, #586525
- Adding support to unsubscribe user by serial number (pkilambi@redhat.com)
- Disable update/unsubscribe buttons if a product is not selected or if a
  selected product is not yet subscribed to any subscription
  (pkilambi@redhat.com)
- hide the add/update windows after successfully applying the subscription
  (pkilambi@redhat.com)
- Fix certlib exception and linger bug. (jortel@redhat.com)
- Removing testing comment.  Add code doc. (jortel@redhat.com)
- Stop removing expired certificates; Display warning in yum for expired
  certificates. (jortel@redhat.com)
- 586388 - Allow multiple pools/products/regnumbers to be able to subscribe
  from commandline (pkilambi@redhat.com)
- exception handling for unsubscribe functionality (pkilambi@redhat.com)
- 586525: Interpret interval as minutes. (jortel@redhat.com)
- clean up (pkilambi@redhat.com)
- Subscribe to pools in Add/Update button by pool id instead of
  productName.Ignore the productId and use productname in the list to identity
  the product pool in the list (pkilambi@redhat.com)
- Beautify error message display on bad login (jbowes@redhat.com)
- clean up old modules (pkilambi@redhat.com)

* Tue Apr 27 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.47-1
- Resolves:  #584330
- Add PyXML to the requires
- fixing the date format to be human readable for GUI (pkilambi@redhat.com)
- Add tzinfo to datetime objects returned by DateRange.begin() and
  DateRange.end() (jortel@redhat.com)
- Provide a command line and GUI option for user to automacally subscribe upon
  register. By default we only register the system (pkilambi@redhat.com)
- fixing the cli date format to be human readable (pkilambi@redhat.com)
- spec clean up (pkilambi@redhat.com)
- Adding support to show registration status on the main screen and direct
  users appropriately (pkilambi@redhat.com)
- 584330: Fix init.d script start() output. (jortel@redhat.com)
- 584137 - cli subscribe now uses cert serial number as ent Id until told
  otherwise (pkilambi@redhat.com)
- Add Reader to skip double newlines left by iniparse when sections are
  removed. (jortel@redhat.com)
- Migrate to iniparse. (jortel@redhat.com)
- Add certmgr to replace direct calling of certlib & repolib.
  (jortel@redhat.com)

* Tue Apr 20 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.41-1
- Resolves: #580043
- jbowes's fix for locale string replacement (pkilambi@redhat.com)
- unsubscribe products based on ent id from cert serial (pkilambi@redhat.com)
- dont show the content/role sets if the list is empty (pkilambi@redhat.com)
- Add access to product hash. (jortel@redhat.com)
- Preserve custom repo properties. (jortel@redhat.com)

* Fri Apr 16 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.39-1
- Resolves: #581032, #581489
- cleaning up obsolete exceptions (pkilambi@redhat.com)
- Certlib robustness & testing. Remove InvalidCertificate exception; no longer
  raised by ProductCertificate.getProduct() and
  EntitlementCertificate.getOrder() Ensure Directory classes only return 'good'
  certificates (not bogus ones). Detect and log invalid cert bundles from UEP.
  Overall more robust error handling. (jortel@redhat.com)

* Wed Apr 14 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.38-1
- Resolves: #568427
- eol string literal missing (pkilambi@redhat.com)
- modify the sequence in whihc subscription column is shown
  (pkilambi@redhat.com)
- fixing index issue due to mismatched product tuple (pkilambi@redhat.com)
- Exception Handling for custom exceptions sent down from candlepin
  (pkilambi@redhat.com)
- Remove all certificate caching; Change certificate read() to be instance
  based. (jortel@redhat.com)
- change to right header based on product state (pkilambi@redhat.com)
- Adding support to list products that are consuming a subscription but not
  installed (pkilambi@redhat.com)
- including locale info in request headers (pkilambi@redhat.com)
- clean up (pkilambi@redhat.com)
- adding a new column called subscription to gui/cli (pkilambi@redhat.com)
- support to handle multiple products per certs for cli/tui
  (pkilambi@redhat.com)
- Backtrack on some of the snapshot stuff. (jortel@redhat.com)
- unbregister account before re-registereing user from GUI
  (pkilambi@redhat.com)
- unregister existing consumer before re-registering with a force flag
  (pkilambi@redhat.com)
- Adding support to manually unregister a client to cli (pkilambi@redhat.com)

* Mon Apr 12 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.37-1
- Resolves: #580576 - fixing error message on failed registration (pkilambi@redhat.com)
- Resolves: #580955 - set ssl_port to cfg value instead of default (pkilambi@redhat.com)
- Ground work for directory snapshot caching. (jortel@redhat.com)
- Resolves: #580630 -  register window will now not be resizable (pkilambi@redhat.com)
- Updated for OID structure 04-07-10. (jortel@redhat.com)
- reflecting changes to the oid schema structure in the client tooling
  (pkilambi@redhat.com)
- Remove 'layered product versioning' prototype code. (jortel@redhat.com)

* Tue Apr 06 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.36-1
- Support for register system by consumerId
- rpmlint fixes
- Resolves: #578860 - alignment issues on registration details screen
- Resolves: #570489: Updating man page to reflect latest functionality
  (pkilambi@redhat.com)
- updating frame icon (pkilambi@redhat.com)

* Mon Apr 05 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.33-1
- Resolves: #578113 - lscpu is localized, use the right locale to accumulate hwdata
- Resolves: #578520 - if no products are selected, clicking 'Unsubscribe' should be a noop
- Resolves: #578517 registration dialog validates for missing input
- Resolves: #576568 catch the socket exceptions or any other unknow exception and  error gracefully (pkilambi@redhat.com)
- removing test files (pkilambi@redhat.com)
- specfile clean up (pkilambi@redhat.com)
- updated icons (pkilambi@redhat.com)
- some minor UI tweaks based on feedback from the demo (pkilambi@redhat.com)
- multiple bug fixes to gui, cli and proxy (pkilambi@redhat.com)
- Update product __str__ to show valid and valid date range.
  (jortel@redhat.com)
- test (pkilambi@redhat.com)
- updating config to remove cert paths (pkilambi@redhat.com)
- Fix extension parsing with values on following line as '.\n<value>'.
  (jortel@redhat.com)

* Tue Mar 30 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.28-1
- Resolves:  #577238 #577140
- Use SSLv3 for Candlepin communication. (dgoodwin@redhat.com)
- Fix edge case in OID seaching. (jortel@redhat.com)
- dont use ssl certs for register even for re registration
  (pkilambi@redhat.com)
- Update for entitlement OID schema 3-29-10 spec=DOC-33548 which includes yum
  repo (.1) namespace. (jortel@redhat.com)
- make --force default true (pkilambi@redhat.com)
- Ability to unsubscribe in offline mode. Adding a confirm window before
  unsubscribing (pkilambi@redhat.com)
- --force option to override existing registrations (pkilambi@redhat.com)
- adding dist to rpm spec (pkilambi@redhat.com)
- bug#571242 return error code of 0 for help options (pkilambi@redhat.com)

* Fri Mar 26 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.26-1
- Resolves:  #568427
- bug#577238 dont replace config upon reinstall (pkilambi@redhat.com)
- breaking clients. comment our ssl cert stuff until its functional on cp
  (pkilambi@redhat.com)
- some ssl changes (pkilambi@redhat.com)
- Update for getCertificateSerials() returned format change.
  (jortel@redhat.com)
- Initial layered product version work. (jortel@redhat.com)
- notify user politely if there are no available ents (pkilambi@redhat.com)
- adding id to the available list (pkilambi@redhat.com)
- Added icon support for rhsm gui (pkilambi@redhat.com)

* Thu Mar 25 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.22-1
- Resolves: #568427
- Spec file clean up
- moving gnome tools to separate package
- methods to define concrete description for products based on the state, product info and entitlement info.
- constants file to accumulate all static strings in one place 

* Wed Mar 24 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.21-1
- Resolves: #568427
- event notification from add/remove and update subscription actions to main window
- error notification windows
- registration should now auto subscribe products and redirect to already-registered screen

* Mon Mar 22 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.20-1
- Resolves: #568427
- logging support
- changes to support identity cert parsing

* Fri Mar 19 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.19-1
- Resolves: #568427 
- Changes to support dynamic icon changes
- changes to support resteasy api changes
- fixed alignment issues in mainWindow

* Wed Mar 17 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.17-1
- Resolves:  #568427 - New registration/regtoken/add subscriptions screens

* Mon Mar 15 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.17-1
- Resolves:  #568426
- More changes to api proxy
- new gui screens 

* Thu Mar 11 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.16-1
- Resolves:  #568426 
- more updates to connection.py api flush down
- updates to new screens and layout in gui

* Mon Mar 08 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.14-1
- Resolves: #568426 - new build

* Wed Mar 03 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.12-1
- Resolves: #568433 - Flushed out hardware info
- man page for cli

* Mon Feb 22 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-1
- packaging subscription-manager

