Name: subscription-manager
Version: 0.95.5.2
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
        %{buildroot}/etc/xdg/autostart/rhsm-compliance-icon.desktop
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

%{_sysconfdir}/cron.daily/rhsm-complianced
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
%attr(755,root,root) %{_bindir}/rhsmcertd
%attr(755,root,root) %{_sysconfdir}/init.d/rhsmcertd
%attr(755,root,root) %{_libexecdir}/rhsm-complianced
%attr(755,root,root) %dir %{_var}/run/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm/facts

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
%{_bindir}/rhsm-compliance-icon
%{_sysconfdir}/xdg/autostart/rhsm-compliance-icon.desktop
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
# /sbin/service rhsmcertd start

%preun
if [ $1 -eq 0 ] ; then
   /sbin/service rhsmcertd stop >/dev/null 2>&1
   /sbin/chkconfig --del rhsmcertd
fi

%changelog
* Wed Mar 30 2011 Chris Duryee (beav) <cduryee@redhat.com>
- 668616: [RFE] Subscription Manager client (bkearney@redhat.com)
