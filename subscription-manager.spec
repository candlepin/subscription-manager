Name: subscription-manager
Version: 0.95.5.16
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
Requires:  virt-what
Requires:  python-rhsm
Requires:  dbus-python
Requires:  yum >= 3.2.19-15

# There's no dmi to read on these arches, so don't pull in this dep.
%ifnarch ppc ppc64 s390 s390x
Requires:  python-dmidecode
%endif

Requires(post): chkconfig
Requires(post): dbus
Requires(preun): chkconfig
Requires(preun): initscripts
Requires(preun): dbus
BuildRequires: python-devel
BuildRequires: gettext
BuildRequires: intltool
BuildRequires: libnotify-devel
BuildRequires: gtk2-devel
BuildRequires: desktop-file-utils
BuildRequires: redhat-lsb


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


%prep
%setup -q

%build
make -f Makefile

%install
rm -rf $RPM_BUILD_ROOT
make -f Makefile install VERSION=%{version}-%{release} PREFIX=$RPM_BUILD_ROOT MANPATH=%{_mandir}

desktop-file-validate \
        %{buildroot}/etc/xdg/autostart/rhsm-icon.desktop
desktop-file-validate \
        %{buildroot}/usr/share/applications/subscription-manager.desktop
%find_lang rhsm

# fix timestamps on our byte compiled files so them match across arches
find $RPM_BUILD_ROOT -name \*.py -exec touch -r %{SOURCE0} '{}' \;

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

%files -f rhsm.lang
%defattr(-,root,root,-)

%attr(755,root,root) %dir %{_var}/log/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm/facts
%attr(755,root,root) %dir %{_sysconfdir}/rhsm/ca

%attr(640,root,root) %config(noreplace) %{_sysconfdir}/rhsm/rhsm.conf
%attr(640,root,root) %{_sysconfdir}/rhsm/ca/*.pem
%config(noreplace) %{_sysconfdir}/dbus-1/system.d/com.redhat.SubscriptionManager.conf

%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/subscription-manager.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/product-id.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/logrotate.d/subscription-manager

%{_sysconfdir}/cron.daily/rhsmd
%{_datadir}/dbus-1/system-services/com.redhat.SubscriptionManager.service

%dir %{_datadir}/rhsm
%dir %{_datadir}/rhsm/subscription_manager
%{_datadir}/rhsm/subscription_manager/__init__.py*
%{_datadir}/rhsm/subscription_manager/i18n_optparse.py*
%{_datadir}/rhsm/subscription_manager/managercli.py*
%{_datadir}/rhsm/subscription_manager/managerlib.py*
%{_datadir}/rhsm/subscription_manager/async.py*
%{_datadir}/rhsm/subscription_manager/logutil.py*
%{_datadir}/rhsm/subscription_manager/repolib.py*
%{_prefix}/lib/yum-plugins/subscription-manager.py*
%{_prefix}/lib/yum-plugins/product-id.py*
%{_datadir}/rhsm/subscription_manager/certlib.py*
%{_datadir}/rhsm/subscription_manager/hwprobe.py*
%{_datadir}/rhsm/subscription_manager/constants.py*
%{_datadir}/rhsm/subscription_manager/lock.py*
%{_datadir}/rhsm/subscription_manager/facts.py*
%{_datadir}/rhsm/subscription_manager/factlib.py*
%{_datadir}/rhsm/subscription_manager/productid.py*
%attr(755,root,root) %{_datadir}/rhsm/subscription_manager/certmgr.py*
%attr(755,root,root) %{_sbindir}/subscription-manager
%attr(755,root,root) %{_bindir}/subscription-manager
%attr(755,root,root) %{_bindir}/rhsmcertd
%attr(755,root,root) %{_initrddir}/rhsmcertd
%attr(755,root,root) %{_libexecdir}/rhsmd
%attr(755,root,root) %dir %{_var}/run/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm/facts
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
%{_bindir}/rhsm-icon
%{_sysconfdir}/xdg/autostart/rhsm-icon.desktop
%{_sysconfdir}/pam.d/subscription-manager-gui
%{_sysconfdir}/security/console.apps/subscription-manager-gui

%doc
%{_mandir}/man8/subscription-manager-gui.8*
%{_mandir}/man8/rhsm-compliance-icon.8*


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

%post
chkconfig --add rhsmcertd
dbus-send --system --type=method_call --dest=org.freedesktop.DBus / org.freedesktop.DBus.ReloadConfig > /dev/null 2>&1 || :
# /sbin/service rhsmcertd start

%preun
if [ $1 -eq 0 ] ; then
   /sbin/service rhsmcertd stop >/dev/null 2>&1
   /sbin/chkconfig --del rhsmcertd
   dbus-send --system --type=method_call --dest=org.freedesktop.DBus / org.freedesktop.DBus.ReloadConfig > /dev/null 2>&1 || :
fi

%changelog
* Mon May 16 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 697965: use str type for serial id's to fix issues on i386
  (alikins@redhat.com)

* Fri May 13 2011 Chris Duryee (beav) <cduryee@redhat.com>
- a tab snuck in here (cduryee@redhat.com)
- regen strings for string freeze (two new strings) (cduryee@redhat.com)
- 696791: Handle exceptions thrown in hardware detection modules.
  (alikins@redhat.com)

* Thu May 12 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 703920: contract selection was not showing dates for pools
  (alikins@redhat.com)
- 683553: Make -1 show as unlimited (bkearney@redhat.com)

* Tue May 10 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 703626: product-id yum plugin was using too new of yum api
  (alikins@redhat.com)
- 703491: firstboot would continue to next screen on auth failure
  (alikins@redhat.com)

* Tue May 10 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 700958: fire check_status dbus calls in a non-blocking manner
  (jbowes@redhat.com)
- 701458: Do not display activation messages as errors. (dgoodwin@redhat.com)

* Mon May 09 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 670973: check for yum conduit api we need, it's missing on 5.7
  (alikins@redhat.com)
- 702092: fit 'activate a subscription' button in 800x600 (jbowes@redhat.com)
- 700952: Fix SystemExit traceback logging on older Python versions.
  (dgoodwin@redhat.com)
- 693527: Adding 'usage: ' id for older versions of optparse.
  (jharris@redhat.com)
- 701263: Moving dmiinfo declaration and allowing for failures in dmi function
  calls. (jharris@redhat.com)
- 702026: confusing warning message when rhsm-icon runs twice
  (cduryee@redhat.com)
- 702078: try really hard to set a meaningful locale (alikins@redhat.com)

* Wed May 04 2011 Chris Duryee (beav) <cduryee@redhat.com>
- fix BZ # in spec to reference el5 cloned bug (cduryee@redhat.com)

* Wed May 04 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 700058: Displaying previous imported cert in cert browser option
  (cduryee@redhat.com)
- 700838: we need to import glade from gtk (alikins@redhat.com)
- 700547: ensure the notification attaches to rhsm-icon (jbowes@redhat.com)
- Write unique key.pem for each entitlement. (dgoodwin@redhat.com)
- regenerate PO files for translation (3 new strings, and one fuzzy)
  (cduryee@redhat.com)
- Apply initial cut of 5.7 translations (cduryee@redhat.com)
- Revert "regenerate PO files for translation" (cduryee@redhat.com)
- regenerate PO files for translation (cduryee@redhat.com)
- 702072: We were skipping the code that hides the activation button
  (alikins@redhat.com)
- 702072: Tweaking activate dialog properties to show in firstboot.
  (jharris@redhat.com)
- fix typo per l10n team (cduryee@redhat.com)
- fix typo per l10n team (cduryee@redhat.com)
- 700073: Background is click able while handling Import certificate dialog box
  (cduryee@redhat.com)
- 695234: dates are being displayed incorrectly everywhere (alikins@redhat.com)
- 697908: regression in subscription-manager unregister (cduryee@redhat.com)
- 697965: on x86, serial numbers do not like to be long's (alikins@redhat.com)

* Mon Apr 18 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 694851: only open one dbus proxy connection (jbowes@redhat.com)
- 696679: add pam/consolehelper links for subscription-manager
  (alikins@redhat.com)
- 696947: wrong webqa url is present in rhsm.conf for rhel5.7
  (cduryee@redhat.com)
- 696947: wrong webqa url is present in rhsm.conf for rhel5.7
  (cduryee@redhat.com)
- 674652: Subscription Manager Leaves Broken Yum Repos After Unregister
  (cduryee@redhat.com)
- 694839: clean a merge error (old regex was not removed) (alikins@redhat.com)
- 696210: fix display of error messages with urls (alikins@redhat.com)
- 694839: Remove some pango markup and instead linkify links ourselves
  (alikins@redhat.com)
- 696674: rhsmcertd was using the wrong path for certmgr.py
  (alikins@redhat.com)
- 683553: subscription-manager-gui is displaying unlimited pools as -1
  (cduryee@redhat.com)
- 696171: fix regression in error message formatting (jbowes@redhat.com)
- 694842: error messages do not get populated during firstboot
  (cduryee@redhat.com)
- 695788: fix bug showing the "you are registered to rhn" dialog
  (alikins@redhat.com)
- 694837: fix entitlement failure that throws sequence error
  (alikins@redhat.com)
- Latest japanese strings (bkearney@redhat.com)

* Mon Apr 11 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 695367: call to dbus-send fails during upgrades on selinux-enabled machines
  (cduryee@redhat.com)
- 670798: put initscript in /etc/rc.d/init.d (jbowes@redhat.com)

* Fri Apr 08 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 694877: Fix wrong module imports in yum plugins and wrong path for certmgr.py
  (alikins@redhat.com)
* Wed Apr 06 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 694154: remove extraneous slashes in symlink (cduryee@redhat.com)
- 693896: subscription manager does not always reload dbus scripts
  automatically (cduryee@redhat.com)

* Tue Apr 05 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 693834: remove $PREFIX from svg icon symlink (alikins@redhat.com)
- re-extract i18n keys (jbowes@redhat.com)
- remove duplicate l10n from context removal (jbowes@redhat.com)
- remove msg context from glade files (jbowes@redhat.com)
- Add "arch" info to the product info displayed on installed products screen
  (alikins@redhat.com)
- extract latest i18n keys (jbowes@redhat.com)
- Add the latest l10n strings (jbowes@redhat.com)
* Wed Mar 30 2011 Chris Duryee (beav) <cduryee@redhat.com>
- alter specfile to make sense in cvs (cduryee@redhat.com)

* Wed Mar 30 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 668616: [RFE] Subscription Manager client (bkearney@redhat.com)
