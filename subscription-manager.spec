Name: subscription-manager
Version: 0.98.2
Release: 1%{?dist}
Summary: Tools and libraries for subscription and repository management
Group:   System Environment/Base
License: GPLv2
Source0: %{name}-%{version}.tar.gz
URL:     https://engineering.redhat.com/trac/subscription-manager
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:  python-ethtool
Requires:  python-simplejson
Requires:  python-iniparse
Requires:  PyXML
Requires:  glib2
Requires:  virt-what
Requires:  python-rhsm >= 0.96.11
Requires:  dbus-python
Requires:  yum >= 3.2.19-15

# There's no dmi to read on these arches, so don't pull in this dep.
%ifnarch ppc ppc64 s390 s390x
Requires:  python-dmidecode
%endif

Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
BuildRequires: python-devel
BuildRequires: gettext
BuildRequires: intltool
BuildRequires: libnotify-devel
BuildRequires: gtk2-devel
BuildRequires: desktop-file-utils
BuildRequires: redhat-lsb
BuildRequires: scrollkeeper


%description
The Subscription Manager package provides programs and libraries to allow users
to manage subscriptions and yum repositories from the Red Hat entitlement
platform.


%package -n subscription-manager-gnome
Summary: A GUI interface to manage Red Hat product subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}
Requires: pygtk2 pygtk2-libglade gnome-python2 gnome-python2-canvas
Requires: usermode
Requires: usermode-gtk
Requires: librsvg2
Requires: dbus-x11
Requires(post): scrollkeeper
Requires(postun): scrollkeeper

%description -n subscription-manager-gnome
This package contains a GTK+ graphical interface for configuring and
registering a system with a Red Hat Entitlement platform and manage
subscriptions.

%package -n subscription-manager-firstboot
Summary: Firstboot screens for subscription manager
Group: System Environment/Base
Requires: %{name}-gnome = %{version}-%{release}
%{?el5:Requires: rhn-setup-gnome >= 0.4.20-49}
%{?el6:Requires: rhn-setup-gnome >= 1.0.0-39}
Requires: librsvg2

%description -n subscription-manager-firstboot
This package contains the firstboot screens for subscription manager.

%package -n subscription-manager-migration
Summary: Migration scripts for moving to certificate based subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}

%description -n subscription-manager-migration
This package contains scripts that aid in moving to certificate based
subscriptions

%prep
%setup -q

%build
make -f Makefile

%install
rm -rf $RPM_BUILD_ROOT
make -f Makefile install VERSION=%{version}-%{release} PREFIX=$RPM_BUILD_ROOT MANPATH=%{_mandir}

%if 0%{?fedora} < 15
desktop-file-validate \
        %{buildroot}/etc/xdg/autostart/rhsm-icon.desktop
%endif
desktop-file-validate \
        %{buildroot}/usr/share/applications/subscription-manager.desktop
%find_lang rhsm

# fix timestamps on our byte compiled files so them match across arches
find $RPM_BUILD_ROOT -name \*.py -exec touch -r %{SOURCE0} '{}' \;

# fake out the redhat.repo file
mkdir %{buildroot}%{_sysconfdir}/yum.repos.d
touch %{buildroot}%{_sysconfdir}/yum.repos.d/redhat.repo

%post -n subscription-manager-gnome
touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
scrollkeeper-update -q -o %{_datadir}/omf/%{name} || :

%postun -n subscription-manager-gnome
if [ $1 -eq 0 ] ; then
    touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
    scrollkeeper-update -q || :
fi

%posttrans -n subscription-manager-gnome
gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%clean
rm -rf $RPM_BUILD_ROOT

%files -f rhsm.lang
%defattr(-,root,root,-)

%attr(755,root,root) %dir %{_var}/log/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm/facts

%attr(640,root,root) %config(noreplace) %{_sysconfdir}/rhsm/rhsm.conf
%config(noreplace) %{_sysconfdir}/dbus-1/system.d/com.redhat.SubscriptionManager.conf

#remove the repo file when we are deleted
%ghost %{_sysconfdir}/yum.repos.d/redhat.repo

%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/subscription-manager.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/product-id.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/katello.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/logrotate.d/subscription-manager
%{_sysconfdir}/bash_completion.d/subscription-manager

%{_sysconfdir}/cron.daily/rhsmd
%{_datadir}/dbus-1/system-services/com.redhat.SubscriptionManager.service

%dir %{_datadir}/rhsm
%dir %{_datadir}/rhsm/subscription_manager
%{_datadir}/rhsm/subscription_manager/__init__.py*
%{_datadir}/rhsm/subscription_manager/i18n.py*
%{_datadir}/rhsm/subscription_manager/i18n_optparse.py*
%{_datadir}/rhsm/subscription_manager/managercli.py*
%{_datadir}/rhsm/subscription_manager/managerlib.py*
%{_datadir}/rhsm/subscription_manager/async.py*
%{_datadir}/rhsm/subscription_manager/logutil.py*
%{_datadir}/rhsm/subscription_manager/repolib.py*
%{_prefix}/lib/yum-plugins/subscription-manager.py*
%{_prefix}/lib/yum-plugins/product-id.py*
%{_prefix}/lib/yum-plugins/katello.py*
%{_datadir}/rhsm/subscription_manager/certlib.py*
%{_datadir}/rhsm/subscription_manager/certdirectory.py*
%{_datadir}/rhsm/subscription_manager/cert_sorter.py*
%{_datadir}/rhsm/subscription_manager/validity.py*
%{_datadir}/rhsm/subscription_manager/hwprobe.py*
%{_datadir}/rhsm/subscription_manager/constants.py*
%{_datadir}/rhsm/subscription_manager/lock.py*
%{_datadir}/rhsm/subscription_manager/facts.py*
%{_datadir}/rhsm/subscription_manager/factlib.py*
%{_datadir}/rhsm/subscription_manager/productid.py*
%{_datadir}/rhsm/subscription_manager/cache.py*
%{_datadir}/rhsm/subscription_manager/branding
%{_datadir}/rhsm/subscription_manager/quantity.py*
%{_datadir}/rhsm/subscription_manager/jsonwrapper.py*

%attr(755,root,root) %{_datadir}/rhsm/subscription_manager/certmgr.py*
%attr(755,root,root) %{_sbindir}/subscription-manager
%attr(755,root,root) %{_bindir}/subscription-manager
%attr(755,root,root) %{_bindir}/rhsmcertd
%attr(755,root,root) %{_initrddir}/rhsmcertd
%attr(755,root,root) %{_libexecdir}/rhsmd
%attr(755,root,root) %dir %{_var}/run/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm/facts
%attr(755,root,root) %dir %{_var}/lib/rhsm/packages
%attr(755,root,root) %dir %{_var}/lib/rhsm/cache
%{_sysconfdir}/pam.d/subscription-manager
%{_sysconfdir}/security/console.apps/subscription-manager

%doc
%{_mandir}/man8/subscription-manager.8*
%{_mandir}/man8/rhsmcertd.8*


%files -n subscription-manager-gnome
%defattr(-,root,root,-)
%dir %{_datadir}/rhsm/subscription_manager/gui
%dir %{_datadir}/rhsm/subscription_manager/gui/data
%dir %{_datadir}/rhsm/subscription_manager/gui/data/icons
%{_datadir}/rhsm/subscription_manager/gui/*
%{_datadir}/icons/hicolor/scalable/apps/subscription-manager.svg
%{_datadir}/applications/subscription-manager.desktop
%attr(755,root,root) %{_sbindir}/subscription-manager-gui
%attr(755,root,root) %{_bindir}/subscription-manager-gui

%if 0%{?fedora} < 15
%{_bindir}/rhsm-icon
%{_sysconfdir}/xdg/autostart/rhsm-icon.desktop
%endif

%{_sysconfdir}/pam.d/subscription-manager-gui
%{_sysconfdir}/security/console.apps/subscription-manager-gui

%doc
%{_mandir}/man8/subscription-manager-gui.8*
%{_mandir}/man8/rhsm-compliance-icon.8*
%{_datadir}/omf/subscription-manager
%{_datadir}/gnome/help/subscription-manager

%files -n subscription-manager-firstboot
%defattr(-,root,root,-)
%{_datadir}/rhn/up2date_client/firstboot/rhsm_login.py*
%{_datadir}/rhn/up2date_client/firstboot/rhsm_subscriptions.py*
%if 0%{?rhel} < 6
%if 0%{?fedora} > 12
%else
%{_prefix}/share/firstboot/modules/rhsm_login.py*
%{_prefix}/share/firstboot/modules/rhsm_subscriptions.py*
%endif
%endif

%files -n subscription-manager-migration
%defattr(-,root,root,-)
%attr(755,root,root) %{_sbindir}/rhn-migrate-classic-to-rhsm
%attr(755,root,root) %{_sbindir}/install-num-migrate-to-rhsm

%post
chkconfig --add rhsmcertd
if [ -x /bin/dbus-send ] ; then
  dbus-send --system --type=method_call --dest=org.freedesktop.DBus / org.freedesktop.DBus.ReloadConfig > /dev/null 2>&1 || :
fi
if [ "$1" -eq "2" ] ; then
    /sbin/service rhsmcertd condrestart >/dev/null 2>&1 || :
fi

%preun
if [ $1 -eq 0 ] ; then
   /sbin/service rhsmcertd stop >/dev/null 2>&1
   /sbin/chkconfig --del rhsmcertd
   if [ -x /bin/dbus-send ] ; then
     dbus-send --system --type=method_call --dest=org.freedesktop.DBus / org.freedesktop.DBus.ReloadConfig > /dev/null 2>&1 || :
   fi
fi

%changelog
* Fri Oct 28 2011 William Poteat <wpoteat@redhat.com> 0.98.2-1
- Switch to EL5 compatible APIs (jbowes@redhat.com)
- Remove post-healing logging of product status. (dgoodwin@redhat.com)
- Refresh certificates after healing. (dgoodwin@redhat.com)
- Push the latest strings to zanata (bkearney@redhat.com)
- 699970: Remove many of the multiple line items in the translated strings.
  (bkearney@redhat.com)
* Tue Oct 25 2011 William Poteat <wpoteat@redhat.com> 0.97.2-1
- Update the strings file and push it to Zanata (bkearney@redhat.com)
- 747024: Restore previous behaviour for unhandled exceptions
  (alikins@redhat.com)
- 747630: Fit allsubs tab in firstboot for verbose locales (jbowes@redhat.com)
- 747630: Use shorter strings for 'Entitlement Platform Registration'
  (jbowes@redhat.com)
- Fix yum repo location for EL6. (dgoodwin@redhat.com)
- 742013: More fixes for translations in firstboot (alikins@redhat.com)
- 742013: Fix for translations in firstboot (alikins@redhat.com)
- 692242: Subscription-manager does not force a dbus status check when certs
  are updated (cduryee@redhat.com)
- 746257: Update activationkey man page example (jbowes@redhat.com)
- 737145: remove successive newlines on write (jbowes@redhat.com)
- 694450: Updated chinese string which was incorrect (bkearney@redhat.com)
- 717654: Subscription-manager lock file should be created with the correct
  label (awood@redhat.com)
- Alter entitlements_valid to be ternary (cduryee@redhat.com)
- Adding new tito releasers.conf. (dgoodwin@redhat.com)

* Mon Oct 17 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.97.1-1
- 743704: Fix healing date issues. (dgoodwin@redhat.com)
- 580905: Add a help button to subscription-manager-gui (jbowes@redhat.com)
- 580905: include help documentation for the gui (jbowes@redhat.com)
- pep8/whitespace cleanups. make "make pep8" clean (alikins@redhat.com)
- remove en.po (alikins@redhat.com)
- 742128: Fix string concats in the get text calls to improve the strings for
  the translators (bkearney@redhat.com)
- 744536: handle unicode and plain str types passed to systemExit
  (alikins@redhat.com)
- 743732: French and Chinese Usage strings were incomplete
  (bkearney@redhat.com)
- 743732: typo in the as.po file caused the entire language to be dropped
  (bkearney@redhat.com)
- 744136: workaround date parsing problems in some locales (alikins@redhat.com)
- 744110: Fuzzy strings from translation tool are visibile in the UI
  (bkearney@redhat.com)
- 742128: Newlines in strings cause the Usage line in help to not be
  translated. (bkearney@redhat.com)
- 737145: remove the call to tidy(), it wasn't needed and isn't always
  available (jbowes@redhat.com)
- 737145: prevent whitespace from building up in redhat.repo
  (jbowes@redhat.com)
- 743082: don't show stale subscriptions after autosub (jbowes@redhat.com)
- 740773: Do not delete certs if we have repo metadata errors
  (alikins@redhat.com)
- Be even more paranoid about exceptions in the plugin. (alikins@redhat.com)
- add katello plugin to spec file (alikins@redhat.com)
- katello yum plugin to support $env and $org in repo confs
  (alikins@redhat.com)
- 742416: Remove the close button from our progress dialog (jbowes@redhat.com)
- 742013: sub-mgr translations not showing up in firstboot (cduryee@redhat.com)
- 742425:Extra strings are in the translation files (bkearney@redhat.com)
- 742473:Extra strings are in the Korean translations (bkearney@redhat.com)
- Find instances where the string substitution is done before the string
  lookup, this will cause localization to fail (bkearney@redhat.com)
- 742027: Certificate status does not account for rhn classic
  (cduryee@redhat.com)
- 741857,741820: Fixed issue where i18n was not being loaded before constants,
  causing untranslated text (mstead@redhat.com)
- 741563: Wrapped Type column name in gettext (mstead@redhat.com)
- 741863: Made the date box larger. (mstead@redhat.com)
- 741850: Properly wrapped with gettext. (mstead@redhat.com)
- 741293: Ensure that blank gpg urls do not have the baseurl prepended to them
  (bkearney@redhat.com)
- 737553: Change criteria for system.entitlements_valid comsumer fact
  (wpoteat@redhat.com)
- 725535: check that fopen was successful before writing to timestamp
  (cduryee@redhat.com)
- 740675: do a condrestart on rhsmcertd when we upgrade subscription-manager
  (cduryee@redhat.com)
- 741335: Fix a date comparison bug for healing. (dgoodwin@redhat.com)
- 740877: autosubscribe output was showing ver instead of status
  (alikins@redhat.com)
- heal for today and future (jesusr@redhat.com)
- 740046: Change entitlement match to product hash for date detection
  (wpoteat@redhat.com)
- 730020: Change if error logging to stderr (wpoteat@redhat.com)
- 740831: set subscribe button insensitive if nothing is selected
  (alikins@redhat.com)
- 692242: rhsm_icon disappears and will not return (cduryee@redhat.com)
- Pull in the latest translations from zanata (bkearney@redhat.com)
- 720022: Update man page for new command line options (bkearney@redhat.com)
- Add logging, tests, and comments for broken yellow detection.
  (dgoodwin@redhat.com)
- Cleanup several stacking problems in tests. (dgoodwin@redhat.com)
- 738517: use https when writing proxy values to redhat.repo
  (cduryee@redhat.com)
- 740046: Ensure common behavior on dates between CLI and GUI
  (wpoteat@redhat.com)
- 688454: On error, set DatePicker's date to the previously accepted date.
  (mstead@redhat.com)
- 733873: disable proxy options for cert import command (cduryee@redhat.com)
- Revert "zanata syncrhonization" (jesusr@redhat.com)
- uncomment daemonize(), was commented by mistake for debugging
  (cduryee@redhat.com)
- Bump the zanata version to match the spec version (bkearney@redhat.com)
- zanata syncrhonization (bkearney@redhat.com)
- 706853: Do not perform local cleanup if unregister server call fails
  (mstead@redhat.com)
- 737684: replace through with until in sub assistant (jbowes@redhat.com)
- 739796: replace certificate column with status (jbowes@redhat.com)
- 736784: Incorrect use of sys.exit in option checking (wpoteat@redhat.com)
- Move the CertSorter tests into correct module. (dgoodwin@redhat.com)
- 738549: Allow subscription-manager to run without dbus (jbowes@redhat.com)
- Allow sslverify to be changed (bkearney@redhat.com)
- 739714: Fix typo in the clean help text (bkearney@redhat.com)
- add check-syntax makefile target for emacs user[s] (alikins@redhat.com)
- add support for bash completion of subscription-manager (alikins@redhat.com)
- Revert "katello yum plugin to support $env and $org in repo confs"
  (alikins@redhat.com)
- 718045: Registration dialog remains open on invalid credentials.
  (mstead@redhat.com)
- 642660: [First Boot] Disable 'Back' button once registered and on
  subscription-manager screen (RHEL6) (mstead@redhat.com)
- 739595: [Fistboot] Ensure the credentials screen is reset on FB module
  initialization. (mstead@redhat.com)
- comment clarification (cduryee@redhat.com)
- 739227: make healFrequency non-mandatory (cduryee@redhat.com)
- move the future check around so we check it first (alikins@redhat.com)
- start tracking products that will be valid in the future (alikins@redhat.com)
- 736424: list --installed only shows installed products (alikins@redhat.com)
- s/all_products/installed_products (more accurate name) (alikins@redhat.com)
- katello yum plugin to support $env and $org in repo confs
  (alikins@redhat.com)
- 738327: C refactoring from sgrubb (cduryee@redhat.com)
- 738549: remove dbus dependency in post/postun steps (cduryee@redhat.com)
- Applying "indent -linux -pcs -psl -ci8 -cs -cli8 -cp0" to codebase.
  (cduryee@redhat.com)
- post branch version bump (jbowes@redhat.com)
- 737841: Handle dates beyond 2038 on 32-bit systems. (dgoodwin@redhat.com)
- Update the strings and the remote server location (bkearney@redhat.com)
- Changes to rhsmcertd to support healing frequency (part I).
  (cduryee@redhat.com)
- add autoheal option to certmgr.py (cduryee@redhat.com)
- 707641: CLI auto-subscribe tries to re-use basic auth credentials.
  (wpoteat@redhat.com)
- make "make stylish" run all the checks, make whitespace "pop"
  (alikins@redhat.com)
- 712047: yum prints non-error messages when running in quiet mode
  (cduryee@redhat.com)
- 736784: Subscription-manager config --remove add config property to rhsm.conf
  if it doesn't exist. (wpoteat@redhat.com)
- Update translations (bkearney@redhat.com)
- 735338: Subscription Manager CLI tool does not allow unsubscribe when not
  registered. (wpoteat@redhat.com)
- 735695: add support for multiple config "--remove" options via cli
  (cduryee@redhat.com)
- 734606: ImportFileExtractor now creates cert/key files based on serial number
  of the cert. (mstead@redhat.com)
- Moved multi-entitlement column (*) next to the quantity column.
  (mstead@redhat.com)
- Made the contract selector a little wider so all columns were visible (no
  manual resize). (mstead@redhat.com)
- 736166: move certs from subscription-manager to python-rhsm
  (cduryee@redhat.com)

* Wed Sep 07 2011 James Bowes <jbowes@redhat.com> 0.96.9-1
- 734880: Handle bundled certs in the installed produict status.
  (bkearney@redhat.com)
- Center the machine type column header. (mstead@redhat.com)
- Move quantity column to the end. (mstead@redhat.com)
- Center the Arch column header (mstead@redhat.com)
- Center tree view table properties. (mstead@redhat.com)
- Add '* Click to Adjust Quantity' label to places allowing editable
  subscription quantity. (mstead@redhat.com)
- managerlib was expecting a single ent_cert, but we return a list
  (alikins@redhat.com)
- Add the coverage tool detritus to .gitignore (alikins@redhat.com)
- Only autoheal when required (cduryee@redhat.com)
- 735226: Importing should fail without a valid key and cert
  (bkearney@redhat.com)
- Add a "refresh" method to cert_sorter (cduryee@redhat.com)
- Double click or button press (enter, return, space) on row will
  expand/collapse row. (mstead@redhat.com)
- Update to All Available Subscriptions tab to put stacked subscriptions under
  parent node. (mstead@redhat.com)
- Display subscription assistant's subscriptions as a tree. (mstead@redhat.com)
- Add a require_connection callback to commands (bkearney@redhat.com)
- 730020: Change the help text to show that config can list or set changes
  (bkearney@redhat.com)
- New icons for red/green (cduryee@redhat.com)
- Add virt_only attribute to subscription detail pane (cduryee@redhat.com)
- Use server side consumer autoheal flag. (dgoodwin@redhat.com)

* Tue Aug 30 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.8-1
- Fix issues with list --installed/consumed with deletion of certs
  (alikins@redhat.com)
- Display a dialog box when subscription import was successful.
  (cduryee@redhat.com)
- In the mysubs tab, title stacked groups by product name (jbowes@redhat.com)
- Removed icons for virt/phys machines and replaced with text column
  (mstead@redhat.com)
- 730018: Update for new registered with rhn classic msg (jbowes@redhat.com)
- 717629: Clear user credentials on registration dialog after register/cancel
  (mstead@redhat.com)
- 717405: Return to credentials dialog after cancelled registration.
  (mstead@redhat.com)
- 733658: Check if directory exists before listing files. (mstead@redhat.com)
- Correction to config command remove logic. Changes for List Formatting and
  Messages. (wpoteat@redhat.com)
- Support "yellow" icon for partially covered products (cduryee@redhat.com)
- Make cert_sorter show valid/partially_valid/unentitled mutually exclusive
  (alikins@redhat.com)

* Wed Aug 24 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.7-1
- I18N update. (dgoodwin@redhat.com)
- Add test case for entitlement certs with no products (alikins@redhat.com)
- Fix problem with subscribing to products with no product certs
  (alikins@redhat.com)
- Remove unneeded for loop around getProduct (alikins@redhat.com)
- Fix typo in partially valid syslog message (jbowes@redhat.com)
- 733042: Update default rhsm.conf values for production. (dgoodwin@redhat.com)
- 732499: Fix redeem command error handling. (dgoodwin@redhat.com)
- Move the project to the public zanata server (bkearney@redhat.com)
- implement red/yellow/green for the cli (jesusr@redhat.com)
- Add 'partially valid' status to syslog and nag icon (jbowes@redhat.com)
- Add a debugging cli arg to rhsmd to force a signal (jbowes@redhat.com)
- Group All Available subscriptions by stack id (mstead@redhat.com)
- Add stacking_id grouping to Subscription Assistant (mstead@redhat.com)
- Update man page. (bkearney@redhat.com)
- Refactor facts to use the cache manager logic. (dgoodwin@redhat.com)
- Fix "import" cli with no certs (alikins@redhat.com)
- Upload info about the installed products on the system. (dgoodwin@redhat.com)
- Add "partially valid entitlement coverage" status to top-left sm-gui icon.
  (cduryee@redhat.com)
- Aligned stacking id up with other subscription properties.
  (mstead@redhat.com)
- Display My Subscriptions as a tree grouped by stacking_id.
  (mstead@redhat.com)
- Created a MappedTreeStore implementation. (mstead@redhat.com)
- Created StackingGroupSorter class to sort entitlements into groups based on
  stacking_id (mstead@redhat.com)
- Make the environemnt output look like all the others (bkearney@redhat.com)
- Client-side changes for healing (cduryee@redhat.com)

* Wed Aug 17 2011 James Bowes <jbowes@repl.ca> 0.96.6-1
- 729688: expected "Network Error" message is not getting displayed in the GUI
  (cduryee@redhat.com)
- 727978: returning wrong exit code from subscription-manager redeem
  (cduryee@redhat.com)
- EntitlementDirectory._check_key was not returning for True case
  (alikins@redhat.com)
- Move the ImportFileExtractor for managerlib. (bkearney@redhat.com)
- 730114: Placed machine type icon and asterisk in seperate column
  (mstead@redhat.com)
- Remove unused check entitlements flag. (dgoodwin@redhat.com)
- Cleanup facts.json created during tests. (dgoodwin@redhat.com)
- Change all instances of "unknown" to "Unknown". (cduryee@redhat.com)
- 727970: delete future dated entitlements (cduryee@redhat.com)
- Fix a test assertion that isn't in RHEL 6 Python. (dgoodwin@redhat.com)
- add certdirectory.py to the files section (jesusr@redhat.com)
- Change to the CLI config manipulation includes updates for defaulted values
  and update for ACK (wpoteat@redhat.com)
- Add the latest man page from deon (bkearney@redhat.com)
- Track partially valid entitlements (alikins@redhat.com)
- Log uncaught GUI exception stacktraces. (dgoodwin@redhat.com)
- 727967: Fix first non-compliant date calculation past first expiry.
  (dgoodwin@redhat.com)
- Move Writer class over to certdirectory (cduryee@redhat.com)
- Break certlib into two files. (cduryee@redhat.com)
- 679822: add a check all button for invalid product selection
  (jbowes@redhat.com)
- Show asterisk in GUI when subscription allows multi-entitlement
  (mstead@redhat.com)
- Calculate default quantity for virtual machines using prod attributes vcpu,
  sockets or 1 (mstead@redhat.com)
- Command line ability to change config settings of the server
  (wpoteat@redhat.com)
- 728349: Environments help command should reference the correct command name.
  (bkearney@redhat.com)
- pep8 cleanups (alikins@redhat.com)
- Multiline error message was not parseable. Triple quote it.
  (alikins@redhat.com)
- 707752: may need a dbus-x11 package dependency for subscription-manager-gnome
  (cduryee@redhat.com)
- Multi-entitle yes/no for list (wottop@redhat.com)
- 712047: yum prints non-error messages when running in quiet mode
  (cduryee@redhat.com)
- 679822: Reselect products in subscription assistant (jbowes@redhat.com)
- Default quanity value to 1 when contract selection not required
  (mstead@redhat.com)
- 710149: Always show the compliance assistant button. (dgoodwin@redhat.com)
- 725046: Make the help text more explicit as to what the command does
  (bkearney@redhat.com)
* Wed Aug 03 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.5-1
- I18N update. (dgoodwin@redhat.com)
- check that dmi info was populated before attempting to query it
  (cduryee@redhat.com)
- 718205: Block read only users from registering via the command line and gui
  (bkearney@redhat.com)
- 727600: Ensure that the help messages for the new redeem action are
  consistent (bkearney@redhat.com)
- 725870: Do not require registration for some list commands.
  (dgoodwin@redhat.com)
- Updated default quantity calc to use product's vcpu for virt machine
  (mstead@redhat.com)
- Added MachineType to CLI list --available to indicate  whether pool is for
  physical/virtual machine. (mstead@redhat.com)
- Added icons to tables to identify whether a pool is for physical/virtual
  machine. (mstead@redhat.com)
- 726791: Rename subscriptoin activation to redemption (bkearney@redhat.com)
- Refresh the entitlements after activation key registration
- 717052: Removing the rpm should remove the redhat repo file
  (bkearney@redhat.com)
- 726440: Make host type 'Not Applicable' when guest is false
  (bkearney@redhat.com)
- Add virt.uuid reporting to facts (cduryee@redhat.com)
- 703997: fix a11y handler clash in subscription assistant (jbowes@redhat.com)
- 722248: Modify all blank facts to be 'Unknown' (bkearney@redhat.com)
- 725609: Refactored code so that GTK module is not loaded when running CLI.
  (mstead@redhat.com)
- 723248: Correctly update quantity when Subscribe button is
  clicked and quantity still in edit mode. (mstead@redhat.com)
- 723248: Validate quantity is greater than 0 before subscribe
  (mstead@redhat.com)
- Set defaults for quantity values in subscription assistant and contract
  selector (mstead@redhat.com)
- handle empty product names in list command (alikins@redhat.com)
- 719378: remove leading and trailing spaces in the username
  (bkearney@redhat.com)
- 722554: Improve error checking on the subscription quantity
  (bkearney@redhat.com)
- 723336: Cert deaemon was not using the refactored CertSorter class
  (bkearney@redhat.com)
- 724809: Support the repos call without logging in. (bkearney@redhat.com)
- 722239: CLI and GUI should show the same facts (bkearney@redhat.com)
- 719109: Added feedback for identity regeneration (bkearney@redhat.com)
- 706889: Fix -1 printed from CLI when exiting with Python 2.4.
  (dgoodwin@redhat.com)
- 719739: Make CLI orgs command more informative. (dgoodwin@redhat.com)
- Use polling file monitor impl instead of GIO. (mstead@redhat.com)
- 723363: Fixed unsubscribe when system is not registered. (mstead@redhat.com)
- 720045: Add a period at the end of the output (bkearney@redhat.com)
- 712980: Support importing single file containing key/certificate
  (mstead@redhat.com)
- 712415: Make the names consistent between list --installed and list
  --consumed (bkearney@redhat.com)
- 717664: Improve the usability of subscribes (bkearney@redhat.com)
- 720045: Fixed the header files in yum repolist (bkearney@redhat.com)
- 722281: Fixed type in output for facts being updated (bkearney@redhat.com)
- 722334: Display quantity used in list --consumed. (dgoodwin@redhat.com)
- Show contract selection dialog when there is only one pool and is multi-
  entitled (mstead@redhat.com)
- Check for socket counts in entitlement checks (alikins@redhat.com)
- 714306: Make subscription details accessability unique (bkearney@redhat.com)
- 717395: Add accessability strings to the owner and environment selection
  dialogs (bkearney@redhat.com)
- show stacking id in subscriptions detail pane (alikins@redhat.com)
- try to find pools that "stack" and validate that we have enough sockets to
  make them valid. (alikins@redhat.com)
- Add in primary versus secondary modules to try and focus the user on which
  ones to pick (bkearney@redhat.com)
- Find and send owner key during CLI registration if possible.
  (dgoodwin@redhat.com)
- 707525 - Facts update command displays success (mstead@redhat.com)
- 713164: fixes some strange phrases on pt_BR translation (mmello@redhat.com)
- Get owner select working with firstboot (jbowes@redhat.com)
- Hook up owner selection during registration (jbowes@redhat.com)
- Make autosubscribe its own async step during register (jbowes@redhat.com)
- make the initial registration call async, and pulse a progress bar
  (jbowes@redhat.com)
- Move register screen to its own module (jbowes@redhat.com)

* Wed Jul 13 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.4-1
- Add ability to select larger quantity on subscribe (mstead@redhat.com)
- 717734: Allow double clicking on fact dialog rows to support exanding and
  collapsing (bkearney@redhat.com)
- Improve how clean removes the proxy commands (bkearney@redhat.com)
- 720049: remove the proxy libraries from the repos command
  (bkearney@redhat.com)
- Upload package profiles if the server supports them. (dgoodwin@redhat.com)
- If updating facts on CLI, force the push. (dgoodwin@redhat.com)
- Refactor Facts to only write cache after uploading. (dgoodwin@redhat.com)
- Clean fact/profile caches in CLI clean command. (dgoodwin@redhat.com)
- Delete fact and profile caches on unregister. (dgoodwin@redhat.com)
- Log when facts haven't changed and we skip update. (dgoodwin@redhat.com)
- Close file descriptors when reading/writing facts. (dgoodwin@redhat.com)

* Wed Jul 06 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.3-1
- Support registration to Katello environments. (dgoodwin@redhat.com)
- Fix facts auto-update. (mstead@redhat.com)
- Add a repos command. (bkearney@redhat.com)
- 718217: Fixed the command name in the org usage (bkearney@redhat.com)
- Improve a few error messages (bkearney@redhat.com)
- 718052: Rebrand owner as org (bkearney@redhat.com)
- Updated My Subs quantity to display quantity used. (mstead@redhat.com)
- Added 'Quantity' column to 'My Subscriptions' tab. (mstead@redhat.com)
- Improve the output of subscribing to a single pool (bkearney@redhat.com)
- Improve the output from registering (bkearney@redhat.com)

* Mon Jun 27 2011 Devan Goodwin <dgoodwin@redhat.com> 0.96.2-1
- 656968: Add in a super class to cut down on the code duplication
  (bkearney@redhat.com)
- Update pool list request to match python-rhsm changes. (dgoodwin@redhat.com)
- 656975: Ran pylint on all code. No builtins were found (bkearney@redhat.com)
- 699442: Change the wording on the validty string to make it work
  (bkearney@redhat.com)
- 708226: Remove the parens in the subscription assistant (bkearney@redhat.com)
- Bit more cleanup of the help text (bkearney@redhat.com)
- Move activate to redeem (bkearney@redhat.com)
- Simple typo (bkearney@redhat.com)
- Remove the term lifecycle (bkearney@redhat.com)
- Clean up the main help text (bkearney@redhat.com)
- Add in primary versus secondary modules to try and focus the user on which
  ones to pick (bkearney@redhat.com)
- Find and send owner key during CLI registration if possible.
  (dgoodwin@redhat.com)
- 707525 - Facts update command displays success (mstead@redhat.com)
- 707525 - Facts update command displays success (mstead@redhat.com)
- 713164: fixes some strange phrases on pt_BR translation (mmello@redhat.com)
- pep8/pyflake/pylint cleanup: (alikins@redhat.com)
- pylint: remove unused imports (alikins@redhat.com)
- pylint: shadowed builtin id remove unused lines (alikins@redhat.com)
- pylint: shadowing builtin buffer (alikins@redhat.com)
- ignore "line too long" errors, we are no where close to that
  (alikins@redhat.com)
- add license blurb (alikins@redhat.com)
- Can add activation keys (bkearney@redhat.com)
- pep8 and pyflakes clean ups (alikins@redhat.com)
- added quantity to subscribe (wottop@dhcp231-152.rdu.redhat.com)
- revert (wottop@dhcp231-152.rdu.redhat.com)
- List subscribe (wottop@dhcp231-152.rdu.redhat.com)
- lies and magic to get the global CFG config class replaces with a stub
  (alikins@redhat.com)
- more whitespace cleanup (alikins@redhat.com)
- revert (alikins@redhat.com)
- Revert "696791: Change the way we detect cpu sockets on s390x"
  (alikins@redhat.com)
- cleanup some weird whitespace issues in hwprobe.py (alikins@redhat.com)
- 711133: new fix for old style to new style key format migrations
  (alikins@redhat.com)
- quite debug spew in stubs.py (alikins@redhat.com)
  certs (alikins@redhat.com)
- pass a real ISO8601 date in for start/end date (alikins@redhat.com)
  and subscription_assistant (alikins@redhat.com)
- import gtk.glade directly (alikins@redhat.com)
- 696791: Change the way we detect cpu sockets on s390x (alikins@redhat.com)
- Added the zanata.xml file for master (bkearney@redhat.com)
- show owner in gui (cduryee@redhat.com)
- Update the string files (bkearney@redhat.com)
- 709412: cli was using product names for ent cert-> product cert matching
  (alikins@redhat.com)
- 711133: Handle updates from old style key.pem certs (alikins@redhat.com)
- 706127: Subscription Assistant too large for firstboot (cduryee@redhat.com)
- 707041: date picker in subscription-manager-gui does not work
  (cduryee@redhat.com)
- 709754: Workaround for the way Desktop/Workstation repo's and productids
  work. (alikins@redhat.com)
- 708095: workaround for or_IN dates (cduryee@redhat.com)
- 705236: use correct path for pid lockfiles (cduryee@redhat.com)
- 706552: check for, log, and clear dmi warnings to prevent them being printed
  to stdout (cduryee@redhat.com)
- 707292: Better counting of cpu sockets (alikins@redhat.com)
- 709754: Workaround for the way Desktop/Workstation repo's and productids
  work. (alikins@redhat.com)
- 707292: Better counting of cpu sockets (alikins@redhat.com)
- 709412: cli was using product names for ent cert-> product cert matching
  (alikins@redhat.com)
  manager (alikins@redhat.com)
- 708095: workaround for or_IN dates (cduryee@redhat.com)
- 705236: use correct path for pid lockfiles (cduryee@redhat.com)
  manager (alikins@redhat.com)
- Disable RHSM status icon for F15. (dgoodwin@redhat.com)
- Get owner select working with firstboot (jbowes@redhat.com)
- 706552: check for, log, and clear dmi warnings to prevent them being printed
  to stdout (cduryee@redhat.com)
- Revert "Add redhat branding back for internal repo" (jbowes@redhat.com)
- Hook up owner selection during registration (jbowes@redhat.com)
- Make autosubscribe its own async step during register (jbowes@redhat.com)
- Add redhat branding back for internal repo (jbowes@redhat.com)
- remove redhat branding (jbowes@redhat.com)
- 700547: delay running the first icon status check (jbowes@redhat.com)
- 707313: rhel5 product id is being deleted upon first package install after
  subscribing to rhel5 subscription (cduryee@redhat.com)
- Change for owner list call (wottop@dhcp231-152.rdu.redhat.com)
- make the initial registration call async, and pulse a progress bar
  (jbowes@redhat.com)
- 670973: try to handle /var/log and /var/run being readonly
  (alikins@redhat.com)
- Move register screen to its own module (jbowes@redhat.com)
- 704305: fix translated string for "Invalid date format..."
  (alikins@redhat.com)
- 705445: Fix for calculation of "available" susbcriptions label
  (alikins@redhat.com)
- Introduce branding module (jbowes@redhat.com)
- Remove uses of Red Hat and RHN where it makes sense (jbowes@redhat.com)
- Remove unused rhsm.glade (jbowes@redhat.com)
- added hooks for 'list --owners' (wottop@dhcp231-152.rdu.redhat.com)
- 705068: product-id plugin displays duration (cduryee@redhat.com)
- Added the owner from the cli to the registration REST request
  (wottop@dhcp231-152.rdu.redhat.com)
- 670973: remove YumBase() in method default args (alikins@redhat.com)
- 697965: use str type for serial id's to fix issues on i386
  (alikins@redhat.com)
- changed the pool query to use both owner and consumer information
  (wottop@dhcp231-152.rdu.redhat.com)
- added owner information for cli command 'identity' (cduryee@redhat.com)
- a tab snuck in here (cduryee@redhat.com)
- 696791: Handle exceptions thrown in hardware detection modules.
  (alikins@redhat.com)
- 703920: contract selection was not showing dates for pools
  (alikins@redhat.com)
- 683553: Make -1 show as unlimited (bkearney@redhat.com)
- 703626: product-id yum plugin was using too new of yum api
  (alikins@redhat.com)
- 702026: confusing warning message when rhsm-icon runs twice
  (cduryee@redhat.com)
- 700838: we need to import glade from gtk (alikins@redhat.com)
- 670973: check for yum conduit api we need, it's missing on 5.7
  (alikins@redhat.com)
- 703491: firstboot would continue to next screen on auth failure
  (alikins@redhat.com)
- 700958: fire check_status dbus calls in a non-blocking manner
  (jbowes@redhat.com)
- 710458: Do not display activation messages as errors. (dgoodwin@redhat.com)
- 693527: Adding 'usage: ' id for older versions of optparse.
  (jharris@redhat.com)
- Remove unused firstboot dir (jbowes@redhat.com)
- 702092: fit 'activate a subscription' button in 800x600 (jbowes@redhat.com)
- 700952: Fix SystemExit traceback logging on older Python versions.
  (dgoodwin@redhat.com)
- 701263: Moving dmiinfo declaration and allowing for failures in dmi function
  calls. (jharris@redhat.com)
- 700601: try really hard to set a meaningful locale (alikins@redhat.com)
- remove debug raise (alikins@redhat.com)
- 700058: Displaying previous imported cert in cert browser option
  (cduryee@redhat.com)
- 700547: ensure the notification attaches to rhsm-icon (jbowes@redhat.com)
- Write unique key.pem for each entitlement. (dgoodwin@redhat.com)
- 700313: We were skipping the code that hides the activation button
  (alikins@redhat.com)
- 700313: Tweaking activate dialog properties to show in firstboot.
  (jharris@redhat.com)
- 700073: Background is click able while handling Import certificate dialog box
  (cduryee@redhat.com)
- 695234: dates are being displayed incorrectly everywhere (alikins@redhat.com)
- 697908: regression in subscription-manager unregister (cduryee@redhat.com)
- 696020: on x86, serial numbers do not like to be long's (alikins@redhat.com)
- 694851: only open one dbus proxy connection (jbowes@redhat.com)
- 695367: call to dbus-send fails during upgrades on selinux-enabled machines
  (cduryee@redhat.com)
- 696679: add pam/consolehelper links for subscription-manager
  (alikins@redhat.com)
- 674652: Subscription Manager Leaves Broken Yum Repos After Unregister
  (cduryee@redhat.com)
- update help text for identity command (jbowes@redhat.com)
- 696674: rhsmcertd was using the wrong path for certmgr.py
  (alikins@redhat.com)
- 696210: fix display of error messages with urls (alikins@redhat.com)
- 694839: Remove some pango markup and instead linkify links ourselves
  (alikins@redhat.com)
- indention fix (alikins@redhat.com)
- 683553: subscription-manager-gui is displaying unlimited pools as -1
  (cduryee@redhat.com)
- 696021: fix regression in error message formatting (jbowes@redhat.com)
- 694842: error messages do not get populated during firstboot
  (cduryee@redhat.com)
- 691784: fix entitlement failure that throws sequence error
  (alikins@redhat.com)
- Latest japanese strings (bkearney@redhat.com)
- 670798: put initscript in /etc/rc.d/init.d (jbowes@redhat.com)
- 694877: Fix wrong module imports in yum plugins and wrong path for certmgr.py
  (alikins@redhat.com)
- 693709: fix bug showing the "you are registered to rhn" dialog
  (alikins@redhat.com)
- 691784: Fix handling of unsubscribing imported certs while unregistered
  (alikins@redhat.com)
- 694662: New man page (bkearney@redhat.com)
- 691480: update syslog message for proper cli command name (jbowes@redhat.com)
- remove unused glade string (jbowes@redhat.com)
- 688508: override more of optparse for i18n (jbowes@redhat.com)
- 693549: New man pages (bkearney@redhat.com)
- change status_changed signal to entitlement_status_changed
  (jbowes@redhat.com)
- 693896: subscription manager does not always reload dbus scripts
  automatically (cduryee@redhat.com)
- 694154: remove extraneous slashes in symlink (cduryee@redhat.com)
- 693834: remove $PREFIX from svg icon symlink (alikins@redhat.com)
- re-extract i18n keys (jbowes@redhat.com)
- remove duplicate l10n from context removal (jbowes@redhat.com)
- remove msg context from glade files (jbowes@redhat.com)
- extract latest i18n keys (jbowes@redhat.com)
- Add the latest l10n strings (jbowes@redhat.com)
- throw a bugzilla script into rel-eng (cduryee@redhat.com)
- rename dbus interface (to get rid of compliance) (jbowes@redhat.com)
- get rid of 'compliance' subdir (jbowes@redhat.com)
- rename rhsm-complianced to rhsmd (jbowes@redhat.com)
- rename rhsm-compliance-icon to rhsm-icon (jbowes@redhat.com)
- Remove 'compliance' from the code (except for complianced and related)
  (jbowes@redhat.com)
- Add "arch" info to the product info displayed on installed products screen
  (alikins@redhat.com)
- 691788: Check if entitlement cert is valid before allowing manual import.
  (dgoodwin@redhat.com)
- 691137: set return code from main() for rhsmcertd (jbowes@redhat.com)
- 691784: unsubscribing a imported cert was causing an uncaught exception
  (alikins@redhat.com)
- fix imports for rhel6 firstboot modules (alikins@redhat.com)
- latest l10n strings (jbowes@redhat.com)
- 691536: More string updates (jbowes@redhat.com)
- 691536: update strings replacing compliance with valid (jbowes@redhat.com)
- unroll some deps on gui stuff from managerlib (alikins@redhat.com)
- SRC_DIR not CODE_DIR. CODE_DIR is where we install to (alikins@redhat.com)
- add new CODE_DIR to firstboot makefile rules (alikins@redhat.com)
- update test cases to import from subscription_manager (alikins@redhat.com)
- move the src from /src/ to /src/subscription_manager (alikins@redhat.com)
- 684647: i18n/l10n our .desktop files (jbowes@redhat.com)
- 691480: syslog non-compliance on the proper status code (jbowes@redhat.com)
- add logic to handle fedora (cduryee@redhat.com)
- Refactor to use "from susbcription_manager" style imports
  (alikins@redhat.com)
- s/subscriptionmanager/subscription_manager (alikins@redhat.com)
- backport firstboot modules to rhel5 firstboot module api (alikins@redhat.com)
- "use_action_appearance" nde property ot supported on rhel5, remove
  (alikins@redhat.com)
- move subscription-manager code from /usr/share/rhsm to
  /usr/share/rhsn/subscriptionmanager (alikins@redhat.com)
- we don't/can't install firstboot modules to up2date's dir on rhel5, so don't
  (alikins@redhat.com)
- alter conditional to work inside install manifest (cduryee@redhat.com)
- use lsb-release again to get around mock issue (cduryee@redhat.com)
- add dep for redhat-release (cduryee@redhat.com)
- remove dep on lsb_release (cduryee@redhat.com)
- Use polling instead of inotify on el5 (jbowes@redhat.com)
- On el5, create symlinks for firstboot code (cduryee@redhat.com)
- Fork firstboot files for rhel5 and 6. (cduryee@redhat.com)
- 688592: latest strings from the i18n team. (bkearney@redhat.com)
- Missed one translation (bkearney@redhat.com)
- support older yum plugin conduit api (alikins@redhat.com)
- RHEL 5.7 changes (partial) (cduryee@redhat.com)
- RHEL 5.7 changes (partial) (cduryee@redhat.com)
- remove use of "funcName" log formatting option (alikins@redhat.com)
- check for linux_distribution in platform module (alikins@redhat.com)
- replace use of platform module with our own code for RHEL5
  (alikins@redhat.com)
- remove unused import of dbus.mainloop (alikins@redhat.com)
- remove use of hashlib (not there on python2.4) and use md5
  (alikins@redhat.com)
- replace "a = b if b else c" construct since it's not allowed in python2.4
  (alikins@redhat.com)
- use button.get_property('sensitive') since gtk 2.10 lacks
  button.get_sensitive (alikins@redhat.com)
- 688192: don't look for dmi info on machines without dmi (jbowes@redhat.com)
- 688469: workaround for optparse's lack of i18n/l10n (jbowes@redhat.com)
- Ensure that username and password are translated (bkearney@redhat.com)
- 683968: ensure yum plugins don't log to stdout (jbowes@redhat.com)
- 688550: ensure i18n configuration is the first thing to happen
  (jbowes@redhat.com)
- Remove a bunch of unused values from constants.py (jbowes@redhat.com)
- Use xgettext's native glade file handling (jbowes@redhat.com)
- Make the register button translatable (bkearney@redhat.com)
- Regen the keys file (bkearney@redhat.com)
- Add Context extract to gettext (bkearney@redhat.com)
- 685086: Fact times were read from the file but not localized before putting
  on the ui (bkearney@redhat.com)
- 685099: Add in missed translations to the compliance assistant string
  (bkearney@redhat.com)
- 685108: Translation missed for the import dialog (bkearney@redhat.com)
- Remove stray 'raise e' (jbowes@redhat.com)
- 685145: Remove rogue use of pyOpenSSL (jbowes@redhat.com)
- use gobject instead of glib for el5 (jbowes@redhat.com)
- Add conditional support for python-inotify instead of gio (jbowes@redhat.com)
- 684680: Remove unnecessary gettext text domain calls, and ensure only using
  the rhsm domain (bkearney@redhat.com)
- compliant.svg was corrupt under librsvg 2.16. This version works in both 5
  and 6 (cduryee@redhat.com)
- 684285: Add a svg library dependency (bkearney@redhat.com)
- two small fixes for rhel5. Change a class def syntax, and use g_timeout_add
  instead of g_timeout_add_seconds (cduryee@redhat.com)
- Bring in the latest translations from the i18n team (bkearney@redhat.com)
- send up return codes and bypass handle_exception on SystemExit for sm-gui
  (cduryee@redhat.com)
- send up return codes and bypass handle_exception on SystemExit
  (cduryee@redhat.com)
- catch non-exceptional exception thrown by 2.4 (cduryee@redhat.com)
- Support date string parsing in python 2.4 (jbowes@redhat.com)
- 676377: rhsm-compliance-icon's status can be a day out of sync
  (cduryee@redhat.com)
- 681925: subscription-manager masks SIGPIPE when running virt-what, resulting
  in errors in shell commands (cduryee@redhat.com)
- 614453: fix list cli command for multi entitled products (jbowes@redhat.com)
- 682331: Latest man pages from Deon (bkearney@redhat.com)
- 682311: rhsm-compliance icon pegs the cpu at 100% (cduryee@redhat.com)
- Drop unnecessary sort and reverse of entitlement certs. (dgoodwin@redhat.com)
- 672821: Latest man pages from deon (bkearney@redhat.com)
- Add support for tags. (dgoodwin@redhat.com)
- 679961:  Clearing out all fields in subscription details widget.
  (jharris@redhat.com)
- 629670: check for warning periods in valid certs, not expired ones
  (jbowes@redhat.com)
- Remove unused getProductDescription code. (dgoodwin@redhat.com)
- 676371: Better Compliance Assistant refreshing after bind.
  (dgoodwin@redhat.com)
- Move the translations to be language only, not language plus country
  (bkearney@redhat.com)
- 678151: prompt for credentials if not supplied as cli args
  (jbowes@redhat.com)
- 680399: add --auto to subscribe (jbowes@redhat.com)
- 676377: rhsm-compliance-icon's status can be a day out of sync
  (cduryee@redhat.com)
- 672562 request for subscription-manager list --available --ondate option
  (cduryee@redhat.com)
- Add in the latest po files (bkearney@redhat.com)
- Rename the files correctly (bkearney@redhat.com)
- Add in the translated po files (bkearney@redhat.com)
- 678003: Write proxy info for yum repositories we manage.
  (dgoodwin@redhat.com)
- 678003: Fix a certlib cached connection. (dgoodwin@redhat.com)
- 677756 add accesibility names to compliance assistant tables
  (alikins@redhat.com)
- Fix a bug when bare strings were passed to handle_gui_exception
  (alikins@redhat.com)
- 573591: Fix the permissions on some directories (bkearney@redhat.com)
- 678049: Fix status after CLI register with --autosubscribe.
  (dgoodwin@redhat.com)
- The gui was looking for numerics for provides management, but it is returned
  as a string (bkearney@redhat.com)
- 676349: python deprecation fixups (jbowes@redhat.com)
- 676363 - rhsm-compliance-icon has no icon image (cduryee@redhat.com)
- 672562 - request for subscription-manager list --available --ondate option
  (cduryee@redhat.com)
- 672562 - request for subscription-manager list --available --ondate option
  (cduryee@redhat.com)
- 676371 - Compliance Assistant closes when you're not done
  (cduryee@redhat.com)
- 676348: make config file and runtime dirs/logs only readable by root
  (jbowes@redhat.com)
- 676534 - Got message “unable to read /var/lib/rhsm/facts/facts.json” at
  first time register to stage (cduryee@redhat.com)
- 675777 Date search field has no accessibility handler (cduryee@redhat.com)
- 675817 - Compliance Assistant needs an Update button for the date
  (cduryee@redhat.com)
- 675812 - Some tracebacks while beating on subscription-manager-gui
  (cduryee@redhat.com)
- 675951 compliance asst doesn't word wrap label (cduryee@redhat.com)
- 670655 can't dismiss error dialog when subscribing to personal subscriptions
  (cduryee@redhat.com)
- 673050: Using strftime to format update time. (jharris@redhat.com)
- 674078: send 'right now' for compliance today, too (jbowes@redhat.com)
- 673050: Treating time_t as int to work on i686. (jharris@redhat.com)

* Fri Feb 04 2011 Devan Goodwin <dgoodwin@redhat.com> 0.96.1-1
- 674418: Changing accessibility handles to reflect check box functionality.
  (jharris@redhat.com)
- 674691: Add vertical panes to the compliance assistant (jbowes@redhat.com)
- 674078: Send a timezone aware timestamp for activeOn pools query
  (jbowes@redhat.com)
- Update the man pages from deon (bkearney@redhat.com)
- Write metadata expire attribute in yum repos. (dgoodwin@redhat.com)
- Updating warning message. (jharris@redhat.com)
- 671588: hide incompatible pools from the compliance assistant
  (jbowes@redhat.com)
- 673621: Fix the use of tests for return codes (bkearney@redhat.com)
- Changing the RHN Classic warning and only displaying cli warning in register
  command. (jharris@redhat.com)
- Add a logrotate file (bkearney@redhat.com)
- Add a direct require on usermode (bkearney@redhat.com)
- Fix the dangling link for consolehelper (bkearney@redhat.com)
- Add support to compliance code for checking to see if we are RHN registered
  (alikins@redhat.com)
- Add the Encoding to the gui desktop file (bkearney@redhat.com)

* Fri Jan 28 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 673568 Use only svg for application icons. (jharris@redhat.com)

* Fri Jan 28 2011 Chris Duryee (beav) <cduryee@redhat.com>
- Move the man pages (bkearney@redhat.com)
- add a reload to the cert service (bkearney@redhat.com)
- Fix the permissions on the man pages (bkearney@redhat.com)
- Clean up the icons in the makefile (bkearney@redhat.com)

* Fri Jan 28 2011 Chris Duryee (beav) <cduryee@redhat.com>
- Updating the application icon. (jharris@redhat.com)
- Adding CLI warning if registered to classic RHN. (jharris@redhat.com)
- Adding warning dialog if already registered to RHN. (jharris@redhat.com)
- 672965 next update time isn't localized (cduryee@redhat.com)
- Adding RHN classic registration check. (jharris@redhat.com)
- 672939: use re.compile for older pythons (jbowes@redhat.com)
- 672969: put the checkbox filter options in an expander (jbowes@redhat.com)
- 672939: Highlight search term in the main list and details
  (jbowes@redhat.com)
- 668572: search provided product names along with the main product
  (jbowes@redhat.com)
- I18N update. (dgoodwin@redhat.com)
- 672649 Proxy location has no handler to be read by automation
  (cduryee@redhat.com)
- Add in the new manpages (bkearney@redhat.com)
- 669753: set timestamps on .py files for multilib (jbowes@redhat.com)
- Compliance Screen should be called End Date. (bkearney@redhat.com)
- 672122: facts updating wasn't using consumer_uuid (alikins@redhat.com)
- 670655: remove addFrame method. Fix traceback on sub error dialog
  (alikins@redhat.com)
- 671526: Fixing GUI exception messages (jharris@redhat.com)
- 668796: Reducing the default size of most widgets to small screens.
  (jharris@redhat.com)
- 668572: Turn search filters into real filters (jbowes@redhat.com)
- 663756 exit calendar widget when you click outside cal box
  (cduryee@redhat.com)
- 670899: make contract selection screen larger by default (alikins@redhat.com)
- Fix "not yet installed" filter error. (dgoodwin@redhat.com)
- 670823: Remove reg tokens from the cli (bkearney@redhat.com)
- 668572: hide installed subscriptions from search results (jbowes@redhat.com)
- 670597: reload consumer in mainwindow after registration. (jesusr@redhat.com)
- 670885: Adding warning dialog on unsubscribe. (jharris@redhat.com)
- 670212 add a text box in addition to calendar widget (cduryee@redhat.com)
- 669753: use install -p to preserve py file timestamps (jbowes@redhat.com)
- 669513: Make sure we get fresh facts when we show the facts dialog.
  (alikins@redhat.com)
- Show the contract support and management attributes (jbowes@redhat.com)
- Making the tool buttons resize the parent container. (jharris@redhat.com)
- 669513: add a 'system.compliant' fact (alikins@redhat.com)
- Hiding activation button when not active and adding back click handler.
  (jharris@redhat.com)
- set default window size to 640x480 (jbowes@redhat.com)
- 668581: more changes to shrink the ui (jbowes@redhat.com)
- Ignoring network issues with activation button, defaulting to hide.
  (jharris@redhat.com)
- 668521: on unregistration, clear the list of available pools in the gui
  (alikins@redhat.com)
- 668048: Making calendar visible in all subs tab. (jharris@redhat.com)
- 668936: Raising exception if virt-what return code is non-zero.
  (jharris@redhat.com)
- 668796: Make the main window thinner (jbowes@redhat.com)
- 669395: default consumer name to hostname to match ui (alikins@redhat.com)
- 668054: center contract selection dialog (alikins@redhat.com)
- 669208: Fix for exception handler on register (alikins@redhat.com)
- 669208: JSONDecodeError doesn't exist on simplejson 2.0.9 (aka, RHEL6)
  (alikins@redhat.com)
- 667953: remove warning here about empty facts.json (alikins@redhat.com)
- 668032: Log all bundled products on subscription (alikins@redhat.com)
- 668814: break out 404 and 500s into a different error (cduryee@redhat.com)

* Wed Jan 12 2011 Devan Goodwin <dgoodwin@redhat.com> 0.93.11-1
- Resolves: #665122,#668058,#668051
- Config update. (dgoodwin@redhat.com)
- 665122: log to rhsm.log in the plugins with the new logger setup
  (jbowes@redhat.com)
- 665122: initialize logging once for the whole app (jbowes@redhat.com)
- 668058: Remove the fuel gage from the title bar (bkearney@redhat.com)
- 668051: Remove the start date column (bkearney@redhat.com)

* Fri Jan 07 2011 Devan Goodwin <dgoodwin@redhat.com> 0.93.10-1
- Resolves: #668006,#667953,#667788,#664779,#664775,#664581,#666942
- 668006: Error handling fixes. (dgoodwin@redhat.com)
- 667953: handle empty facts.json files (alikins@redhat.com)
- 667788: Fix contract selector total contracts count. (dgoodwin@redhat.com)
- 664779: hide the register/unregister buttons during firstboot
  (jbowes@redhat.com)
- 664779: move the tool button bar buttons to glade (jbowes@redhat.com)
- 664775: potential fix for proxy being ignored in firstboot
  (alikins@redhat.com)
- Moving compliance header up and making larger. (jharris@redhat.com)
- Overhauling the all subs tab per Paul's feedback. (jharris@redhat.com)
- Changing search button to 'Update' (jharris@redhat.com)
- Removing contract number from my subscriptions tab (jharris@redhat.com)
- Adding compliance info icon and text (jharris@redhat.com)
- More UXD tweaks to the compliance sidebar - primarily wording changes
  (jharris@redhat.com)
- Removing contract header from installed tab (jharris@redhat.com)
- Clean up the text a bit in the contract selection screen
  (bkearney@redhat.com)
- 664581: remove proxy options from clean a different way (alikins@redhat.com)
- 666942: Contract Selection page was using product id instead of the contract
  number (bkearney@redhat.com)

* Tue Jan 04 2011 Devan Goodwin <dgoodwin@redhat.com> 0.93.9-1
- Resolves: #664548,#664581
- rely on rhn-client-tools to handle entitlement selection (jbowes@redhat.com)
- firstboot: read up2date proxy settings (jbowes@redhat.com)
- firstboot: split firstboot into a seperate rpm (jbowes@redhat.com)
- 664548: Fix for some subcommands (refresh ) not using proxy info as well
  (alikins@redhat.com)
- 664581:  Removing proxy options for clean command (jharris@redhat.com)
- Removing header image per Paul's feedback and cleaning out unused images.
  (jharris@redhat.com)
- Manpage updates. (dgoodwin@redhat.com)
- Changing registration wording per Paul's input. (jharris@redhat.com)
- Reworking facts dialog and updating to display last update time.
  (jharris@redhat.com)
- gui: add a 'today' button to the calendar (jbowes@redhat.com)
- Show x of y available in compliance assistant. (dgoodwin@redhat.com)
- Shrink the compliance assistant. (dgoodwin@redhat.com)
- check the contains text box when text is entered (jbowes@redhat.com)
- Adding in spacing to compliance selection (jharris@redhat.com)
- Remove the references to Unified Entitlement Platform in the cli
  (bkearney@redhat.com)
- Allow the proxy window to be reopened after a close (jbowes@redhat.com)
- Expanding subscription view in installed tab (jharris@redhat.com)
- Getting rid of guidelines for facts dialog (jharris@redhat.com)
- Adding in accessible name for compliance status image. (jharris@redhat.com)

* Tue Dec 21 2010 Devan Goodwin <dgoodwin@redhat.com> 0.93.8-1
- Resolves: #663038
- Remove certificate.py (moved to python-rhsm package) (dgoodwin@redhat.com)
- Refactor top of compliance assistant. (dgoodwin@redhat.com)
- Make accessible names more consistent (jharris@redhat.com)
- 663038: No bundled products cases a divide by zero error
  (bkearney@redhat.com)
- Adding vertical pane to the all subs tab (jharris@redhat.com)
- Adding pane to installed products tab (jharris@redhat.com)
- Adding vertical pane to my subscriptions tab (jharris@redhat.com)

* Mon Dec 20 2010 Devan Goodwin <dgoodwin@redhat.com> 0.93.7-1
- Resolves: #664538

* Mon Dec 20 2010 Devan Goodwin <dgoodwin@redhat.com> 0.93.6-1
- More import fixes. (dgoodwin@redhat.com)
- New header graphic. (dgoodwin@redhat.com)
- Hiding next update when the value is not known. (jharris@redhat.com)

* Fri Dec 17 2010 Devan Goodwin <dgoodwin@redhat.com> 0.93.5-1
- Resolves: #663669,#659735,#659735,#661517,#661517,#662232,#661876,#661329,#661419
- Update I18N string bundles. (dgoodwin@redhat.com)
- firstboot: initialize the registerscreen superclass (jbowes@redhat.com)
- 639436: make --proxy help blurb more clear about format required
  (alikins@redhat.com)
- Adding in more accessibility labels (jharris@redhat.com)
- 663669: add proxy_user and proxy_password to default config
  (alikins@redhat.com)
- Adding in accessibility names for automation (jharris@redhat.com)
- Fixing update file to be in daemon loop (jharris@redhat.com)
- 659735: fix up dialog display for all cases (jbowes@redhat.com)
- 659735: display errors when the pulse bar is showing (jbowes@redhat.com)
- 661517: make sure changes to proxy settings are respected
  (alikins@redhat.com)
- Set and write out config values on network config screen close.
  (alikins@redhat.com)
- 661517: make network config dialog respect disabling of proxy settings
  (alikins@redhat.com)
- Changing update label to use dropfile with unix timestamp
  (jharris@redhat.com)
- gui: stop using global UEP during register (jbowes@redhat.com)
- 661542: update gui if registration state changes externally
  (alikins@redhat.com)
- 662232: remove "showIncompatiblePools" config option (alikins@redhat.com)
- 661876: fix a bug with cli not using config file proxy auth info
  (alikins@redhat.com)
- 661329: Only requiring registration if updating facts. (jharris@redhat.com)
- firstboot: fix display of compliance screen (jbowes@redhat.com)
- 661419: Adding modal dialog when running second GUI instance.
  (jharris@redhat.com)
- Remove python-rhsm sub-package. (dgoodwin@redhat.com)
- firstboot: get all but compliance to center on firstboot window
  (jbowes@redhat.com)
- Adding Next Update notification to main screen (jharris@redhat.com)
- firstboot: let the MainWindow know the sytem is registered
  (jbowes@redhat.com)
- firstboot: start using the new gui in firstboot (jbowes@redhat.com)
- firstboot: add proxy configuration button (jbowes@redhat.com)

* Wed Dec 08 2010 Devan Goodwin <dgoodwin@redhat.com> 0.93.3-1
- Resolves: #661345,#660102,#634254
- New Subscription Manager UI.
* Tue Nov 23 2010 Devan Goodwin <dgoodwin@redhat.com> 0.93.2-1
- Resolves: 654442,654435,654113,643931,645883,650965,654430,654429,648977,647891,649374
- I18N strings update. (dgoodwin@redhat.com)
- 654442: Record rpm package name in yum history (jbowes@redhat.com)
- 654435: Give the yum plugins better names (jbowes@redhat.com)
- make sure we show all noncompliant products (alikins@redhat.com)
- show installed but not compliant on compliance screen (alikins@redhat.com)
- Refactoring main window to use common widget and adding cert monitoring
  (jharris@redhat.com)
- Add tests for find last compliant date. (dgoodwin@redhat.com)
- add progressbar (jesusr@redhat.com)
- Hook up the subscriptions detail pane to the date (alikins@redhat.com)
- Check for expiration on entitlment certs not product certs.
  (alikins@redhat.com)
- allsubs: handle errors during bind (jbowes@redhat.com)
- refresh the all subs search results after a subscribe (jbowes@redhat.com)
- Allow for subscribing from the all subscriptions tab (jbowes@redhat.com)
- thread search results (jesusr@redhat.com)
- Fix compliance error comparing date/datetime. (dgoodwin@redhat.com)
- Error handling improvements. (dgoodwin@redhat.com)
- 654113: software license -> subscription (jesusr@redhat.com)
- s/day/day_entry to fix traceback (jesusr@redhat.com)
- add pulse() method (jesusr@redhat.com)
- BZ 643931 (jharris@redhat.com)
- Make all subs date selector match the compliance assistants.
  (dgoodwin@redhat.com)
- Minor error message touchup. (dgoodwin@redhat.com)
- 645883: repo_ca_cert in rhsm.conf should make use of ca_cert_dir
  (anadathu@redhat.com)
- Make the name subscription-manager instead of subscription-manager-cli
  (bkearney@redhat.com)
- Populate the subscriptions list based on products chosen (alikins@redhat.com)
- Add findAllByProduct method to EntitlementDir (alikins@redhat.com)
- BZ 650965 (jharris@redhat.com)
- Get  uncompliant list working (alikins@redhat.com)
- 654430: Calling register with no username or password should result in clear
  text (anadathu@redhat.com)
- 654429: when running facts/identity command, notify user when not registered.
  (anadathu@redhat.com)
- Uncomment overlapping filter. (dgoodwin@redhat.com)
- Add new UI support for unregistration. (dgoodwin@redhat.com)
- remove duplicate code in unregister method. (anadathu@redhat.com)
- Moving new ui to sm-gui (jharris@redhat.com)
- filter out installed products properly (jesusr@redhat.com)
- Prompt to register when trying to open compliance assistant.
  (dgoodwin@redhat.com)
- Display/hide all subs tab depending on registration status.
  (dgoodwin@redhat.com)
- Add registration callbacks. (dgoodwin@redhat.com)
- Add start of a contract selection window (jbowes@redhat.com)
- Fix a busted Makefile target. (dgoodwin@redhat.com)
- Allow overlapping pool filter to be skipped. (dgoodwin@redhat.com)
- Moving cert monitoring to the backend object (jharris@redhat.com)
- Fixing bugs around subscription display and adding some ui tweaks
  (jharris@redhat.com)
- Fix overlapping option in compliance assistant. (dgoodwin@redhat.com)
- Hookup date selector in compliance assistant. (dgoodwin@redhat.com)
- stop subscription manager from deleting entitlement certificates without
  product information (anadathu@redhat.com)
- list from entitlements, not products, for overlap (jbowes@redhat.com)
- Add a filter for overlapping subscriptions (jbowes@redhat.com)
- Adding status icon to product column (jharris@redhat.com)
- Allow compliance assistant to be used more than once per run.
  (dgoodwin@redhat.com)
- Adding product directory monitoring in installed tab (jharris@redhat.com)
- Add sub details to compliance assistant. (dgoodwin@redhat.com)
- Fix for server side provided product changes. (dgoodwin@redhat.com)
  manager (alikins@redhat.com)
- add a toggle button to the product list on compliance page
  (alikins@redhat.com)
- Figure out what products to display in the out of compliance product list
  (alikins@redhat.com)
- Make compliance date filter widget comply with mockup (alikins@redhat.com)
- Make the compliance label use actual date (alikins@redhat.com)
- Ensured that the cli prints out products which have been autosubscribed
  (bkearney@redhat.com)
- add a "install-file" and "install-conf" targets (alikins@redhat.com)
- Introducing MappedListStore and adding installed table headers
  (jharris@redhat.com)
- Hookup compliance assistant button. (dgoodwin@redhat.com)
- 648977: Changed the tool tip to be more specific (bkearney@redhat.com)
- 647891: Add consumer name to the output (bkearney@redhat.com)
- Refactor All Subs to better match wireframe spec. (dgoodwin@redhat.com)
- gui: show account number for subscriptions (jbowes@redhat.com)
- cli: show account number during 'list' (jbowes@redhat.com)
- fix up some whitespace alignment in constants (jbowes@redhat.com)
- add syslogging of adding and removing subscriptions (bkearney@redhat.com)
- Getting all the headers in order (jharris@redhat.com)
- Adding documentation and refactoring mysubs table (jharris@redhat.com)
- Use new server-side date filtering. (dgoodwin@redhat.com)
- gui: Remove unused broken import (jbowes@redhat.com)
- Add syslogging of register and unregister (bkearney@redhat.com)
- Refactoring common widgets into a widgets module (jharris@redhat.com)
- 649374: Make the ssl verify depth configurable (bkearney@redhat.com)

* Wed Nov 03 2010 Devan Goodwin <dgoodwin@redhat.com> 0.93.1-1
- Update I18N strings. (dgoodwin@redhat.com)
- Pulling out contract info in 'All Subscriptions' tab (jharris@redhat.com)
- 648947: update certs and config for stage env (jbowes@redhat.com)
- Fixing up facts test (jharris@redhat.com)
- 647855: subscription update button doesn't work, remove it
  (alikins@redhat.com)
- Adding working logic around subscription date coloring (jharris@redhat.com)
- 646565: Don't load key.pem as an entitlement cert (jbowes@redhat.com)
- Make the facts a tree view (bkearney@redhat.com)
- Ensure that autosubscribe is called from the cli, and exceptions are logged
  (bkearney@redhat.com)
- Display bundled product names in details for all subs tab.
  (dgoodwin@redhat.com)
- Hookup all subs display of provided products. (dgoodwin@redhat.com)
- 647410: handle error on unbindBySerial call in ui (don't reraise)
  (alikins@redhat.com)
- Adding first pass at date-based subscription coloring (jharris@redhat.com)
- 646451: Handle network outages on the add subscription screen
  (alikins@redhat.com)
- Tweaking subscription table renderering options (grid lines, centering)
  (jharris@redhat.com)
- Filter pools in memory. (dgoodwin@redhat.com)
- Stash pool results in the all subs tab. (dgoodwin@redhat.com)
- Pulling out the Renew button from My Subscriptions (jharris@redhat.com)
- Adding renew button back to My Subscriptions tab (jharris@redhat.com)
- Lots of glade cleanup and tweaks. (jharris@redhat.com)
- Adding in none check for tree_iter to get rid of initial traceback
  (jharris@redhat.com)
- Removing hardware column and making products table functional.
  (jharris@redhat.com)
- Remove unecessary call to server after GUI bind. (dgoodwin@redhat.com)
- Touchups for compliance status width/wrapping. (dgoodwin@redhat.com)
- Calculate and display products out of compliance status.
  (dgoodwin@redhat.com)
- Hookup All Subs tab to the subscription details below. (dgoodwin@redhat.com)
- Break subscription details out into a class. (dgoodwin@redhat.com)
- Getting rid of duplicate date formatting method (jharris@redhat.com)
- Adding products table layout - currently showing dummy data
  (jharris@redhat.com)
- 646431: Fix missing refresh for add screen. (dgoodwin@redhat.com)
- 646916: Enable the plugin by default (bkearney@redhat.com)
- 646557: remove extraneous "user service" in the selector (alikins@redhat.com)
- Fixing bug in percentage calculation of installed products
  (jharris@redhat.com)
- Rendering installed products as a progress bar (jharris@redhat.com)
- Hookup View Facts button. (dgoodwin@redhat.com)
- Enable Registration Settings button. (dgoodwin@redhat.com)
- Add new UI sidebar. (dgoodwin@redhat.com)
- Refactoring how to obtain widget refs (jharris@redhat.com)
- More All Subs tab UI touchups. (dgoodwin@redhat.com)
- Set new UI main window size to 1024x768. (dgoodwin@redhat.com)
- All Subs tab UI touchups. (dgoodwin@redhat.com)
- Set all subs date selector to current date by default. (dgoodwin@redhat.com)
- Hookup all subs date filtering. (dgoodwin@redhat.com)
- Enable active on date selection UI components. (dgoodwin@redhat.com)
- Adding in selection listener to update mysubs info (jharris@redhat.com)
- 64431 Man page updates (bkearney@redhat.com)
- 645347: Long usernames caused httpd server to reject the request.
  (bkearney@redhat.com)
- 640463: Update the oids in the order namespace (bkearney@redhat.com)
- 645115: clean up the location of the entitlement certificates
  (bkearney@redhat.com)
- 645378: do not allow empty system names on registration (alikins@redhat.com)
- 645372: better logging during a force register to say what is going on
  (bkearney@redhat.com)
- Latest man page from Deon. This is version 49774 (bkearney@redhat.com)
- 643027: Use the new bind by product API (jbowes@redhat.com)
- Moving out renew button and adding a little polish (jharris@redhat.com)
- Hookup uninstalled/name filtering in new UI. (dgoodwin@redhat.com)
- Add helper for filtering a list of pools. (dgoodwin@redhat.com)
- Hookup pool list on all subscriptions tab. (dgoodwin@redhat.com)
- Calculate 'merged' pool data. (dgoodwin@redhat.com)
- cleanup rhsm.conf a bit, make everything of form "a = b" (alikins@redhat.com)
- 617662: Add a config value for the default yum repo ca cert location
  (jbowes@redhat.com)
- Moving 'My Subscriptions' page to look at entitlement certs (whoops!)
  (jharris@redhat.com)
- Force local cleanup if GUI unregister fails. (dgoodwin@redhat.com)
- Fix bad i18n calls. (dgoodwin@redhat.com)
- Fix my subs tab. (dgoodwin@redhat.com)
- Remove global facts object. (dgoodwin@redhat.com)
- Begin using mocks in tests. (dgoodwin@redhat.com)
- 613709: Munge product labels so we always have a valid repo id
  (jbowes@redhat.com)
- Remove use of 'consumer' global in GUI. (dgoodwin@redhat.com)
- Fix monkey-patching test error. (dgoodwin@redhat.com)
- Switch to webqa in default rhsm.conf. (dgoodwin@redhat.com)
- Add All Subs search button. (dgoodwin@redhat.com)
- Enable the 'contains text' UI widgets. (dgoodwin@redhat.com)
- Adding several additions to 'My Subscriptions' page. (jharris@redhat.com)
- 627962: Fix issue with cpu.cpu_mhz causing facts to always update
  (alikins@redhat.com)
- 642705: destroy icon wen compliant (jesusr@redhat.com)
- 643402: update the gui after a manual cert import (jbowes@redhat.com)
- 642705: destroy icon when compliant (jesusr@redhat.com)
- Wildcard GNOME files in spec. (dgoodwin@redhat.com)
- Pass data between new main window and tab classes. (dgoodwin@redhat.com)
- 642997: split RHN or RHN sat option into two choices (alikins@redhat.com)
- 642997: split RHN or RHN sat option into two choices (alikins@redhat.com)
- 642661: Fix registration status during firstboot (alikins@redhat.com)
- 642661: Fix registration status during firstboot (alikins@redhat.com)
- 643054: Add in the latest man page. (bkearney@redhat.com)
- 643054: Add in the latest man page. (bkearney@redhat.com)
- Dynamically loading subscriptoin tabs. (jharris@redhat.com)
- Hookup signals for all subs filter checkboxes. (dgoodwin@redhat.com)
- Refactor all subs tab into separate class. (dgoodwin@redhat.com)
- Get all subs treeview operational. (dgoodwin@redhat.com)
- Mockup "all subscriptions" tab. (dgoodwin@redhat.com)
- Wildcard glade files in spec. (dgoodwin@redhat.com)
- Skeleton code for new UI. (dgoodwin@redhat.com)
- Reversion alpha branch, next tag 0.92.1 (dgoodwin@redhat.com)
- Reversion for beta, next tag will go to 0.93.1. (dgoodwin@redhat.com)

* Wed Oct 13 2010 Devan Goodwin <dgoodwin@redhat.com> 0.92-1
- Resolves: #641037,#641448,#641479,#641502
- Update I18N strings. (dgoodwin@redhat.com)
- Add helper for quantity used OID extension. (dgoodwin@redhat.com)
- Add string substituion parameter to UNREGISTER_ERROR. (anadathu@redhat.com)
- 641037:  Skipping past RHSM screens when selecting 'Do not register'
  (jharris@redhat.com)
- 641037:  Skipping Entitlement choice screen in firstboot if network is
  not avaiable (jharris@redhat.com)
- 641448: invalid error message on SSL failure(s) (anadathu@redhat.com)
- 641479: users should be informed of invalid certs from candlepin.
  (anadathu@redhat.com)
- Skipping entitlement selection page if id cert exists (jharris@redhat.com)
- Reload subscriptions on changes. (anadathu@redhat.com)
- 641502: Add the options prepend to the description (bkearney@redhat.com)

* Fri Oct 08 2010 Devan Goodwin <dgoodwin@redhat.com> 0.91-1
- Resolves: #641040,#633814,#632570,#631472
- Display buttons on main screen dynamically. (dgoodwin@redhat.com)
- Adjust firstboot screen priorities. (dgoodwin@redhat.com)
- No network required for firstboot entitlement chooser. (dgoodwin@redhat.com)
- remove the content portion from the fakamai url (bkearney@redhat.com)
- Pull down the latest code if you autosubscribe, or register as an existing
  consumer (bkearney@redhat.com)
- Add a 'refresh' command which will pull down the latest entitlement data
  (bkearney@redhat.com)
- Add a clean command. (bkearney@redhat.com)
- Add configuration and certificate for the dev environment
  (bkearney@redhat.com)
- Make the cfg check work for show compatible screen (bkearney@redhat.com)
- 633814: fix 'Compliance icon not refreshed' (anadathu@redhat.com)
- 632570: alignment issues with product description text (anadathu@redhat.com)
- 631472: Using close button in update screen breaks GUI (anadathu@redhat.com)

* Thu Oct 07 2010 Devan Goodwin <dgoodwin@redhat.com> 0.90-1
- Resolves: #641082,#640338
- 641082: Fix double call to Path.abs. (dgoodwin@redhat.com)
- 640338: subscribe is occasionally dropping duplicate entitlement certs
  (anadathu@redhat.com)

* Thu Oct 07 2010 Devan Goodwin <dgoodwin@redhat.com> 0.89-1
- Resolves: #640980

* Thu Oct 07 2010 Devan Goodwin <dgoodwin@redhat.com> 0.88-1
- Resolves: #638696,#585193
- Fix broken directory path joining. (dgoodwin@redhat.com)
- Display error messages sent from the server on entitlement bind
  (jbowes@redhat.com)
- Update the config name for the ca cert dir to ca_cert_dir (jbowes@redhat.com)
- clean up a gtk warning about the bad button group (alikins@redhat.com)
- 638696: bugfix 'cli fails silently with wrong server SSL cert'
  (anadathu@redhat.com)
- unregister should delete identity certs if candlepin call is successfull.
  (anadathu@redhat.com)
- some glade reference renaming s/treeview_2/treeview_matching, etc
  (alikins@redhat.com)
- refactor the populate*Subscriptions methods. (alikins@redhat.com)
- 585193: refractor error handling code. (anadathu@redhat.com)


* Tue Oct 05 2010 Devan Goodwin <dgoodwin@redhat.com> 0.84-1
- Resolves: #632612,#640128,#639320,#639491,#637160,#638289
- When re-registering, previously subscribed-to subscriptions are checked
  by default) (alikins@redhat.com)
- update CA trust chain (jbowes@redhat.com)
- Write identity cert with correct permissions initially. (dgoodwin@redhat.com)
- Check and fix identity cert permissions on every run. (dgoodwin@redhat.com)
- Type in the identity command (bkearney@redhat.com)
- fix for bz#639320 (anadathu@redhat.com)
- Fix segfault when adding subs during firstboot. (dgoodwin@redhat.com)
- 639491: Put register by consumer back in (bkearney@redhat.com)
- Moving re-register to be identity. (bkearney@redhat.com)
- Get firstboot displaying the right subscription screen. (dgoodwin@redhat.com)
- Fix separate subscription window in firstboot. (dgoodwin@redhat.com)
- 637160 - require --all to unsubscribe to unsub all (jbowes@redhat.com)
- merge getAllAvailableSubscriptions and getAvailableEntitlements
  (jbowes@redhat.com)
- getAvailableEntitlementsCLI isn't needed, just call the regular version
  (jbowes@redhat.com)
- remove some code duplication for getting available entitlements/subscriptions
  (jbowes@redhat.com)
- remove unneeded wrapper method (jbowes@redhat.com)
- Move registration status on main UI page. (dgoodwin@redhat.com)
- Handle errors during unregistration. (dgoodwin@redhat.com)
- Add "Activate Subscription" button. (dgoodwin@redhat.com)
- Add unregister button to main screen. (dgoodwin@redhat.com)
- Display UUID on main page of the GUI. (dgoodwin@redhat.com)
- 638289: Fix broken re-register if identity cert doesn't exist.
  (dgoodwin@redhat.com)
- Fix broken list all subscriptions. (dgoodwin@redhat.com)
- Update registration screen to match new mockups. (dgoodwin@redhat.com)
- remove some unused imports (jbowes@redhat.com)
- Add missing imports (jbowes@redhat.com)
- Split registration screens into separate glade files. (dgoodwin@redhat.com)
- Remove duplicate log initialization in connection.py (jbowes@redhat.com)
- Ship the CA chain (jbowes@redhat.com)
- Load CA trust chains from a directory of pem formatted files
  (jbowes@redhat.com)

* Tue Sep 28 2010 Devan Goodwin <dgoodwin@redhat.com> 0.83-1
- Resolves: #617685
- Cleanup authentication logic. (dgoodwin@redhat.com)
- Split out REST lib into seprate rpm. (dgoodwin@redhat.com)
- config: define defaults in the config module (jbowes@redhat.com)
- Start of glade name cleanup. Make glade names per top level.
  (alikins@redhat.com)
- Initial work in adding facts dialog. (jharris@redhat.com)
- Line length fixups in the firstboot module (jbowes@redhat.com)
- 617685: Ensure that the baseurl works with and without trailing slashes.
  (bkearney@redhat.com)
- Use config file for directories to use. (dgoodwin@redhat.com)
- Specify default cert location in default config. (dgoodwin@redhat.com)
- Fix insecure setting comparison. (dgoodwin@redhat.com)
- Refactor to use Python ConfigParser. (dgoodwin@redhat.com)
- Fallback to console logging if we cannot write to /var/log.
  (dgoodwin@redhat.com)

* Wed Sep 22 2010 Devan Goodwin <dgoodwin@redhat.com> 0.80-1
- Resolves: #628589
- Updated I18N strings. (dgoodwin@redhat.com)
- added username & password check for reregister with --consumerid option
  command (dmitri@redhat.com)
- Fix bad translation. (dgoodwin@redhat.com)
- fix for #628589 -removed --consumerid option from register command
  (dmitri@redhat.com)
- 623264: Fix multiple issues with registration. (dgoodwin@redhat.com)

* Tue Sep 21 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.79-1
- Resolves: #631472
- update these screens priorities so we show the management screen first to
  simplify the flow (alikins@redhat.com)
- Have the UEP Connection read the values from the local config file
  (bkearney@redhat.com)
- escape the product name in unsubscribe confirm dialog. (alikins@redhat.com)
- return True from delete_event handlers. fix bz#631472 (alikins@redhat.com)
- 635844:If there is a colossal failure, and no json is returned.. then assume
  it is a network erorr and provide a generic response (bkearney@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- Change the name of the entitlement chooser module to a more vibrant and
  impressive name as to better establish our brand and mark in a challenging
  marketplace. (alikins@redhat.com)

* Tue Sep 21 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.78-1
- Resolves: #631537, #633514
- Only escape strings that need it (aka, product name for now) instead of all
  strings sent to the messageWindow. Escaping all of them broke the formating.
  (alikins@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- change packing on register/close buttons so they display correctly in
  firstboot (alikins@redhat.com)
- Catch locale errors (bkearney@redhat.com)
- Move close button in the subscription token/modify subscription dialog
  (alikins@redhat.com)
- change paths for firstboot modules (alikins@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- Escape text passed to gtk's text markup. (alikins@redhat.com)
- 623448: Added the new config options to the example config file
  (bkearney@redhat.com)
- 596136 ensure that the daemon only runs one time (jbowes@redhat.com)
- Fix up some spec file issues with the local being double listed and the first
  boot stuff not being included (bkearney@redhat.com)
- bugfix for bz#631537 (anadathu@redhat.com)
- rename files firstboot modules (alikins@redhat.com)
- Add an option on the entitlement choose screen for "local"
  (alikins@redhat.com)
- bugfix for bz#633514 (anadathu@redhat.com)
- Change rhms screen priority to match those of rhn. (alikins@redhat.com)
- add chooser screen (alikins@redhat.com)
- start of adding a rhn or rhesus screen (alikins@redhat.com)
- Fix missing gettext import. (dgoodwin@redhat.com)
- fixed a problem with prefix config (dmitri@redhat.com)
- made '/candlepin' prefix configurable as 'prefix' configuration file
  parameter (dmitri@redhat.com)
- Merge branch 'i18n' (dgoodwin@redhat.com)
- Remove the translations used for testing. (dgoodwin@redhat.com)
- Deploy translations to /usr/share/locale/. (dgoodwin@redhat.com)
- Add po/build to gitignore (jbowes@redhat.com)
- Make a seperate update-po makefile target (jbowes@redhat.com)
- glob po files for compile_pos (jbowes@redhat.com)
- Add a menu icon for subscription-manager (bkearney@redhat.com)
- Minor strings update. (dgoodwin@redhat.com)
- Safer generation of glade.h string files. (dgoodwin@redhat.com)
- Add missing translation markers in Python code. (dgoodwin@redhat.com)
- Remove bad glade translatable markers. (dgoodwin@redhat.com)
- We need to import certlib after setting path in include rhsm
  (alikins@redhat.com)
- I18N for compliance icon. (dgoodwin@redhat.com)
- Include Glade strings for translation. (dgoodwin@redhat.com)
- Enable I18N in subscription manager itself. (dgoodwin@redhat.com)
- Compile .po files during install. (dgoodwin@redhat.com)
- Remove (most of) HATEOAS. (dgoodwin@redhat.com)
- 608005: checking for bad html characters on the client (bkearney@redhat.com)
- Handle window manager delete_entry signals. fix bz#631472
  (alikins@redhat.com)
- fix for bz#628070 Do not try to unsubscribe from the server for local
  management (alikins@redhat.com)
- 632019: Remove hyphen from re-register (bkearney@redhat.com)
- 613650: Improved the text a bit (bkearney@redhat.com)
- 632019: Clean up typo in the help message (bkearney@redhat.com)
- Add make target to extract strings for i18n. (dgoodwin@redhat.com)
- bugfix for bz#617703 (anadathu@redhat.com)

* Mon Sep 20 2010 Adrian Likins <alikins@redhat.com>
- names on firstboot modules changed

* Thu Sep 09 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.77-1
- Resolves: #627915
- Update for Candlepin HATEOAS changes. (dgoodwin@redhat.com)
- Comment out logging response from server. bz#627915 (anadathu@redhat.com)

* Wed Sep 08 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.76-1
Resolves: #627681, #616137, #618819, #627707
- bugfix for bz#627681 (anadathu@redhat.com)
- compliance-icon: support warning period notification (jbowes@redhat.com)
- bugfix for bz#618819 (anadathu@redhat.com)
- fix for bz#616137 (anadathu@redhat.com)
- Fix broken exception handling. (dgoodwin@redhat.com)
- Use the write method name when saving facts. fix bz#628679
  (alikins@redhat.com)
- fix for bz#585193 (anadathu@redhat.com)
- Fix  bz #627707 - facts cache not being updated for "update facts now" button
  if the facts file is deleted under it (alikins@redhat.com)
- add /etc/rhsm/facts to makefile (alikins@redhat.com)
- add /etc/rhsm/facts to spec file (alikins@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- 624106 - handle the consumerid properly (jesusr@redhat.com)
- 624106 - add consumerid param to reregister. (jesusr@redhat.com)
- fix for bz#609126 (anadathu@redhat.com)
- bugzilla fix#601848 (anadathu@redhat.com)
- 624816 - unlimited flag unavailable, check quantity for -1.
  (jesusr@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- Change the firstboot ordering (alikins@redhat.com)
- Missing config options for insecure options and ca certs.
  (pkilambi@redhat.com)
- bugfix/enhancement for bugzilla#597210 (anadathu@redhat.com)
- BZ624794: Start using basic auth (bkearney@redhat.com)
- date format did not change. reverting it back to original
  (anadathu@redhat.com)
- Fix format string and added logging to detect failures when running cert-
  daemon (anadathu@redhat.com)
- add user certs in all the places it makes sense (alikins@redhat.com)
- add user/cert based auth for unregister as well. fix bz#624025
  (alikins@redhat.com)
- Remove debug "raise" that was breaking some of the error handling
  (alikins@redhat.com)
- Try to only create the UEP once, and add ssl certs to it when we get them
  (alikins@redhat.com)
- move around where we init the connection object (alikins@redhat.com)
- add my favorite "trace_me" helper method that dumps the stack of where it is
  called from to logutil.py. (alikins@redhat.com)

* Wed Aug 11 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.75-1
- Resolves: #622839, #612250
- get rid of stray print debug (jbowes@redhat.com)
- missed an instance of create_connection_with_userIdentity
  (alikins@redhat.com)
- remove unneeded printing of consumer id bz#622839 (alikins@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- implement entitlement grace periods (jbowes@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- Adding some firstboot niceties for registration. (jharris@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- Somewhat rough fix for BZ #612250 (jharris@redhat.com)
- Add back some missing atk strings (alikins@redhat.com)
- remove the executable bit from productid.py (jbowes@redhat.com)
- Add bin to gitignore (jbowes@redhat.com)
- Remove unused 'test' file (from repo check) (jbowes@redhat.com)
- s/create_connection_with_userIdentity/create_connection_with_userIdentity
  (alikins@redhat.com)
- remove reference to non existent variable (alikins@redhat.com)
- More moving of ImportCertificate screen dialog around (alikins@redhat.com)
- refactor ImportCertificate screen a bit. (alikins@redhat.com)
- more refactoring (alikins@redhat.com)
- refactor AddSubscriptionScreen.init to be slightly less indented
  (alikins@redhat.com)
- remove unused imports cleanup indention (alikins@redhat.com)
- remove unused "os" import (alikins@redhat.com)
- indention cleanup pylint cleanups (alikins@redhat.com)
- unused variable removed pychecker cleanups (alikins@redhat.com)
- import os here pychecker fix (alikins@redhat.com)
- BZ615357: Can now pass in --all if you are doing list --available
  (root@localhost.localdomain)
- BZ615404 changed the name (bkearney@redhat.com)

* Tue Aug 03 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.74-1
- Resolves: #614015, #613635, #612730
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager (alikins@redhat.com)
- compliance-icon: fix up right click handling (jbowes@redhat.com)
- compliance-icon: call notify_init for older distros (jbowes@redhat.com)
- make add subscriptions dialog a singleton (alikins@redhat.com)
- Making register screen and regtoken screen singletons. (jharris@redhat.com)
- Getting the firstboot screens working again with the common glade file.
  (jharris@redhat.com)
-     Refactoring managergui to use signals for consumer updates.
  (jharris@redhat.com)
- Make the progress dialog for subscribing to channels a little better.
  (alikins@redhat.com)
- Change getMatchedSubscriptions to uniq the list of products based on pool id.
  (alikins@redhat.com)
- Moving firstboot regsiter screen to use common network init method.
  (jharris@redhat.com)
- Tweaking the registration screen. (jharris@redhat.com)
- remove unwanted print statement (anadathu@redhat.com)
- unregister functionality implemented (anadathu@redhat.com)
- Make RegisterScreen run as a dialog (alikins@redhat.com)
- remove redundant connection method (jesusr@redhat.com)
- register client if consumer cert doesn't exist (jesusr@redhat.com)
- fix typo (jesusr@redhat.com)
- remove --regen option from facts, use the reregister command
  (jesusr@redhat.com)
- add reregister command (jesusr@redhat.com)
- add rhms_subscriptions module to spec (alikins@redhat.com)
- remove debug spew (alikins@redhat.com)
- Turn subscriptionToken/status/factupdate/kitchen sink screen back on
  (alikins@redhat.com)
- Several small UI tweaks to register screen. (jharris@redhat.com)
- turn on "subscriptionTokenScreen" again (alikins@redhat.com)
- change the add subscription dialog to "run" so we don't block in it's main
  loop. (alikins@redhat.com)
- refactoring to make firstboot gui work (alikins@redhat.com)
- Merge branch 'firstboot' of git+ssh://axiom.rdu.redhat.com/scm/git
  /subscription-manager into firstboot (alikins@redhat.com)
- abstract more rhsm gui stuff so we can redefine them in firstboot
  (alikins@redhat.com)
- Basically adding documentation. (jharris@redhat.com)
- Merge branch 'firstboot' of git+ssh://axiom.rdu.redhat.com/scm/git
  /subscription-manager into firstboot (alikins@redhat.com)
- Merge branch 'master' of git+ssh://axiom.rdu.redhat.com/scm/git/subscription-
  manager into firstboot (alikins@redhat.com)
- bugfix for connection not using usr credentials after registration.
  (anadathu@redhat.com)
- remove unused code (alikins@redhat.com)
- Merging in master and doing further work on register screen.
  (jharris@redhat.com)
- Getting the basics of the register screen in and working.
  (jharris@redhat.com)
- add the main "rhms_subscriptions" screen. (alikins@redhat.com)
- Disarm "reload" since it causes firstboot ui to freak out.
  (alikins@redhat.com)
- s/rhms_module/rhms_login (alikins@redhat.com)
- reenabled installing rhsm.conf. (alikins@redhat.com)
- create firstboot dirs in make install (alikins@redhat.com)
- add rhms firstboot module to repo (alikins@redhat.com)
- add firstboot modules to spec (alikins@redhat.com)
- install the firstboot modules in make install (alikins@redhat.com)
- Changes to make this module also work as a firstboot screen.
  (alikins@redhat.com)
- force the symlink to console helper. Do not install the config file on make
  install. (alikins@redhat.com)
- Merging in master and doing further work on register screen.
  (jharris@redhat.com)
- insecure mode option moved to rhsm.conf file (anadathu@redhat.com)
- Getting the basics of the register screen in and working.
  (jharris@redhat.com)
- add the main "rhms_subscriptions" screen. (alikins@redhat.com)
- Disarm "reload" since it causes firstboot ui to freak out.
  (alikins@redhat.com)
- s/rhms_module/rhms_login (alikins@redhat.com)
- reenabled installing rhsm.conf. (alikins@redhat.com)
- create firstboot dirs in make install (alikins@redhat.com)
- add rhms firstboot module to repo (alikins@redhat.com)
- add firstboot modules to spec (alikins@redhat.com)
- install the firstboot modules in make install (alikins@redhat.com)
- Changes to make this module also work as a firstboot screen.
  (alikins@redhat.com)
- force the symlink to console helper. Do not install the config file on make
  install. (alikins@redhat.com)
- Create /var/lib/rhsm/facts if it doesn't exist. Fix for bz#613003
  (alikins@redhat.com)
- Always push the facts up if users click "update facts" even if we don't think
  there has been a change. (adrian@alikins.usersys.redhat.com)
- Add a "update facts" button the the "modify registration" screen.
  (adrian@alikins.usersys.redhat.com)
- Merge branch 'master' of git://axiom.rdu.redhat.com/scm/git/subscription-
  manager (adrian@alikins.usersys.redhat.com)
- add "facts --list" and "facts --update" to cli
  (adrian@alikins.usersys.redhat.com)
- add factlib.py to repo (adrian@alikins.usersys.redhat.com)
- Swap OrderNumber and SerialNumber fields for formatting in list --consumed
  (adrian@alikins.usersys.redhat.com)

* Fri Jul 30 2010 Adrian Likins <alikins@redhat.com> 0.74-1
- add rhms_subscriptions firstboot module

* Tue Jul 27 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.73-1
- Resolves: #614015, #613635, #612730
- remove prints, use proper method name (jesusr@redhat.com)
- store the cert (jesusr@redhat.com)
- adding regen identity certs to client (jesusr@redhat.com)
- moving importing of logutils after PYTHONPATH is set (pkilambi@redhat.com)
- fix for bugzilla#607162 (anadathu@redhat.com)
- bugfix for 'connection.UEPConnection' instance. (anadathu@redhat.com)
- renaming the main subscription-manager-gui glade as rhsm
  (pkilambi@redhat.com)
- Show and accept consumer names via the gui (bkearney@redhat.com)
- Show the name in the register page (bkearney@redhat.com)
- Removed setters. Multiple connections not spawned for every execution.
  (anadathu@redhat.com)
- BZ616065: Allow a name to passed into the register command
  (bkearney@redhat.com)
- added exception logging and fix for one bug. (anadathu@redhat.com)
- 614015 - fixing name mismatches (pkilambi@redhat.com)
- 613635 - remove printing cp instance (pkilambi@redhat.com)
- 612730 - fixing typo (pkilambi@redhat.com)
- display error when unregister fails (pkilambi@redhat.com)

* Thu Jul 22 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.72-1
- Resolves: #617303
- BZ613650: Clean up the help text (root@localhost.localdomain)
- Make insecure by default for testing purposes. (anadathu@redhat.com)

* Wed Jul 21 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.71-1
- Resolves: #613003
- Make subscription-manager-gui run as root (jbowes@redhat.com)
- Pass the UUID in the subject, and name in the subjectAlternateName
  (bkearney@redhat.com)
- hook up consolehelper for subscription-manager-gui (jbowes@redhat.com)
- Add compliance notification syslogging/desktop icon (jbowes@redhat.com)
- Make candlepin_ca_file an instance variable (root@localhost.localdomain)
- subscription-manager now checks server's certificate before performing
  further commands (anadathu@redhat.com)
- From: Adrian Likins <alikins@redhat.com> Date: Mon, 12 Jul 2010 15:23:59
  -0400 Subject: [PATCH 7/7] Don't try to use any existing consumer certs for
  registration (anadathu@redhat.com)
- Need to add pidplugin.conf to Makefile. (jortel@redhat.com)
- Daemon not started at install; pidplugin disabled. As per fedora packaging
  guidelines, the rhsm daemon is not started during rpm install.
  (jortel@redhat.com)
- Add product ID (yum) plugin conf. (jortel@redhat.com)
- Add support for alternate root directories. Change the root dir to
  /mnt/sysimage when it exists to support running the product id plugin within
  an Anaconda install. (jortel@redhat.com)
- Add productid plugin. (jortel@redhat.com)
- Remove unnecessary import. (jortel@redhat.com)
- Removing bind by product name. Use pool or reg-token to do future binds
  (pkilambi@redhat.com)

*Wed Jul 21 2010 Adrian Likins <alikins@redhat.com> 0.69-1
- add firstboot modules

* Fri Jul 09 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.68-1
- Resolves: #613003
- putting back accessibility strings overridden by facts commit
  (pkilambi@redhat.com)

* Fri Jul 09 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.67-1
- Resolves: #613003
- Create /var/lib/rhsm/facts if it doesn't exist. Fix for bz#613003
  (alikins@redhat.com)
- New button in gui for refreshing facts - alikins (pkilambi@redhat.com)
- Adding the facts lib (pkilambi@redhat.com)
- First pass at support for supporting updating facts for subscription-manager.
  (pkilambi@redhat.com)
- subscribing to a regnumber was failing (bkearney@redhat.com)

* Thu Jun 24 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.66-1
- Resolves: #589626
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

