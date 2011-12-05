Name: subscription-manager
Version: 0.98.5
Release: 1%{?dist}
Summary: Tools and libraries for subscription and repository management
Group:   System Environment/Base
License: GPLv2

# How to create the source tarball:
#
# git clone git://git.fedorahosted.org/git/subscription-manager.git/
# tito build --tag subscription-manager-%{version}-%{release} --tgz
Source0: %{name}-%{version}.tar.gz
URL:     https://fedorahosted.org/subscription-manager/
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:  python-ethtool
Requires:  python-simplejson
Requires:  python-iniparse
Requires:  PyXML
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

%if 0%{?fedora} < 15
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

# Using _prefix + lib here instead of libdir as that evaluates to /usr/lib64 on x86_64,
# but yum plugins seem to normally be sent to /usr/lib/:
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
%attr(644,root,root) %{_datadir}/omf/subscription-manager/*.omf
%{_datadir}/gnome/help/subscription-manager
%attr(644,root,root) %{_datadir}/gnome/help/subscription-manager/C/*
%attr(755,root,root) %{_datadir}/gnome/help/subscription-manager/C/figures

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
