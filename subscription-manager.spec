# Skip rhsm-icon on Fedora 15+ and RHEL 7+
%define use_rhsm_icon (0%{?fedora} && 0%{?fedora} < 15) || (0%{?rhel} && 0%{?rhel} < 7)

# A couple files are for RHEL 5 only:
%if 0%{?rhel} == 5
%define el5 1
%endif

Name: subscription-manager
Version: 1.0.2
Release: 1%{?dist}
Summary: Tools and libraries for subscription and repository management
Group:   System Environment/Base
License: GPLv2

# How to create the source tarball:
#
# git clone git://git.fedorahosted.org/git/subscription-manager.git/
# yum install tito
# tito build --tag subscription-manager-%{version}-%{release} --tgz
Source0: %{name}-%{version}.tar.gz
URL:     https://fedorahosted.org/subscription-manager/
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:  python-ethtool
Requires:  python-simplejson
Requires:  python-iniparse
Requires:  PyXML
Requires:  virt-what
Requires:  python-rhsm >= 1.0.1
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
BuildRequires: GConf2-devel


%description
The Subscription Manager package provides programs and libraries to allow users
to manage subscriptions and yum repositories from the Red Hat entitlement
platform.


%package -n subscription-manager-gui
Summary: A GUI interface to manage Red Hat product subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}
Requires: pygtk2 pygtk2-libglade gnome-python2 gnome-python2-canvas
Requires: usermode
Requires: usermode-gtk
Requires: dbus-x11
Requires(post): scrollkeeper
Requires(postun): scrollkeeper

# Renamed from -gnome, so obsolete it properly
Obsoletes: %{name}-gnome < %{version}-%{release}
Provides %{name}-gnome = %{version}-%{release}

# Fedora can figure this out automatically, but RHEL cannot:
Requires: librsvg2

%description -n subscription-manager-gui
This package contains a GTK+ graphical interface for configuring and
registering a system with a Red Hat Entitlement platform and manage
subscriptions.

%package -n subscription-manager-firstboot
Summary: Firstboot screens for subscription manager
Group: System Environment/Base
Requires: %{name}-gui = %{version}-%{release}
%{?el5:Requires: rhn-setup-gnome >= 0.4.20-49}
%{?el6:Requires: rhn-setup-gnome >= 1.0.0-82}

# Fedora can figure this out automatically, but RHEL cannot:
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
rm -rf %{buildroot}
make -f Makefile install VERSION=%{version}-%{release} PREFIX=%{buildroot} MANPATH=%{_mandir}

%if %use_rhsm_icon
desktop-file-validate \
        %{buildroot}/etc/xdg/autostart/rhsm-icon.desktop
%endif

desktop-file-validate \
        %{buildroot}/usr/share/applications/subscription-manager.desktop
%find_lang rhsm

# fix timestamps on our byte compiled files so them match across arches
find %{buildroot} -name \*.py -exec touch -r %{SOURCE0} '{}' \;

# fake out the redhat.repo file
mkdir %{buildroot}%{_sysconfdir}/yum.repos.d
touch %{buildroot}%{_sysconfdir}/yum.repos.d/redhat.repo

%post -n subscription-manager-gui
touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
scrollkeeper-update -q -o %{_datadir}/omf/%{name} || :

%postun -n subscription-manager-gui
if [ $1 -eq 0 ] ; then
    touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
    scrollkeeper-update -q || :
fi

%posttrans -n subscription-manager-gui
gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%clean
rm -rf %{buildroot}

%files -f rhsm.lang
%defattr(-,root,root,-)

%attr(755,root,root) %dir %{_var}/log/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm/facts

%attr(644,root,root) %config(noreplace) %{_sysconfdir}/rhsm/rhsm.conf
%config(noreplace) %{_sysconfdir}/dbus-1/system.d/com.redhat.SubscriptionManager.conf

#remove the repo file when we are deleted
%ghost %{_sysconfdir}/yum.repos.d/redhat.repo

%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/subscription-manager.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/product-id.conf
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

# Using _prefix + lib here instead of libdir as that evaluates to /usr/lib64 on x86_64,
# but yum plugins seem to normally be sent to /usr/lib/:
%{_prefix}/lib/yum-plugins/subscription-manager.py*
%{_prefix}/lib/yum-plugins/product-id.py*

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
%{_datadir}/rhsm/subscription_manager/certmgr.py*
%{_datadir}/rhsm/subscription_manager/listing.py*
%{_datadir}/rhsm/subscription_manager/release.py*
%{_datadir}/rhsm/subscription_manager/utils.py*


%attr(755,root,root) %{_sbindir}/subscription-manager
%attr(755,root,root) %{_bindir}/subscription-manager
%attr(755,root,root) %{_bindir}/rhsmcertd
%attr(755,root,root) %{_initrddir}/rhsmcertd
%attr(755,root,root) %{_libexecdir}/rhsmcertd-worker
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
%doc LICENSE


%files -n subscription-manager-gui
%defattr(-,root,root,-)
%dir %{_datadir}/rhsm/subscription_manager/gui
%dir %{_datadir}/rhsm/subscription_manager/gui/data
%dir %{_datadir}/rhsm/subscription_manager/gui/data/icons
%{_datadir}/rhsm/subscription_manager/gui/*
%{_datadir}/icons/hicolor/scalable/apps/subscription-manager.svg
%{_datadir}/applications/subscription-manager.desktop
%attr(755,root,root) %{_sbindir}/subscription-manager-gui
%attr(755,root,root) %{_bindir}/subscription-manager-gui

%if %use_rhsm_icon
%{_bindir}/rhsm-icon
%{_sysconfdir}/xdg/autostart/rhsm-icon.desktop
%endif

%{_sysconfdir}/pam.d/subscription-manager-gui
%{_sysconfdir}/security/console.apps/subscription-manager-gui

%doc
%{_mandir}/man8/subscription-manager-gui.8*
%{_mandir}/man8/rhsm-icon.8*
%{_datadir}/omf/subscription-manager
%attr(644,root,root) %{_datadir}/omf/subscription-manager/*.omf
%{_datadir}/gnome/help/subscription-manager
%attr(644,root,root) %{_datadir}/gnome/help/subscription-manager/C/*
%attr(755,root,root) %{_datadir}/gnome/help/subscription-manager/C/figures
%doc LICENSE

%files -n subscription-manager-firstboot
%defattr(-,root,root,-)
%{_datadir}/rhn/up2date_client/firstboot/rhsm_login.py*
%{_datadir}/rhn/up2date_client/firstboot/rhsm_select_sla.py*
%{_datadir}/rhn/up2date_client/firstboot/rhsm_confirm_subs.py*
%{_datadir}/rhn/up2date_client/firstboot/rhsm_manually_subscribe.py*

%if 0%{?rhel} < 6
  %if 0%{?fedora} <= 12
    # we are building for fedora <= 12 or rhel < 6
    %{_prefix}/share/firstboot/modules/rhsm_login.py*
    %{_prefix}/share/firstboot/modules/rhsm_select_sla.py*
    %{_prefix}/share/firstboot/modules/rhsm_confirm_subs.py*
    %{_prefix}/share/firstboot/modules/rhsm_manually_subscribe.py*
  %endif
%endif

%files -n subscription-manager-migration
%defattr(-,root,root,-)
%attr(755,root,root) %{_sbindir}/rhn-migrate-classic-to-rhsm
# Install num migration is only for RHEL 5:
%{?el5:%attr(755,root,root) %{_sbindir}/install-num-migrate-to-rhsm}

%doc
%{_mandir}/man8/rhn-migrate-classic-to-rhsm.8*
# Install num migration is only for RHEL 5:
%{?el5:%{_mandir}/man8/install-num-migrate-to-rhsm.8*}
%doc LICENSE
#only install this file on Fedora
%if 0%{?fedora} > 14
%doc README.Fedora
%endif

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
* Wed May 16 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.0.2-1
- Updating strings from zanata (mstead@redhat.com)
- Add new server setup GUI screen. (dgoodwin@redhat.com)
- Add new server setup CLI options. (alikins@redhat.com)
- 813296: Remove check for candlepin_version (jbowes@redhat.com)
- Allow importing multiple subscriptions at once (jbowes@redhat.com)
- 820170: Subscription Manager release --list should display "not supported"
  message for older candlepin. (wpoteat@redhat.com)
- 817938: Make columns in subscription-manager tables sortable.
  (awood@redhat.com)
- 812153: Release command should have a --show command which is the default.
  (wpoteat@redhat.com)
- 820080: Fix "Configuration" spelling on firstboot page (alikins@redhat.com)
- Set the parent window for the about dialog (mstead@redhat.com)
- removing a sentence from the manpage about working on RHEL 5.8 and later,
  bz820765 (deon@deonlackey.com)
- 821024: Properly handle ESC on preferences dialog (mstead@redhat.com)
- Replaced toolbar with menubar. (mstead@redhat.com)
- 820040,820037,820030: don't break multibyte help blurbs (alikins@redhat.com)
- 817036: Add a version command to subscription-manager. (awood@redhat.com)
- The unbindAll command now returns JSON. (awood@redhat.com)
- Explain the conditional imports more accurately. (alikins@redhat.com)
- Print different message when subscribing to no service level.
  (awood@redhat.com)
- remove deprecated use of "md5" module (alikins@redhat.com)
- Enable and disable available repos on client machine from Subscription
  Manager CLI (wpoteat@redhat.com)
- 790939: Add SLA to rhn-migrate-classic-to-rhsm. (awood@redhat.com)
- 812388: Show the number of entitlements unsubscribed from. (awood@redhat.com)
- 818298: release --list should not display rhel-5 when only rhel-6 product is
  installed (wpoteat@redhat.com)
- 810236: Update facts after registering with --consumerid.
  (dgoodwin@redhat.com)
- 818461: invalid date format error when using or_IN.UTF-8 (cduryee@redhat.com)
- Store date of migration in migration facts for rhn-migrate-classic-to-rhsm.
  (awood@redhat.com)
- Unify our el5 and el6 firstboot modules (jbowes@redhat.com)
- add a gconf setting for users who do not want to use the icon
  (cduryee@redhat.com)
- do not use the gui by default when migrating (cduryee@redhat.com)
- Allow service level change for consumer via CLI independent of other calls.
  (wpoteat@redhat.com)
- 815479: Incorrect owner should be relayed on service level list call.
  (wpoteat@redhat.com)
- 817390: add completion support for servicelevel (alikins@redhat.com)
- 817117: fix completion of environment command (alikins@redhat.com)
- 816377: handle cert migration data being missing (alikins@redhat.com)
- Store date of migration and installation number in migration facts.
  (awood@redhat.com)
- Fixing registration error when loading SlaWizard (mstead@redhat.com)

* Thu Apr 26 2012 Michael Stead <mstead@redhat.com> 1.0.1-1
- latest strings from zanata (alikins@redhat.com)
- add test cases for autobind.py (alikins@redhat.com)
- pep8 and pyflakes cleanups (jbowes@redhat.com)
- 815563: Remove incorrect at-spi locators. (awood@redhat.com)
- 795541: Environment command should omit the Library from katello
  (bkearney@redhat.com)
- 806993: Tolerate the provision of a scheme with the proxy string.
  (awood@redhat.com)
- remove remnants of subscription_assistant.py (alikins@redhat.com)
- 811952: Don't try to unsubscribe old ents if we register (alikins@redhat.com)
- 811952: Handle errors on unsubscribing ent certs (alikins@redhat.com)
- 812929: Fix issue with selected sla not being in suitable_slas
  (mstead@redhat.com)
- 812897: Use consistent casing for the word "Error" (awood@redhat.com)
- Improve preferences dialog error message. (dgoodwin@redhat.com)
- 811863: Handle unforseen errors in preferences dialog. (dgoodwin@redhat.com)
- 811340: Select the first product in My Installed Software table by default.
  (awood@redhat.com)
- 811594: The config, repos, and facts commands should default to --list if no
  options are provided. (awood@redhat.com)
- 812104: add "release" and "service-level" to completion (alikins@redhat.com)
- 801434: Add at-spi accessibility name to calendar widget. (awood@redhat.com)
- updates to man pages (deon@deonlackey.com)
- 811591: Use consistent messages for not being registered
  (bkearney@redhat.com)
- Updated the --servicelevel option description (deon@deonlackey.com)
- Use numeric index to access value returned by urlparse. (awood@redhat.com)
- 790579: Show translations for errors thrown by installation number parsing.
  (awood@redhat.com)
- adding --servicelevel option to list command (deon@deonlackey.com)
- 810306: Improved messaging in firstboot (mstead@redhat.com)
- 811337: unregister any time we return to rhsm_login (jbowes@redhat.com)
- 807153: Allow more aggressive deletion of product certs. (awood@redhat.com)
- 810399: require the latest rhn-setup-gnome for firstboot (alikins@redhat.com)
- 810290: use correct calculation for "Next update" time in sm-gui
  (cduryee@redhat.com)
- 810363: handle socket errors for bad proxy host in firstboot
  (alikins@redhat.com)
- Latest man page and documentation (dlackey@redhat.com)
- 809989: Add the shortened password url to the strings files.
  (bkearney@redhat.com)
- 809989: Add a shorter URL to the registration screen (bkearney@redhat.com)
- rev the zanata version to 1.0.X (alikins@redhat.com)
- Incrementing version number after 6.3 branch. (mstead@redhat.com)

* Wed Apr 04 2012 Michael Stead <mstead@redhat.com> 0.99.13-1
- latest strings into keys.pot and updated from zanata (alikins@redhat.com)
- 809611: Fix undefined variable in installedtab for expired
  (alikins@redhat.com)
- pep8/pyflakes cleanups (alikins@redhat.com)
- Repolib now requires a UEP connection. (awood@redhat.com)
- Use numeric index to access portion of URL. (awood@redhat.com)
- 807785: use a better title on the autobind wizard (jbowes@redhat.com)
- latest strings from zanata (alikins@redhat.com)
- Add release selection to preferences dialog (alikins@redhat.com)
- 805415: handle entitlements for socket count of 0 (alikins@redhat.com)
- 804201: Fix sla select in firstboot after back button (jbowes@redhat.com)
- 807477: Delay attempt to connect to RHN until after basic error checks.
  (awood@redhat.com)
- 803374: Change the 'Subscribe' button to read 'Auto-subscribe.'
  (awood@redhat.com)
- 808217: Add a header to the release list (bkearney@redhat.com)
- 807153: Provide a more informative error message when encountering repodata
  errors. (awood@redhat.com)
- 807822: Allow setting release to '' (mstead@redhat.com)
- 807036: Instruct users to go to All Subscriptions for all SLA failures
  (bkearney@redhat.com)
- 807407: Subscripton Manager substitutes "" for $releasever when releaseVer
  not set on consumer (wpoteat@redhat.com)
- 803756: Trap RemoteServerException as well as RestLibException (404) for
  service-level command (mstead@redhat.com)
- 806941: Removed unknown swapped attribute from autobind.glade.
  (mstead@redhat.com)
- 807360: Allow the repos command to work without being registered
  (bkearney@redhat.com)
- 806457: Fix deletion of productids with yum localinstall (alikins@redhat.com)

* Fri Mar 23 2012 Michael Stead <mstead@redhat.com> 0.99.12-1
- Don't skip past firstboot login page on invalid user/pass (jbowes@redhat.com)
- 805690: Turn repo gpgcheck off if no gpgkey specified. (dgoodwin@redhat.com)
- 795552: Put safe int conversions around certain fact checks.
  (bkearney@redhat.com)
- 804100: display an error when candlepin doesn't support release
  (jbowes@redhat.com)
- 804227: expect a Release object instead of a bare string (alikins@redhat.com)
- Latest string files from zanata (bkearney@redhat.com)
- 805450: display better error message when autosubscribing
  (cduryee@redhat.com)
- 805594: Give each "Subscribe" button in the GUI a unique at-spi name.
  (awood@redhat.com)
- 803374: Provide unambiguous at-spi names for widgets. (awood@redhat.com)
- 805353: subscription-manager list --help should use consistent wording for
  servicelevel option. (awood@redhat.com)

* Thu Mar 22 2012 Michael Stead <mstead@redhat.com> 0.99.11-1
- 805906: fix missing imports for firstboot (jbowes@redhat.com)
- Fix RHEL6 firstboot attribute error (dgoodwin@redhat.com)
- 772218: throw an error if unparsed command line options exist
  (cduryee@redhat.com)
- Add missing imports to rhsm_login for error dialogs (jbowes@redhat.com)
- 803386: Display product ID in GUI and CLI. (awood@redhat.com)
- Fix specfile for el5 firstboot (jbowes@redhat.com)
- 804227,804076,804228: Handle 404's from old candlepin servers without
  /release (alikins@redhat.com)
- 803778: Updated the --servicelevel not supported messages for subscribe
  command (mstead@redhat.com)
- 803778: Updated the --servicelevel not supported messages for register
  command (mstead@redhat.com)
- 803756,803762: Updated error message for service-level command
  (mstead@redhat.com)
- fixups for strings from zanata (alikins@redhat.com)
- latest strings from zanata (alikins@redhat.com)
- 789007: Migration should fail early when attempted with non org admin user.
  (awood@redhat.com)
- 805024: Hide extra separator along with redeem button. (awood@redhat.com)
- 800999: Added --servicelevel arg to CLI list command (mstead@redhat.com)
- 804227: Fix issues with repos --list (alikins@redhat.com)
- Add proper back/forward logic for firstboot sla subscribe (jbowes@redhat.com)
- 800933: Display service level and type in CLI list commands.
  (dgoodwin@redhat.com)
- 789008: Print a more specific error message when Candlepin calls fail.
  (awood@redhat.com)
- hook up sla firstboot to more registration cases (jbowes@redhat.com)
- Define globals at module scope. (awood@redhat.com)
- Remove firstboot subscriptions module (jbowes@redhat.com)
- Fix broken tests for DST. Stop using time.time() (alikins@redhat.com)
- Add error cases for firstboot autobind (jbowes@redhat.com)
- Perform the actual entitlement bind on confirm subs screen
  (jbowes@redhat.com)
- Set up shared state for AutobindController in firstboot (jbowes@redhat.com)
- Extract a controller class for sla select logic (jbowes@redhat.com)
- Break apart autobind first boot module (jbowes@redhat.com)
- Add some autobind wizard button spacing. (dgoodwin@redhat.com)
- Always update the icon and notification details on status change.
  (mstead@redhat.com)
- Only add icon click listeners once. (mstead@redhat.com)
- Adding notification nag icon support for Registration Required
  (mstead@redhat.com)
- add firstboot rhsm_autobind to spec file (jbowes@redhat.com)
- Autobind cancel during registration will now unregister you.
  (dgoodwin@redhat.com)
- Update CLI to handle server that doesn't support service levels.
  (dgoodwin@redhat.com)
- Move back/forward/cancel buttons in sla selection to parent
  (jbowes@redhat.com)
- Revert "Update CLI to handle server that doesn't support service levels."
  (dgoodwin@redhat.com)
- Update GUI to handle server that does not support service levels.
  (dgoodwin@redhat.com)
- Update CLI to handle server that doesn't support service levels.
  (dgoodwin@redhat.com)
- Add autobind screen to firstboot (jbowes@redhat.com)
- Fix firstboot unregister import error. (dgoodwin@redhat.com)
- Add missing spacers to main window toolbar. (dgoodwin@redhat.com)
- Fix an error handling bug. (dgoodwin@redhat.com)
- Get register screen working in el6 firstboot (jbowes@redhat.com)
- Center wizard's error dialog on main window (mstead@redhat.com)
- Removing commented out code in register dialog (mstead@redhat.com)
- Add skip option instead of autobind in register dialog. (mstead@redhat.com)
- Fix preferences dialog error when not registered. (dgoodwin@redhat.com)
- Improved error handling for autobind wizard. (dgoodwin@rm-rf.ca)
- Fix message window warnings. (dgoodwin@rm-rf.ca)
- Fix alignment on select SLA screen. (dgoodwin@redhat.com)
- Display the service level selected when confirming autobind subs (dgoodwin
  @rm-rf.ca)
- Implement Cancel button on autobind wizard screens. (dgoodwin@redhat.com)
- Allow setting service level from preferences dialog. (dgoodwin@redhat.com)
- First cut at a preferences dialog. (dgoodwin@redhat.com)
- Pack SLA's into a scrolled window. (dgoodwin@rm-rf.ca)
- Handle any exception that happens when the autobind wizard is loaded.
  (mstead@redhat.com)
- Setting parent window on AutobindDialog and add titles to screens.
  (mstead@redhat.com)
- Integrating autobind wizard with register gui. (mstead@redhat.com)
- Fix autobind wizard disappearing on window switch. (dgoodwin@redhat.com)
- Do not set SLA until user hit's subscribe button. (dgoodwin@redhat.com)
- Polish autobind glade UI (dgoodwin@redhat.com)
- Set and use the system's service level. (dgoodwin@redhat.com)
- Cleaning up Select SLA screen (mstead@redhat.com)
- Added framework for back button support (mstead@redhat.com)
- Handle no SLAs cover all installed products. (dgoodwin@rm-rf.ca)
- Handle launching autobind when no entitlements needed. (dgoodwin@rm-rf.ca)
- Set detected prod list in Select SLA screen (mstead@redhat.com)
- Close autobind wizard once complete. (dgoodwin@redhat.com)
- Hookup actual bind in autobind wizard. (dgoodwin@redhat.com)
- SelectSLA now keeps track of selected SLA and pass to confirm dialog.
  (mstead@redhat.com)
- Load the autobind glade file on wizard creation. (mstead@redhat.com)
- Switch to more explicit screen switching. (dgoodwin@redhat.com)
- Set screen title when screen is changed. (mstead@redhat.com)
- Allow screens to pass custum data during wizard screen change.
  (mstead@redhat.com)
- Hooking up button signals for selectsla (mstead@redhat.com)
- Add callback to allow screen change in wizard (mstead@redhat.com)
- Fixing broken tests due to leap year. (mstead@redhat.com)
- Attempt to keep button bar right aligned. (mstead@redhat.com)
- Removed the button bar form the wizard. (mstead@redhat.com)
- Created AutobindWizardScreen to provide contract for AutobindWizard
  (mstead@redhat.com)
- Display appropriate screen in SLA wizard. (mstead@redhat.com)
- Fixed GtkWarning: IA__gtk_widget_reparent error when launchig dialog
  (mstead@redhat.com)
- First cut at adding the Select SLA screen. (mstead@redhat.com)
- Check if dry-run results cover required products. (dgoodwin@redhat.com)
- Check dry run autobind results for each service level. (dgoodwin@redhat.com)
- Sketch out an autobind wizard class. (dgoodwin@redhat.com)
- Start sketching out the confirm subscriptions screen. (dgoodwin@redhat.com)

* Wed Mar 14 2012 Michael Stead <mstead@redhat.com> 0.99.10-1
- latest strings from zanata (alikins@redhat.com)
- 801434: Add at-spi accessibility name to calendar selection widget.
  (awood@redhat.com)
- 800917: Display service level and type in All Subs tab (dgoodwin@redhat.com)
- Add support for "release" command (alikins@redhat.com)
- 801517: Missed translating a label during the registration process
  (bkearney@redhat.com)
- 801513: One translation had a copy/paste error (bkearney@redhat.com)
- The migration script should write default proxy auth settings.
  (awood@redhat.com)
- Revert "801513: A replacement variable was used in a translation file where
  it was not needed" (dgoodwin@redhat.com)
- 801545: Break apart the string to make them easier for the translators
  (bkearney@redhat.com)
- 801513: A replacement variable was used in a translation file where it was
  not needed (bkearney@redhat.com)
- 798015: Migration script should play nicely with proxies. (awood@redhat.com)
- 742033: Unsubscribe button is not greyed out when nothing is selected
  (wpoteat@redhat.com)
- 783990: Handle network errors when migrating. (awood@redhat.com)

* Tue Mar 06 2012 Michael Stead <mstead@redhat.com> 0.99.9-1
- Updating required version of python-rhsm (mstead@redhat.com)
- fixes for po files (alikins@redhat.com)
- latest translations from zanata (alikins@redhat.com)
- 799394: Do not attempt to remove redhat.repo if it does not exist.
  (awood@redhat.com)
- 800121: do not attempt to call UEP when system is unregistered
  (cduryee@redhat.com)
- 799271: The usage string for service-levels contained the incorrect command
  name (bkearney@redhat.com)
- 799271: The usage string for service-levels contained the incorrect command
  name (bkearney@redhat.com)
- 704408: date field patch fixes per jbowes (cduryee@redhat.com)
- 797243: make unregister finish updating repos (alikins@redhat.com)
- 704408: allow users to clear the date box for contract searches
  (cduryee@redhat.com)
- 799316: Re-add librsvg2 dependency (dgoodwin@redhat.com)
- 797996: Add manage_repos setting to default rhsm.conf (dgoodwin@redhat.com)
- 795564: Add a newline at the end of the options error (bkearney@redhat.com)
- 752756: Cache the facts, and refresh the validity facts whenever they change.
  (bkearney@redhat.com)
- Return a consistent scope for public IPv6 addresses across EL5 and EL6.
  (awood@redhat.com)
- 737773: Do not show the forgotten password url as a link.
  (bkearney@redhat.com)
- Fixing broken tests due to leap year. (mstead@redhat.com)
- Explicitly define el5 macro in spec file. (dgoodwin@redhat.com)
- 796730: Improve the clarity of the usage statement (bkearney@redhat.com)
- 767790: Improve the messaging when a system is not registered.
  (bkearney@redhat.com)
- 797294: Typo in commit caused execution error. (bkearney@redhat.com)
- 796756: use only the basename for the usage string (bkearney@redhat.com)
- 796756: The usage string should be less verbose to be more consistent with
  the other executable files (bkearney@redhat.com)
- CLI service-levels touchups. (dgoodwin@redhat.com)
- 656896: remove attribute 'swapped' (msuchy@redhat.com)
- Release to Fedora 17 branch as well. (dgoodwin@redhat.com)

* Wed Feb 22 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 0.99.8-1
- 790205: do not lay down install-num-migrate-to-rhsm on rhel6 systems
  (cduryee@redhat.com)
- latest translations from zanata (alikins@redhat.com)
- 795541: Change the environment filtering which is being done on the client
  side (bkearney@redhat.com)
- Add consumer deleted on server detection. (jbowes@redhat.com)
- Fix spec for both Fedora 15+ and RHEL 7+. (dgoodwin@redhat.com)
- Fix Makefile for both Fedora 15+ and RHEL 7+. (dgoodwin@redhat.com)
- Add service level to register and subscribe CLI commands.
  (dgoodwin@redhat.com)
- Add service-level CLI command. (dgoodwin@redhat.com)
- delete consumer on rhsmcertd checkin (jbowes@redhat.com)
- pull out rhsmcertd python worker to its own file (jbowes@redhat.com)
- clean up some compiler warnings in rhsmcertd (jbowes@redhat.com)
- String cleanups (alikins@redhat.com)
- 790217: install-num-migrate-to-rhsm shouldn't copy both Desktop and
  Workstation product certs. (awood@redhat.com)

* Mon Feb 13 2012 Michael Stead <mstead@redhat.com> 0.99.7-1
- Improve relevancy of details on my installed products tab.
  (dgoodwin@redhat.com)
- 719743: Added better punctuation to one status message (bkearney@redhat.com)
- Have client check sockets on non-stacked entitlements as well.
  (dgoodwin@redhat.com)
- New date compare implemetation for determining start/end dates
  (mstead@redhat.com)
- Add "zanata-pull" and "zanata-push" makefile targets (alikins@redhat.com)
- as_IN seems busted on RHEL6, so skip it (alikins@redhat.com)
- pep8/make stylish cleanups (alikins@redhat.com)
- 741155: Fixed start/end date calculations for My Installed Software tab
  (mstead@redhat.com)
- fixes for po files from zanata (alikins@redhat.com)
- new po files from zanata (alikins@redhat.com)
- 767620: Add manage_repos config option. (dgoodwin@redhat.com)
- 784031: remove katello plugin (cduryee@redhat.com)
- Make return code from import consistent with subscribe. (awood@redhat.com)
- Add Fedora release target. (dgoodwin@redhat.com)

* Wed Feb 01 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 0.99.6-1
- 783542: Return code for bad input to install-num-migrate-to-rhsm should be 1.
  (awood@redhat.com)
- 773707: remove hard coded reference to /etc/pki/product (cduryee@redhat.com)
- 783278: do not alter system facts on dry run (cduryee@redhat.com)
- IPv4 and IPv6 facts that are undefined should return 'Unknown' instead of
  'None'. (awood@redhat.com)

* Fri Jan 27 2012 Michael Stead <mstead@redhat.com> 0.99.5-1
- Updated releasers.conf for rhel-6.3 (mstead@redhat.com)
- Making return code from subscribe --pool consistent with subscribe --auto
  (awood@redhat.com)
- 785018: Corrected help text for --no-auto. (awood@redhat.com)
- 656944: List IPv6 information in facts. (awood@redhat.com)
- 689608: Subscription failure should result in a return code of 1.
  (awood@redhat.com)
- 772921: Do not show message dialog when multiple sub-man launches detected.
  (mstead@redhat.com)
- 772921: Clicking notification icon shuts down subscription manager.
  (mstead@redhat.com)
- 734533: Failure to import should result in a return code of 1.
  (awood@redhat.com)
- 782549: Subscription manager throws exception when an expired cert exists.
  (mstead@redhat.com)
- 772338: Subscription-manager-gui help documentation review
  (wpoteat@redhat.com)
- 772338: subscription-manager-gui Help documentation needs a review
  (wpoteat@redhat.com)
- latest strings from zanata (alikins@redhat.com)
- 781510: 'subscription-manager clean' should delete redhat.repo
  (awood@redhat.com)
- 771726: Man page for rhsm-compliance-icon should be re-authored to rhsm-icon
  (wpoteat@redhat.com)

* Thu Jan 12 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 0.99.4-1
- 766778: Improvements on quantity spinner max value entry. (mstead@redhat.com)
- 736465: "Product's Subscription Details" in the gui is neglecting stack
  subscriptions (wpoteat@redhat.com)
- 772209: install-num-migrate-to-rhsm does not work on x86 arch
  (cduryee@redhat.com)
- 761140: enable the help button in firstboot (jbowes@redhat.com)
- 771726: Rename man manpage for rhsm-compliance-icon to rhsm-icon.
  (bkearney@redhat.com)
- 758038: Guest's system facts displays "virt.uuid: Unknown"
  (wpoteat@redhat.com)
- 767265: Always send up the list of packages on registration.
  (awood@redhat.com)
- 768983: show future subs in list --consumed (jbowes@redhat.com)

* Tue Jan 03 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 0.99.3-1
- 768983: don't purge future dated entitlements (jbowes@redhat.com)
- 769642: confusing output from rhn-migrate-to-rhsm when autosubscribe fails
  (cduryee@redhat.com)
- 769433: make rhel5 firstboot modules use bound gettext (alikins@redhat.com)
- Custom facts should be loaded after hardware facts. (awood@redhat.com)
- 745973: Fixed missing product icons for partially stacked future entitlement.
  (mstead@redhat.com)
- 769433: Tag the module names as gettext (alikins@redhat.com)
- 761478: Facts viewed in the GUI were getting out of date when system
  entitlement status changed. (awood@redhat.com)
- 761133: Support fixing yellow state in compliance assistant.
  (dgoodwin@redhat.com)
- 766577: use unicode strings for possible server errors (alikins@redhat.com)
- 768415: remove hardcoded reference to x86_64 for extra channel enablement
  (cduryee@redhat.com)

* Fri Dec 16 2011 Devan Goodwin <dgoodwin@redhat.com> 0.99.2-1
- Initial Fedora build. (dgoodwin@redhat.com)
- 754425: Remove grace period logic (jbowes@redhat.com)
- 766577: Fix error on "redeem" with multibyte lang (alikins@redhat.com)
- Add README.Fedora to Fedora builds (cduryee@redhat.com)
- 757697: report xen dom0 as host, not guest (cduryee@redhat.com)
- 747014: Help icon was not working in RHEL 5. (awood@redhat.com)
- 767754: Invalid certificate status when stacked entitlements have overlapping
  dates (wpoteat@redhat.com)
- 745995: Ensure default quantity calc does not include future entitlements.
  (mstead@redhat.com)
- 760017: Display a friendly message when an invalid installation number is
  encountered. (awood@redhat.com)
- 758162: allow --force to override missing mappings (cduryee@redhat.com)
- 759069: catch exception when enabling invalid repositories
  (cduryee@redhat.com)

* Mon Dec 12 2011 William Poteat <wpoteat@redhat.com> 0.98.8-1
- 755861: Fixed quantity selection issue due to older version of pygtk on 5.8.
  (mstead@redhat.com)
- 765905: add man pages for subscription-manager-migration (cduryee@redhat.com)

* Wed Dec 07 2011 William Poteat <wpoteat@redhat.com> 0.98.7-1
- mismatch newlines in strings (jesusr@redhat.com)

* Wed Dec 07 2011 William Poteat <wpoteat@redhat.com> 0.98.6-1
- 755031: Update to Subscription Assistant quantity check in unlimited pool
  case. (wpoteat@redhat.com)

* Mon Dec 05 2011 William Poteat <wpoteat@redhat.com> 0.98.5-1
- 755031: Unregister before attempting to run a second registration
  (jbowes@redhat.com)

* Mon Dec 05 2011 William Poteat <wpoteat@redhat.com> 0.98.4-1
- 740788: Getting error with quantity subscribe using subscription-assitance
  page. (wpoteat@redhat.com)
- 755130: add extra whitespace to classic warning (cduryee@redhat.com)
- 759199: rhsmcertd is logging the wrong value for certFrequency
  (cduryee@redhat.com)
- 758471: install-num-migrate-to-rhsm threw traceback when no instnum was
  found. (awood@redhat.com)
- 752572: add interval logging statements back in on rhsmcertd startup
  (cduryee@redhat.com)
- 756507: do not use output from "getlocale" as input for "setlocale"
  (cduryee@redhat.com)
- 746259: Don't allow the user to pass in an empty string as an activation key
  (awood@redhat.com)
- 705883: Fix error dialog modal issues. (dgoodwin@redhat.com)
- 756173: Unexpected behavoir change in subscription-manager unregister
  (wpoteat@redhat.com)
- 746732: Only use fallback locales for dates we need to parse
  (alikins@redhat.com)
- 753093: The available subscriptions count does not show correctly in
  Subscription Manager GUI (wpoteat@redhat.com)
- 749636: Client should not support users entering activation keys and existing
  consumer ids (bkearney@redhat.com)
- 719743: Improved text output for successful pool subscription
  (bkearney@redhat.com)
- 755541: Enhanced the message in the katello plugin to debug when the backend
  system does not support environments. (bkearney@redhat.com)
- 755035: Migration script should work on RHEL 5.7 and up. (awood@redhat.com)
- 749332: Normalize the error messages for not being registered
  (bkearney@redhat.com)
- 754821: Default org of "Unknown" was not marked for gettext
  (alikins@redhat.com)
