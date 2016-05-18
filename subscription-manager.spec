# Prefer systemd over sysv on Fedora 17+ and RHEL 7+
%global use_systemd (0%{?fedora} && 0%{?fedora} >= 17) || (0%{?rhel} && 0%{?rhel} >= 7)
# For optional building of ostree-plugin sub package. Unrelated to systemd
# but the same versions apply at the moment.
%global has_ostree %use_systemd
%global use_firstboot 0
%global use_initial_setup 1
%global rhsm_plugins_dir  /usr/share/rhsm-plugins
%global use_gtk3 %use_systemd
%global rhel7_minor %(%{__grep} -o "7.[0-9]*" /etc/redhat-release |%{__sed} -s 's/7.//')

%if 0%{?rhel} == 7
%global use_initial_setup 1
%global use_firstboot 0
%endif

# 6 < rhel < 7
%if 0%{?rhel} == 6
%global use_initial_setup 0
%global use_firstboot 1
%endif

%global use_dnf (0%{?fedora} && 0%{?fedora} >= 22)


%global _hardened_build 1
%{!?__global_ldflags: %global __global_ldflags -Wl,-z,relro -Wl,-z,now}

# A couple files are for RHEL 5 only:
%if 0%{?rhel} == 5
%global el5 1
%endif

%if %{has_ostree}
%define install_ostree INSTALL_OSTREE_PLUGIN=true
%else
%define install_ostree INSTALL_OSTREE_PLUGIN=false
%endif

# makefile will guess, but be specific.
%if %{use_gtk3}
%define gtk_version GTK_VERSION=3
%else
%define gtk_version GTK_VERSION=2
%endif

%if %{use_initial_setup}
%define post_boot_tool INSTALL_INITIAL_SETUP=true INSTALL_FIRSTBOOT=false
%else
%define post_boot_tool INSTALL_INITIAL_SETUP=false INSTALL_FIRSTBOOT=true
%endif

# makefile defaults to INSTALL_YUM_PLUGIN=true
%define install_yum_plugins INSTALL_YUM_PLUGINS=true

# makefile defaults to INSTALL_DNF_PLUGIN=false
%if %{use_dnf}
%define install_dnf_plugins INSTALL_DNF_PLUGINS=true
%else
%define install_dnf_plugins INSTALL_DNF_PLUGINS=false
%endif

%define subman_install_dir %{_datadir}/rhsm/subscription_manager
%define rct_install_dir %{_datadir}/rhsm/rct
%define rhsm_debug_install_dir %{_datadir}/rhsm/rhsm_debug

Name: subscription-manager
Version: 1.17.4
Release: 1%{?dist}
Summary: Tools and libraries for subscription and repository management
Group:   System Environment/Base
License: GPLv2

# How to create the source tarball:
#
# git clone https://github.com/candlepin/subscription-manager.git
# yum install tito
# tito build --tag subscription-manager-$VERSION-$RELEASE --tgz
Source0: %{name}-%{version}.tar.gz
URL:     http://www.candlepinproject.org/
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:  python-ethtool
Requires:  python-iniparse
Requires:  virt-what
Requires:  python-rhsm >= 1.17.0
Requires:  dbus-python
Requires:  python-slip
Requires:  yum >= 3.2.29-73
Requires:  usermode
Requires:  python-dateutil
%if %use_gtk3
Requires: gobject-introspection
Requires: pygobject3-base
%else
Requires:  pygobject2
%endif

# There's no dmi to read on these arches, so don't pull in this dep.
%ifnarch ppc ppc64 s390 s390x
Requires:  python-dmidecode
%endif

%if %use_systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
%else
Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
%endif

BuildRequires: python-devel
BuildRequires: gettext
BuildRequires: intltool
BuildRequires: libnotify-devel
BuildRequires: desktop-file-utils
BuildRequires: redhat-lsb
BuildRequires: scrollkeeper
BuildRequires: GConf2-devel
%if %use_gtk3
BuildRequires: gtk3-devel
%else
BuildRequires: gtk2-devel
%endif
%if %use_systemd
# We need the systemd RPM macros
BuildRequires: systemd
%endif


%description
The Subscription Manager package provides programs and libraries to allow users
to manage subscriptions and yum repositories from the Red Hat entitlement
platform.


%if %has_ostree
%package -n subscription-manager-plugin-ostree
Summary: A plugin for handling OSTree content.
Group: System Environment/Base

Requires: pygobject3-base
# plugin needs a slightly newer version of python-iniparse for 'tidy'
Requires:  python-iniparse >= 0.4
Requires: %{name} = %{version}-%{release}

%description -n subscription-manager-plugin-ostree
Enables handling of content of type 'ostree' in any certificates
from the server. Populates /ostree/repo/config as well as updates
the remote in the currently deployed .origin file.

%files -n subscription-manager-plugin-ostree
%defattr(-,root,root,-)
%{_sysconfdir}/rhsm/pluginconf.d/ostree_content.OstreeContentPlugin.conf
%{rhsm_plugins_dir}/ostree_content.py*
%{subman_install_dir}/plugin/ostree/*.py*
%endif

%package -n subscription-manager-plugin-container
Summary: A plugin for handling container content.
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}

%description -n subscription-manager-plugin-container
Enables handling of content of type 'containerImage' in any certificates
from the server. Populates /etc/docker/certs.d appropriately.

%files -n subscription-manager-plugin-container
%defattr(-,root,root,-)
%{_sysconfdir}/rhsm/pluginconf.d/container_content.ContainerContentPlugin.conf
%{rhsm_plugins_dir}/container_content.py*
%{subman_install_dir}/plugin/container.py*
# Copying Red Hat CA cert into each directory:
%attr(755,root,root) %dir %{_sysconfdir}/docker/certs.d/cdn.redhat.com
%attr(644,root,root) %{_sysconfdir}/rhsm/ca/redhat-entitlement-authority.pem
%attr(644,root,root) %{_sysconfdir}/docker/certs.d/cdn.redhat.com/redhat-entitlement-authority.crt

%package -n subscription-manager-gui
Summary: A GUI interface to manage Red Hat product subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}

# We need pygtk3 and gtk2 until rhsm-icon is ported to gtk3
%if %use_gtk3
Requires: pygobject3
Requires: gtk3
%else
Requires: pygtk2 pygtk2-libglade
%endif
Requires: usermode-gtk
Requires: dbus-x11
Requires: gnome-icon-theme
Requires(post): scrollkeeper
Requires(postun): scrollkeeper

# Renamed from -gnome, so obsolete it properly
Obsoletes: %{name}-gnome < 1.0.3-1
Provides: %{name}-gnome = %{version}-%{release}

# Fedora can figure this out automatically, but RHEL cannot:
# See #987071
Requires: librsvg2%{?_isa}

%description -n subscription-manager-gui
This package contains a GTK+ graphical interface for configuring and
registering a system with a Red Hat Entitlement platform and manage
subscriptions.

%if %use_firstboot
%package -n subscription-manager-firstboot
Summary: Firstboot screens for subscription manager
Group: System Environment/Base
Requires: %{name}-gui = %{version}-%{release}
Requires: rhn-setup-gnome

# Fedora can figure this out automatically, but RHEL cannot:
Requires: librsvg2

%description -n subscription-manager-firstboot
This package contains the firstboot screens for subscription-manager.
%endif

%if %use_initial_setup
%package -n subscription-manager-initial-setup-addon
Summary: initial-setup screens for subscription-manager
Group: System Environment/Base
Requires: %{name}-gui = %{version}-%{release}
Requires: initial-setup-gui >= 0.3.9.24-1
Obsoletes: subscription-manager-firstboot < 1.15.3-1

%description -n subscription-manager-initial-setup-addon
This package contains the initial-setup screens for subscription-manager.
%endif

%package -n subscription-manager-migration
Summary: Migration scripts for moving to certificate based subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}
Requires: rhnlib

# Since the migration data package is not in Fedora, we can only require it
# on RHEL.
%if 0%{?rhel}
Requires: subscription-manager-migration-data
%endif

%description -n subscription-manager-migration
This package contains scripts that aid in moving to certificate based
subscriptions

%if %use_dnf
%package -n dnf-plugin-subscription-manager
Summary: Subscription Manager plugins for DNF
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}
Requires: dnf >= 1.0.0

%description -n dnf-plugin-subscription-manager
Subscription Manager plugins for DNF, contains subscription-manager and product-id plugins.
%endif

%prep
%setup -q

%build
make -f Makefile VERSION=%{version}-%{release} CFLAGS="%{optflags}" \
    LDFLAGS="%{__global_ldflags}" OS_DIST="%{dist}" %{?gtk_version}

%install
rm -rf %{buildroot}
make -f Makefile install VERSION=%{version}-%{release} \
    PREFIX=%{buildroot} MANPATH=%{_mandir} PYTHON_SITELIB=%{python_sitelib} \
    OS_VERSION=%{?fedora}%{?rhel} OS_DIST=%{dist} \
    %{?install_ostree} %{?post_boot_tool} %{?gtk_version} \
    %{?install_yum_plugins} %{?install_dnf_plugins}

desktop-file-validate \
        %{buildroot}/etc/xdg/autostart/rhsm-icon.desktop

desktop-file-validate \
        %{buildroot}/usr/share/applications/subscription-manager-gui.desktop

%find_lang rhsm
%find_lang %{name} --with-gnome

# fix timestamps on our byte compiled files so them match across arches
find %{buildroot} -name \*.py -exec touch -r %{SOURCE0} '{}' \;

# fake out the redhat.repo file
mkdir %{buildroot}%{_sysconfdir}/yum.repos.d
touch %{buildroot}%{_sysconfdir}/yum.repos.d/redhat.repo

# fake out the certificate directories
mkdir -p %{buildroot}%{_sysconfdir}/pki/consumer
mkdir -p %{buildroot}%{_sysconfdir}/pki/entitlement

# Setup cert directories for the container plugin:
mkdir -p %{buildroot}%{_sysconfdir}/docker/certs.d/
mkdir %{buildroot}%{_sysconfdir}/docker/certs.d/cdn.redhat.com
install -m 644 %{_builddir}/%{buildsubdir}/etc-conf/redhat-entitlement-authority.pem %{buildroot}%{_sysconfdir}/docker/certs.d/cdn.redhat.com/redhat-entitlement-authority.crt

# The normal redhat-uep.pem is actually a bundle of three CAs.  Docker does not handle bundles well
# and only reads the first CA in the bundle.  We need to put the right CA a file by itself.
mkdir -p %{buildroot}%{_sysconfdir}/etc/rhsm/ca
install -m 644 %{_builddir}/%{buildsubdir}/etc-conf/redhat-entitlement-authority.pem %{buildroot}/%{_sysconfdir}/rhsm/ca/redhat-entitlement-authority.pem

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

# base/cli tools use the gettext domain 'rhsm', while the
# gnome-help tools use domain 'subscription-manager'
%files -f rhsm.lang
%defattr(-,root,root,-)

# executables
%attr(755,root,root) %{_sbindir}/subscription-manager

# symlink to console-helper
%{_bindir}/subscription-manager
%attr(755,root,root) %{_bindir}/rhsmcertd

%attr(755,root,root) %{_libexecdir}/rhsmcertd-worker
%attr(755,root,root) %{_libexecdir}/rhsmd

# init scripts and systemd services
%if %use_systemd
    %attr(644,root,root) %{_unitdir}/rhsmcertd.service
    %attr(644,root,root) %{_tmpfilesdir}/%{name}.conf
%else
    %attr(755,root,root) %{_initrddir}/rhsmcertd
%endif

# our config dirs and files
%attr(755,root,root) %dir %{_sysconfdir}/rhsm
%attr(644,root,root) %config(noreplace) %{_sysconfdir}/rhsm/rhsm.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/rhsm/logging.conf

%attr(755,root,root) %dir %{_sysconfdir}/rhsm/facts

%attr(755,root,root) %dir %{_sysconfdir}/pki/consumer
%attr(755,root,root) %dir %{_sysconfdir}/pki/entitlement

# PAM config
%{_sysconfdir}/pam.d/subscription-manager
%{_sysconfdir}/security/console.apps/subscription-manager

# remove the repo file when we are deleted
%ghost %{_sysconfdir}/yum.repos.d/redhat.repo

# yum plugin config
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/subscription-manager.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/product-id.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/search-disabled-repos.conf

# misc system config
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/logrotate.d/subscription-manager
%attr(700,root,root) %{_sysconfdir}/cron.daily/rhsmd

# This doesn't use systemd dbus activation yet
%{_datadir}/dbus-1/system-services/com.redhat.SubscriptionManager.service

# /var
%attr(755,root,root) %dir %{_var}/log/rhsm
%attr(755,root,root) %dir %{_var}/spool/rhsm/debug
%attr(755,root,root) %dir %{_var}/run/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm/facts
%attr(755,root,root) %dir %{_var}/lib/rhsm/packages
%attr(755,root,root) %dir %{_var}/lib/rhsm/cache

# bash completion scripts
%{_sysconfdir}/bash_completion.d/subscription-manager
%{_sysconfdir}/bash_completion.d/rct
%{_sysconfdir}/bash_completion.d/rhsm-debug
%{_sysconfdir}/bash_completion.d/rhn-migrate-classic-to-rhsm
%{_sysconfdir}/bash_completion.d/rhsm-icon
%{_sysconfdir}/bash_completion.d/rhsmcertd


# code
# python package dirs
%dir %{subman_install_dir}
%dir %{subman_install_dir}/api
%dir %{subman_install_dir}/branding
%dir %{subman_install_dir}/model
%dir %{subman_install_dir}/plugin


# code, python modules and packages
%{subman_install_dir}/*.py*

%{subman_install_dir}/api/*.py*
%{subman_install_dir}/branding/*.py*

# our gtk2/gtk3 compat modules
%dir %{subman_install_dir}/ga_impls
%{subman_install_dir}/ga_impls/__init__.py*

%if %use_gtk3
%{subman_install_dir}/ga_impls/ga_gtk3.py*
%else
%dir %{subman_install_dir}/ga_impls/ga_gtk2
%{subman_install_dir}/ga_impls/ga_gtk2/*.py*
%endif

%{subman_install_dir}/model/*.py*

%{subman_install_dir}/plugin/*.py*

# subscription-manager plugins
%dir %{rhsm_plugins_dir}
%dir %{_sysconfdir}/rhsm/pluginconf.d

# yum plugins
# Using _prefix + lib here instead of libdir as that evaluates to /usr/lib64 on x86_64,
# but yum plugins seem to normally be sent to /usr/lib/:
%{_prefix}/lib/yum-plugins/subscription-manager.py*
%{_prefix}/lib/yum-plugins/product-id.py*
%{_prefix}/lib/yum-plugins/search-disabled-repos.py*

# Incude rt CLI tool
%dir %{rct_install_dir}
%{rct_install_dir}/__init__.py*
%{rct_install_dir}/cli.py*
%{rct_install_dir}/*commands.py*
%{rct_install_dir}/printing.py*
%{rct_install_dir}/version.py*
%attr(755,root,root) %{_bindir}/rct

# Include consumer debug CLI tool
%dir %{rhsm_debug_install_dir}
%{rhsm_debug_install_dir}/__init__.py*
%{rhsm_debug_install_dir}/cli.py*
%{rhsm_debug_install_dir}/*commands.py*
%attr(755,root,root) %{_bindir}/rhsm-debug

# base rhsmlib
%dir %{python_sitearch}/rhsmlib
%{python_sitearch}/rhsmlib/*.py*

# facts modules, so to sitelib
%dir %{python_sitearch}/rhsmlib/facts
%{python_sitearch}/rhsmlib/facts/*.py*

# compat modules, so to sitelib
%dir %{python_sitearch}/rhsmlib/compat
%{python_sitearch}/rhsmlib/compat/*.py*

# candlepin api helper modules, so to sitelib
%dir %{python_sitearch}/rhsmlib/candlepin
%{python_sitearch}/rhsmlib/candlepin/*.py*

# dbus modules
%dir %{python_sitearch}/rhsmlib/dbus
%dir %{python_sitearch}/rhsmlib/dbus/clients
%dir %{python_sitearch}/rhsmlib/dbus/services
%dir %{python_sitearch}/rhsmlib/dbus/common

# dbus common and base modules
%{python_sitearch}/rhsmlib/dbus/*.py*
%{python_sitearch}/rhsmlib/dbus/services/*.py*
%{python_sitearch}/rhsmlib/dbus/common/*.py*

# dbus facts services
%config(noreplace) %{_sysconfdir}/dbus-1/system.d/com.redhat.*.conf
%{_datadir}/polkit-1/actions/com.redhat.*.policy
%attr(755,root,root) %{_libexecdir}/rhsm-*-service
# dbus activation services for systemd
%if %use_systemd
    # TODO: These assume systemd. Need versions for rhel6 as well.
    %{_datadir}/dbus-1/system-services/com.redhat.*.service
    %{_unitdir}/rhsm-*.service
%endif

%dir %{python_sitearch}/rhsmlib/dbus/services/facts
%{python_sitearch}/rhsmlib/dbus/services/facts/*.py*

%dir %{python_sitearch}/rhsmlib/dbus/services/subscriptions
%{python_sitearch}/rhsmlib/dbus/services/subscriptions/*.py*

%dir %{python_sitearch}/rhsmlib/dbus/services/examples
%{python_sitearch}/rhsmlib/dbus/services/examples/*.py*

# dbus client
%{python_sitearch}/rhsmlib/dbus/clients/*.py*

# dbus facts client
%dir %{python_sitearch}/rhsmlib/dbus/clients/facts
%{python_sitearch}/rhsmlib/dbus/clients/facts/*.py*


%doc
%{_mandir}/man8/subscription-manager.8*
%{_mandir}/man8/rhsmcertd.8*
%{_mandir}/man8/rct.8*
%{_mandir}/man8/rhsm-debug.8*
%{_mandir}/man5/rhsm.conf.5*
%doc LICENSE


%files -n subscription-manager-gui -f subscription-manager.lang
%defattr(-,root,root,-)
%attr(755,root,root) %{_sbindir}/subscription-manager-gui
# symlink to console-helper
%{_bindir}/subscription-manager-gui
%{_bindir}/rhsm-icon
%dir %{subman_install_dir}/gui
%dir %{subman_install_dir}/gui/data
%dir %{subman_install_dir}/gui/data/ui
%dir %{subman_install_dir}/gui/data/glade
%dir %{subman_install_dir}/gui/data/icons
%{subman_install_dir}/gui/data/ui/*.ui
%{subman_install_dir}/gui/data/glade/*.glade
%{subman_install_dir}/gui/data/icons/*.svg
%{_datadir}/applications/subscription-manager-gui.desktop
%{_datadir}/icons/hicolor/16x16/apps/*.png
%{_datadir}/icons/hicolor/22x22/apps/*.png
%{_datadir}/icons/hicolor/24x24/apps/*.png
%{_datadir}/icons/hicolor/32x32/apps/*.png
%{_datadir}/icons/hicolor/48x48/apps/*.png
%{_datadir}/icons/hicolor/96x96/apps/*.png
%{_datadir}/icons/hicolor/256x256/apps/*.png
%{_datadir}/icons/hicolor/scalable/apps/*.svg
%{_datadir}/appdata/subscription-manager-gui.appdata.xml

# code and modules
%{subman_install_dir}/gui/*.py*

# gui system config files
%{_sysconfdir}/xdg/autostart/rhsm-icon.desktop
%{_sysconfdir}/pam.d/subscription-manager-gui
%{_sysconfdir}/security/console.apps/subscription-manager-gui
%{_sysconfdir}/bash_completion.d/subscription-manager-gui

%doc
%{_mandir}/man8/subscription-manager-gui.8*
%{_mandir}/man8/rhsm-icon.8*
%doc LICENSE


%if %use_initial_setup
%files -n subscription-manager-initial-setup-addon
%defattr(-,root,root,-)
%dir %{_datadir}/anaconda/addons/com_redhat_subscription_manager/
%dir %{_datadir}/anaconda/addons/com_redhat_subscription_manager/gui/
%dir %{_datadir}/anaconda/addons/com_redhat_subscription_manager/gui/spokes/
%dir %{_datadir}/anaconda/addons/com_redhat_subscription_manager/categories/
%dir %{_datadir}/anaconda/addons/com_redhat_subscription_manager/ks/
%{_datadir}/anaconda/addons/com_redhat_subscription_manager/*.py*
%{_datadir}/anaconda/addons/com_redhat_subscription_manager/gui/*.py*
%{_datadir}/anaconda/addons/com_redhat_subscription_manager/gui/spokes/*.ui
%{_datadir}/anaconda/addons/com_redhat_subscription_manager/gui/spokes/*.py*
%{_datadir}/anaconda/addons/com_redhat_subscription_manager/categories/*.py*
%{_datadir}/anaconda/addons/com_redhat_subscription_manager/ks/*.py*
%endif

%if %use_firstboot
%files -n subscription-manager-firstboot
%defattr(-,root,root,-)
%{_datadir}/rhn/up2date_client/firstboot/rhsm_login.py*
%endif

%files -n subscription-manager-migration
%defattr(-,root,root,-)
%dir %{subman_install_dir}/migrate
%{subman_install_dir}/migrate/*.py*
%attr(755,root,root) %{_sbindir}/rhn-migrate-classic-to-rhsm

%doc
%{_mandir}/man8/rhn-migrate-classic-to-rhsm.8*
%doc LICENSE
#only install this file on Fedora
%if 0%{?fedora} > 14
%doc README.Fedora
%endif

%if %use_dnf
%files -n dnf-plugin-subscription-manager
%defattr(-,root,root,-)
%{python_sitelib}/dnf-plugins/*
%endif

%post
%if %use_systemd
    /bin/systemctl enable rhsmcertd.service >/dev/null 2>&1 || :
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
    /bin/systemctl try-restart rhsmcertd.service >/dev/null 2>&1 || :
%else
    chkconfig --add rhsmcertd
%endif

if [ -x /bin/dbus-send ] ; then
  dbus-send --system --type=method_call --dest=org.freedesktop.DBus / org.freedesktop.DBus.ReloadConfig > /dev/null 2>&1 || :
fi

%if !%use_systemd
    if [ "$1" -eq "2" ] ; then
        /sbin/service rhsmcertd condrestart >/dev/null 2>&1 || :
    fi
%endif

%preun
if [ $1 -eq 0 ] ; then
    %if %use_systemd
        %systemd_preun rhsmcertd.service
    %else
        /sbin/service rhsmcertd stop >/dev/null 2>&1
        /sbin/chkconfig --del rhsmcertd
    %endif

    if [ -x /bin/dbus-send ] ; then
        dbus-send --system --type=method_call --dest=org.freedesktop.DBus / org.freedesktop.DBus.ReloadConfig > /dev/null 2>&1 || :
    fi
fi

%postun
%if %use_systemd
    %systemd_postun_with_restart rhsmcertd.service
%endif

%changelog
* Thu Mar 31 2016 Alex Wood <awood@redhat.com> 1.17.4-1
- 1315859: Only show one proxy dialog (csnyder@redhat.com)
- 1309553: Stylish fixes for consumer fixes (csnyder@redhat.com)
- 1313631: Registration with one environment proceeds as normal
  (csnyder@redhat.com)

* Thu Mar 10 2016 Alex Wood <awood@redhat.com> 1.17.3-1
- 1304427: Fixes system path to properly import from module
  subscription_manager (csnyder@redhat.com)
- 1266935: Turn sub-man logging to INFO level. (awood@redhat.com)
- register screen -> reg screen and pkg profile (alikins@redhat.com)
- 1264964: Always use cert auth for package profile (alikins@redhat.com)
- 1309553: Do not fail on check for consumer["type"]["manifest"]
  (csnyder@redhat.com)
- 1304680: Include error detail in message (wpoteat@redhat.com)
- 1312367: Progress bar needs to go away on repo update connection fail
  (wpoteat@redhat.com)
- 1311935: Emits register-message instead of register-error for display of user
  errors (csnyder@redhat.com)
- 1302564: Push 'Done' box as close to center of firstboot page as possible
  (wpoteat@redhat.com)
- 1308523: Navigation buttons sensitivity matches the current_screen.ready
  (csnyder@redhat.com)
- 1302775: Navigate through all rhsm firstboot screens (csnyder@redhat.com)
- 1304280: Tab stop needed on cancel button (wpoteat@redhat.com)
- 1303092: GUI issues in Repos and Help (wpoteat@redhat.com)

* Fri Feb 19 2016 Alex Wood <awood@redhat.com> 1.17.2-1
- 1308732: Leave hw fact virt.uuid unset if unknown (alikins@redhat.com)
- 1290885: Display formatted error if no DISPLAY exists. (awood@redhat.com)

* Mon Feb 01 2016 Christopher Snyder <csnyder@redhat.com> 1.17.1-1
- 1300259: Select service level label no longer overlaps dropdown box
  (csnyder@redhat.com)
- 1220283: Choose server text no longer overlapped by icon.
  (csnyder@redhat.com)
- 1300816: Add proc_cpuinfo facts for ppc64/le (alikins@redhat.com)
- 1300791: Update man page footers (wpoteat@redhat.com)
- 1300805: Add support for ppc64 virt.uuid (alikins@redhat.com)

* Tue Jan 19 2016 Christopher Snyder <csnyder@redhat.com> 1.16.8-1
- 1298586: Message needed for remove only invalid pool (wpoteat@redhat.com)
- 1046132: rhsm_icon uses status from check_status (alikins@redhat.com)
- 1282961: Update yum version to current RHEL 6.8 one (wpoteat@redhat.com)
- 1046132: rhsm-icon pops up at annoying times - a second attempt
  (vrjain@redhat.com)
- 1298327: Handles exception in repolib (csnyder@redhat.com)
- 1297313: Fixed layout issues with the repository management dialog on GTK2
  (ceiu@cericlabs.com)
- 1292038: Changed adjustments to GtkAdjustment objects
- 1292013: Retain reference to backend for use in proxy config
  (csnyder@redhat.com)

* Fri Jan 08 2016 Alex Wood <awood@redhat.com> 1.16.7-1
- 1263037: Change RHSM Icon reporting of unregistered system
  (wpoteat@redhat.com)
- 1283749: Upgrade the dialogs to error when required fields are blank.
  (wpoteat@redhat.com)
- 1222627: Allows removal of product certs with no active repos, given
  temp_disabled_repos (csnyder@redhat.com)
- 1163398: Modify icon-rhsm man page to reflect the help text
  (wpoteat@redhat.com)
- Install docs with mode 644 (csnyder@redhat.com)
- 1288626: Does not report pool ids as serial numbers, ignore duplicates
  (csnyder@redhat.com)
- 1061407: Avoid unwanted translations for subscription-manager by string
  substitutions (wpoteat@redhat.com)
- Output of errors now goes to stderr (csnyder@redhat.com)
- Use matches string to highlight the field(s) containing the match
  (wpoteat@redhat.com)

* Fri Dec 04 2015 Alex Wood <awood@redhat.com> 1.16.6-1
- 1285004: Adds check for access to the required manager capabilty
  (csnyder@redhat.com)
- 1278472: Change default registration url to subscription.rhsm.redhat.com
  (wpoteat@redhat.com)
- 1275179: Do not allow quantity with auto attach (wpoteat@redhat.com)
- 976859: Only check server version if asked. (alikins@redhat.com)
- 1195003: Subscription manager man page mention of wild cards for repo enable
  (wpoteat@redhat.com)
- Use the stock 'close' button for close button. (alikins@redhat.com)

* Thu Oct 15 2015 Alex Wood <awood@redhat.com> 1.16.4-1
- 1264964: Ignore uuid=None on package sync (alikins@redhat.com)
- Set register-status in RegisterInfo init. (alikins@redhat.com)
- Add glade for selectsla combobox for rhel6 (alikins@redhat.com)
- 1254460: Fixed the credits button in the about dialog in subman GUI
  (crog@redhat.com)
- 1192120: Fixed remaining instances of "reregister" in the man pages
  (crog@redhat.com)
- 1270204: Crash report no longer sent when widget is none (csnyder@redhat.com)
- Cancel button is now labelled "Close" (csnyder@redhat.com)
- 1268088: Changes the rhsm spoke display message to end with "registered"
  (csnyder@redhat.com)
- Use class methods instead of redundant ad-hoc methods. (alikins@redhat.com)
- 1251853: Fix errors if "manage_repos = " in cfg (alikins@redhat.com)
- 1268102: Stop main window from opening duplicate dialogs. (awood@redhat.com)
- 1268095: Replace SLA radio buttons w/ combobox (alikins@redhat.com)
- 1268060: Add 'cancel' back to s-m-gui register. (alikins@redhat.com)
- 1268028: Fix skipped auto attach in registergui (alikins@redhat.com)
- 1266929: Fix bug with exception reporting in register dialog.
  (awood@redhat.com)
- 1266480: Refresh TreeView selection after subscriptions are removed.
  (awood@redhat.com)
- Allow 'back' to go back multiple times. (alikins@redhat.com)
- 1267034: Handle 401 with cert based auth (alikins@redhat.com)
- 1262075,1267179: Fix back/cancel nav (alikins@redhat.com)
- 1267287: Fix allsubs tab ui regression (alikins@redhat.com)
- 1266994: Use our icon for initial-setup spoke icon (alikins@redhat.com)
- 1261006: Handle multiple nav button clicks (alikins@redhat.com)
- 1242998, 1254550: Fix "already reg'ed" in initial-setup (alikins@redhat.com)
- 1265347, 1265371: Added translation updates and corrections from 1.15.X
  (crog@redhat.com)

* Fri Sep 25 2015 Alex Wood <awood@redhat.com> 1.16.3-1
- 1249012: fix start-end date original color (vrjain@redhat.com)
- 884288: Make register widgets handle resizing. (alikins@redhat.com)
- 1185958: Quieter ostree plugin sans ostree (alikins@redhat.com)
- 1168268: Add rhsm.conf proxy info to ostree repo (alikins@redhat.com)
- 1249012: Start-End Date of expired subscription is now in red status
  (vrjain@redhat.com)
- 1262989: Fix unregister action when consumer is already 'Gone' on server
  (fnguyen@redhat.com)
- 1262919: Added convenience function for printing to stderr (crog@redhat.com)
- Add a note about GoneException handling. (alikins@redhat.com)
- Fixed error message, removed mention of ghost --refresh (vrjain@redhat.com)
- Delete the 'release' status cache on clean all. (alikins@redhat.com)
- Fixed error message, removed mention of ghost --refresh (vrjain@redhat.com)
- 1248833: Ensure the displayMessage is displayed regardless of success or
  failure (csnyder@redhat.com)
- 1254550: Fix activation key usage in gui. (alikins@redhat.com)
- Re-initialize() RegisterWidget on RegDialog show (alikins@redhat.com)
- 1257943:Adding a warning to repo-override command when manage_repos = 0
  (fnguyen@redhat.com)
- 1251853: Manage repos config entry needs to allow blank value
  (wpoteat@redhat.com)

* Wed Sep 02 2015 Alex Wood <awood@redhat.com> 1.16.2-1
- 884288: Better registergui for initial-setup (alikins@redhat.com)
- 1254349: move Resgistering to message (vrjain@redhat.com)
- 1257460: Set text domain on Gtk.Builder widgets (alikins@redhat.com)
- 1246680: Hide rhsm-debug --subscriptions options (alikins@redhat.com)
- Set help file name for the Subscription Manager spoke
  (martin.kolman@gmail.com)
- 1246680: Remove subscriptions from rhsm-debug (wpoteat@redhat.com)
- Enabled help options on first tab (seanokeeffe797@gmail.com)
- 1207247: Insecure parameter needs more explanation (wpoteat@redhat.com)
- 1253275: Fix initial-setup ks mode (alikins@redhat.com)
- Stopped --consumerid = distributor id (vrjain@redhat.com)
- 1246429: Stop spinbutton from blocking quantity (alikins@redhat.com)
- 1185958: Remove ostree plugins req on ostree (alikins@redhat.com)
- Do not allow using --force with --consumerid (vrjain@redhat.com)
- 1141128: Subscriptions need refresh after imported cert removed
  (wpoteat@redhat.com)
- x86_64 and aarch /proc/cpuinfo module (alikins@redhat.com)

* Thu Aug 13 2015 Alex Wood <awood@redhat.com> 1.16.1-1
- 1150150: Ostree update report should log updates in proper section
  (wpoteat@redhat.com)
- 1141128: Clean up and correct for style (wpoteat@redhat.com)
- 1251610: Port and prefix were reversed in connection URL statement
  (wpoteat@redhat.com)
- 1141128: Imported certificate in detatched scenario not getting deleted
  (wpoteat@redhat.com)
- 1240553: Fix detection of cert dir changes (alikins@redhat.com)
- Fixing All Subscriptions layout issues (mstead@redhat.com)
- 1221273: Auto-attach failure should not short-circuit other parts of
  registration (wpoteat@redhat.com)
- Remove use of Widget.is_toplevel() (alikins@redhat.com)
- Require initial-setup >= 0.3.9.24, no fb on el7 (alikins@redhat.com)
- Fix spec file build errors (alikins@redhat.com)
- search-disabled-repos: ignore failed temporarily enabled repos
  (vmukhame@redhat.com)
- search-disabled-repos: replace CLI with API calls for enabling repos
  permanently (vmukhame@redhat.com)
- Add new api package to RPM. (awood@redhat.com)
- Turn off ga loading debug messages. (alikins@redhat.com)
- Specify a thread name for any threads we start. (alikins@redhat.com)
- 1248746: Fix layout of contract dialog (GTK3) (mstead@redhat.com)
- 1248821: Add Gtk.Window to ga_gtk2.Gtk (alikins@redhat.com)
- 1248821: All subs date picker was failing. (alikins@redhat.com)
- 1249053: Fixed layout/blank button issues on owner selection dialog
  (mstead@redhat.com)
- 1248729: All subs filter dialog was not focused. (alikins@redhat.com)
- 1248664: Fix GtkAdjustment related warnings (alikins@redhat.com)
- 1248546: Slightly better looking done screen. (alikins@redhat.com)
- 1243704: Goto error screen on 'cancel' (alikins@redhat.com)
- 1245557: Fix release and service level preferences (alikins@redhat.com)
- Add GTK_COMPAT_VERSION to ga_gtk2/gtk_compat (alikins@redhat.com)
- 1248773: Fixed proxy dialog layout (GTK3) (mstead@redhat.com)
- 1248771: Fixing activation key dialog layout (GTK3) (mstead@redhat.com)
- 1247723: Fixed layout issues in Facts dialog (GTK3) (mstead@redhat.com)
- 1245283: Properly initialize AutobindWizard when auto-attach is clicked
  (mstead@redhat.com)
- 1248546: Refine the aesthics of register dialog. (alikins@redhat.com)
- 1243260: Make proxy config dialog work. (alikins@redhat.com)
- 1161157,1155954: Improve performance of Repository Dialog (mstead@redhat.com)
- 1185958: Make ostree plugin depend on ostree. (alikins@redhat.com)
- 1165771: make content plugins require subman (alikins@redhat.com)
- Move gtk_compat features to sub ga module. (alikins@redhat.com)
- Use idle_add from ga_Object for 6.x (alikins@redhat.com)
- Updated initial-setup-addon package requirement to initial-setup-gui
  (crog@redhat.com)
- Only build initial-setup rpm on rhel > 7.1 (alikins@redhat.com)

* Fri Jul 24 2015 Alex Wood <awood@redhat.com> 1.16.0-1
- Bump version to 1.16 (crog@redhat.com)
- Changed initial-setup-addon package requirement from subman to subman-gui
  (crog@redhat.com)
- Cast product.id to int for sort in cat-cert (alikins@redhat.com)
- 1136163: Ignore pythonpath to avoid selinux AVCs (alikins@redhat.com)
- 985157: Display the URL that is the registration target (wpoteat@redhat.com)
- 1234413: lower log level of rhsmd RHN messages (alikins@redhat.com)

* Fri Jul 10 2015 Chris Rog <crog@redhat.com> 1.15.7-1
- Merge pull request #1219 from candlepin/alikins/1241247_ga_ImportError
  (ceiu@cericlabs.com)
- Merge pull request #1211 from candlepin/awood/1232232-enable-repos
  (alikins@redhat.com)
- 1241247: Fix ga ImportError in rhsmcertd (alikins@redhat.com)
- Merge pull request #1214 from
  candlepin/alikins/prevent_nose_loading_ga_impls_directly (awood@redhat.com)
- Add comment about the request_injection decorator. (awood@redhat.com)
- Prevent nose looking for tests in sub_manager/ (alikins@redhat.com)
- Remove assertIn as that test is not in Python 2.6. (awood@redhat.com)
- Move API dependency injection out of module scope. (awood@redhat.com)
- 1232232: Add supported API to enable content repositories. (awood@redhat.com)

* Wed Jul 08 2015 Chris Rog <crog@redhat.com> 1.15.6-1
- 1241184: Updated Makefile to prevent version string clobbering
  (crog@redhat.com)

* Tue Jul 07 2015 Adrian Likins <alikins@redhat.com> 1.15.5-1
- 1240801: Use latest initial-setup API (alikins@redhat.com)

* Tue Jul 07 2015 Adrian Likins <alikins@redhat.com> 1.15.4-1
- Make initial-setup rpm Obsolete firstboot rpm. (alikins@redhat.com)

* Mon Jul 06 2015 Adrian Likins <alikins@redhat.com> 1.15.3-1
- 1232508: file_monitor is no longer a gobject (alikins@redhat.com)
- Add 'subscription-manager-initial-setup-addon' sub package (alikins@redhat.com)
- Make 'subscription-manager-firstboot' optional (alikins@redhat.com)
- Make 'firstboot' and 'initial-setup' RHEL version dependent (alikins@redhat.com)
- Add initial-setup modules. (alikins@redhat.com)
- Port gui from gtk2 to gtk3 via 'ga' (alikins@redhat.com)
- Make gui support gtk2 and gtk3 (alikins@redhat.com)
- Add module 'ga' ('gtk any') as Gtk ver abstraction (alikins@redhat.com)
- Add search-disabled-repos plugin. (vmukhame@redhat.com)

* Mon Jun 22 2015 Chris Rog <crog@redhat.com> 1.15.2-1
- Added release target for RHEL 7.2 (crog@redhat.com)
- Move po compile/install for faster 'install-files' (alikins@redhat.com)
- Stop using deprecated Tito settings. (awood@redhat.com)

* Thu Jun 11 2015 Alex Wood <awood@redhat.com> 1.15.1-1
- Don't try to set file attrs on symlinks in spec (alikins@redhat.com)
- 1228807: Make disabling proxy via gui apply (alikins@redhat.com)
- Use find_lang --with-gnome for the gnome help (alikins@redhat.com)
- Cast return daemon() to void to quiet warnings. (alikins@redhat.com)
- Make the 'compile-po' step in the build quiet. (alikins@redhat.com)
- Make desktop-file-validate warnings. (alikins@redhat.com)
- rpm spec file reorg (alikins@redhat.com)
- 1224806: Prevent yum blocking on rhsm locks (alikins@redhat.com)
- 1092564: Add LDFLAGS to makefile so RPM can modify them. (awood@redhat.com)
- Update registergui.py (wpoteat@redhat.com)
- Bump version to 1.15 (wpoteat@redhat.com)
- Remove spurious debug logging about content labels (alikins@redhat.com)
- Revert "1189953: Replaced usage of "startup" with "start-up""
  (crog@redhat.com)
- Revert "1149098: Removed uses of the non-word "unregister"" (crog@redhat.com)
- Revert "1189937: Added hypens to instances of the non-word "wildcard""
  (crog@redhat.com)
- Revert "1200507: Hyphenated uses of the non-word "plugin."" (crog@redhat.com)
- 1225435: Use LC_ALL instead of LANG for lscpu. (alikins@redhat.com)
- Remove mutable default args in stubs (alikins@redhat.com)
- Add notes about how register/firstboot interact. (alikins@redhat.com)
- 1189953: Replaced usage of "startup" with "start-up" (crog@redhat.com)
- 1194453: Fixed typos and grammar issues in the rhsmcertd man page
  (crog@redhat.com)
- 1192646: Fixed typos and grammar issues in the RHSM conf man page
  (crog@redhat.com)
- 1192574: Fixed typos and grammar issues in subman GUI man page
  (crog@redhat.com)
- 1192120: Fixed typos and grammar issues in subman man page (crog@redhat.com)
- 1192094: Fixed erroneous usage of "servicelevel" for the subman command
  (crog@redhat.com)
- 1194468: Fixed typos and grammar in rhsm-debug man page (crog@redhat.com)
- 1193991: Fixed typos and header for RCT man page. (crog@redhat.com)
- 1200507: Hyphenated uses of the non-word "plugin." (crog@redhat.com)
- 1189946: Removed extraneous hyphens from instances of "pre-configure"
  (crog@redhat.com)
- 1189937: Added hypens to instances of the non-word "wildcard"
  (crog@redhat.com)
- 1149098: Removed uses of the non-word "unregister" (crog@redhat.com)
- 1189880: Removed the non-word "unentitle" from error messages
  (crog@redhat.com)

* Tue Jun 02 2015 William Poteat <wpoteat@redhat.com> 1.14.9-1
- 1223038: Fix API used by openshift clients. (alikins@redhat.com)
- 1195824: Latest strings from zanata (alikins@redhat.com)

* Tue May 26 2015 William Poteat <wpoteat@redhat.com> 1.14.8-1
- 1223860: Revert to default value on remove command (wpoteat@redhat.com)
- translation sync from zanata (alikins@redhat.com)
- 1223852: fix 'Deletedfd' string in repo report (alikins@redhat.com)
- Remove gnome-python2-canvas,gnome-python2 deps (alikins@redhat.com)

* Tue May 19 2015 William Poteat <wpoteat@redhat.com> 1.14.7-1
- 1220287: Proxy Save accel fix with latest strings. (alikins@redhat.com)
- 1212515: Print error message for missing systemid file. (awood@redhat.com)
- Added missing option to the migration manual page (crog@redhat.com)
- Specified error codes on system_exit in rhn-migrate-classic-to-rhsm
  (crog@redhat.com)
- Updated the manual pages for the attach command (crog@redhat.com)
- Remove locale based DatePicker tests. (alikins@redhat.com)
- Make rhsm-debug test cases clean up better. (alikins@redhat.com)

* Fri May 01 2015 William Poteat <wpoteat@redhat.com> 1.14.6-1
- 1149095: Fix error when yum updates subman modules (alikins@redhat.com)
- 1159163: Fix prod id del because of --disablerepo (alikins@redhat.com)
- 1180273: Migrate from RHN Classic without credentials (awood@redhat.com)
- 1213418: Message agreement between GUI and CLI in disconnected system
  (wpoteat@redhat.com)
- 1199597: Fix UnicodeError from repolib's report (alikins@redhat.com)
- 1209519: Removed excerpt from man page listing --auto as a requirement
  (crog@redhat.com)

* Tue Apr 14 2015 William Poteat <wpoteat@redhat.com> 1.14.5-1
- 1211557: Fix crash when rsyslog not running. (dgoodwin@redhat.com)

* Tue Apr 14 2015 William Poteat <wpoteat@redhat.com> 1.14.4-1
- 1141257: Fix wrapping of subscription name in contract dialog
  (mstead@redhat.com)
- 1147404: Fixed firstboot title length issues (mstead@redhat.com)
- 1207306: Revert DBus compliance status code. (dgoodwin@redhat.com)
- 1195501: Properly refresh repo file on override deletion (mstead@redhat.com)
- Add Fedora 22 to Fedora releaser branches. (awood@redhat.com)

* Thu Apr 09 2015 Alex Wood <awood@redhat.com> 1.14.3-1
- 1170314: Clarify that manage_repos 0 will delete redhat.repo.
  (dgoodwin@redhat.com)
- 1207958: Fix traceback when contract # is None (alikins@redhat.com)
- 1117525,1189950,1188961 latest strings from zanata (alikins@redhat.com)
- 1200972: Fixed grammar issue with error message in the attach command
  (crog@redhat.com)
- Bumping required python-rhsm version (mstead@redhat.com)
- 1204012: Added missing documentation for the --release option
  (crog@redhat.com)
- 1209519: Removed erroneous information in help message for subman
  (crog@redhat.com)
- 1198369: refresh_compliance_status now has a default value for state
  (crog@redhat.com)
- 1180273: Allow migration without requiring RHN credentials (awood@redhat.com)
- 1201727: Handle reasons with expired ent id (alikins@redhat.com)

* Mon Mar 09 2015 Alex Wood <awood@redhat.com> 1.14.2-1
- Move to fileConfig based logging. (alikins@redhat.com)
- Ignore glib warnings about class properties. (alikins@redhat.com)
- log level updates, mostly info->debug. (alikins@redhat.com)
- Condense virt fact logging to one info level entry. (alikins@redhat.com)
- Log to info when we update facts. (alikins@redhat.com)
- Change branding 'nothing-happened' logs to debug. (alikins@redhat.com)
- Condense cert_sorter logged info. (alikins@redhat.com)
- Change most cache related log msgs to debug level. (alikins@redhat.com)
- Make D-Bus related log entries debug level. (alikins@redhat.com)
- Change heal logging to be more concise. (alikins@redhat.com)
- Add log friendy str version of Identity (alikins@redhat.com)
- 1133647: Fix messageWindow deprecation warning. (alikins@redhat.com)
- 1183382: Fix test case to work with dateutil 2. (alikins@redhat.com)
- Revert "Added check for /etc/oracle-release in hwprobe" (alikins@redhat.com)
- 1196416: Migration should not need credentials with activation keys
  (awood@redhat.com)
- 1196385: Add --activation-key option to migration man page.
  (awood@redhat.com)
- 1196418: Add bash completion for --activation-key in migration.
  (awood@redhat.com)
- Update spec to point to github / new project website. (dgoodwin@redhat.com)
- Quiet "Whoever translated calendar*" warnings. (alikins@redhat.com)
- Stop 'recently-used.xbel' warnings, disable mru (alikins@redhat.com)
- 1154375: Allow use of activation keys during migration. (awood@redhat.com)
- 1191237: Fix proxy "test connection" in firstboot. (alikins@redhat.com)
- 1191237: Make proxy config "save" work in firstboot. (alikins@redhat.com)
- 1191241: Handle network starting after subman does. (alikins@redhat.com)
- 1145077, disabled column wrapping during redirects (jmolet@redhat.com)
- Add syslog logging handler. (alikins@redhat.com)
- 1191237: Fix problems exitting firstboot on errors (alikins@redhat.com)
- 1163398, fixing rhsm-icon --help descriptions (jmolet@redhat.com)

* Fri Feb 06 2015 Devan Goodwin <dgoodwin@rm-rf.ca> 1.14.1-1
- 976855: populate a "version.py" at build time (alikins@redhat.com)
- Fixed typo in subscription-manager-gui (crog@redhat.com)
- 1186386: Provide one and only one Red Hat CA to Docker. (awood@redhat.com)
- 1114117: Stop collecting subs info by default. (alikins@redhat.com)
- 1184940: Update container plugin config. (dgoodwin@redhat.com)
- 1183122: Fix KeyErrors building dbus ent status (alikins@redhat.com)
- 884285: Needs to maintain loop for dbus calls (wpoteat@redhat.com)

* Wed Jan 14 2015 William Poteat <wpoteat@redhat.com> 1.13.13-1
- 1175284: Show warning for crossdev --noarchive (wpoteat@redhat.com)
- Add missing import of GMT() (alikins@redhat.com)
- 1180400: "Status Details" are now populated on CLI (crog@redhat.com)
- 1180395: Added "Provides Management" to subman list output (crog@redhat.com)
- Bumping required python-rhsm version (mstead@redhat.com)
- Don't fail when product cache has an old format. (awood@redhat.com)
- Use custom JSON encoding function to encode sets. (awood@redhat.com)
- Make 'attach' auto unless otherwise specified. (alikins@redhat.com)
- Add product tag reporting to client. (awood@redhat.com)
- 1175185: Removed extra slash from rhsm-debug output (crog@redhat.com)
- 1175291: Fixed a bug with attaching pools via empty file (crog@redhat.com)
- 1070585: Changed button label from "Ok" to "Save" (crog@redhat.com)
- 1122530: Updated man page examples (crog@redhat.com)
- 1132981: Reverted removal of warning message (crog@redhat.com)
- 1058231: Adjusted "last update" label positioning (crog@redhat.com)

* Thu Dec 11 2014 William Poteat <wpoteat@redhat.com> 1.13.12-1
- Latest strings from zanata. (alikins@redhat.com)
- 1122530: Removed/updated more obsoleted documentation, dates and versions
  (crog@redhat.com)
- 1159348: Improved list error output when using list criteria
  (crog@redhat.com)
- 1142918: Fixed proxy config button labels (crog@redhat.com)
- Move repolibs release fetch to the last minute. (alikins@redhat.com)

* Tue Dec 09 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.13.11-1
- 1132981: Fixed exit code when registering system with no products installed
  (crog@redhat.com)
- Add 'list --matches' example to man page. (alikins@redhat.com)
- 1149286: Removed obsolete CLI options from auto-completion (crog@redhat.com)
- 990183: Spelling errors in man pages (wpoteat@redhat.com)

* Wed Dec 03 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.13.10-1
- 1103824: Add a catchall excepthook for rhsmd (alikins@redhat.com)
- 1119688: Improved exit code usage (crog@redhat.com)

* Fri Nov 21 2014 William Poteat <wpoteat@redhat.com> 1.13.9-1
- Move ostree config to /etc/ostree/remotes.d/redhat.conf (alikins@redhat.com)
- 1147463: Log py.warnings to shutup gobject warning (alikins@redhat.com)
- 1159266: rhsm-icon -i fails with "TypeError: 'NoneType' object has no
  attribute '__getitem__'" (wpoteat@redhat.com)
- 1145833: Do not package sat5to6 with subscription-manager. (awood@redhat.com)
- 1156627: Fix list consumed matching no service level to "".
  (dgoodwin@redhat.com)
- 1162331: Changed how debug_commands.py prints errors. (crog@redhat.com)
- 1160150: Repos --list leads to deletion of certificates imported to a system
  (wpoteat@redhat.com)
- 1162170: Added error output when --pool-only is used with --installed.
  (crog@redhat.com)
- 990183: Fix typos in the new man page (bkearney@redhat.com)
- 1161694: Modify the --pool-id-only to be --pool-only in bash completion and
  man page (bkearney@redhat.com)
- Use .format strings for --ondate example message (alikins@redhat.com)
- 1113741: Fix rhsmd traceback on 502 errors. (alikins@redhat.com)
- 1157387: Fix incorrect no installed products detected status in GUI.
  (dgoodwin@redhat.com)

* Fri Nov 07 2014 Unknown name <wpoteat@redhat.com> 1.13.8-1
- Added support for attaching pools from a file/stdin. (crog@redhat.com)
- Revert "1046132: Makes rhsm-icon slightly less annoying."
  (dgoodwin@redhat.com)
- Further improved exit code standardization (crog@redhat.com)
- 1119688: Improved output of the status module (crog@redhat.com)
- Make repolib tag matching use model.find_content (alikins@redhat.com)
- Added the --pool-only option to subman's list command. (crog@redhat.com)
- 1157761: Fixed incorrect option usage in migration tool. (crog@redhat.com)
- 1157761: revert to "--servicelevel" (alikins@redhat.com)
- 1119688: Improved error code usage in subman. (crog@redhat.com)

* Mon Oct 27 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.13.7-1
- Add content/product tag matching for content plugins. (alikins@redhat.com)
- Remove ostree 'unconfigured' after configuring. (alikins@redhat.com)
- Symlink to redhat-uep.pem if we seem to be syncing a CDN hostname cert dir.
  (dgoodwin@redhat.com)
- Add a test for removing 'unconfigured-state' from origin (alikins@redhat.com)
- Case insensitive content type searching. (dgoodwin@redhat.com)
- Added container plugin for configuring Docker. (dgoodwin@redhat.com)

* Thu Oct 23 2014 Alex Wood <awood@redhat.com> 1.13.6-1
- 1093325: Prevent rhsm-debug from throwing tbs (alikins@redhat.com)
- Send list of compliance reasons on dbus (wpoteat@redhat.com)
- 1149286: Updated autocompletion for RHN migration script. (crog@redhat.com)
- Fix file name for rhsm.conf.5 in spec file (alikins@redhat.com)
- 1120772: Don't traceback on missing /ostree/repo (alikins@redhat.com)
- 1094747: add appdata metdata file (jesusr@redhat.com)
- 1122107: Clarify registration --consumerid option in manpage.
  (dgoodwin@redhat.com)
- 1149636: Specify OS_VERSION to make in spec file. (awood@redhat.com)
- Added client-side support for --matches on the list command.
  (crog@redhat.com)
- 1151925: Improved filtered listing output when results are empty.
  (crog@redhat.com)
- 990183: Add a manpage for rhsm.conf (bkearney@redhat.com)
- 1122530: Improved grammar and abbreviation usage. (crog@redhat.com)
- 1120576: Added additional testing of version parsing (crog@redhat.com)

* Fri Oct 03 2014 Alex Wood <awood@redhat.com> 1.13.5-1
- Use wildcards in the spec file. (awood@redhat.com)

* Thu Oct 02 2014 Alex Wood <awood@redhat.com> 1.13.4-1
- Latest strings from zanata. (alikins@redhat.com)
- 1122001: Reg with --consumerid no longer checks subs (crog@redhat.com)
- 1119648: Added additional functionality to repo listing. (crog@redhat.com)
- Move find content method off entitlement source. (dgoodwin@redhat.com)
- More generic search for content method on entitlment source.
  (dgoodwin@redhat.com)
- Refactor generic model into it's own namespace. (dgoodwin@redhat.com)
- Refactor EntCertEntitledContent. (dgoodwin@redhat.com)
- Add a 'install-pip-requirements' target (alikins@redhat.com)
- Drop models ContentSet and EntCertEntitledContentSet. (dgoodwin@redhat.com)

* Fri Sep 26 2014 Bryan Kearney <bkearney@redhat.com> 1.13.3-1
- Merge pull request #1023 from candlepin/alikins/ppc64le (wpoteat@redhat.com)
- Merge pull request #1026 from
  candlepin/csnyder/update_repo_dialog_config_msg_1139174 (wpoteat@redhat.com)
- Message needed a period (wpoteat@redhat.com)
- Fix certdirectory tests leaking temp directories. (dgoodwin@redhat.com)
- 1142436 - Final fix pre-QE (ggainey@redhat.com)
- Repo dialog displays appropriate message when repos are disabled by config.
  (root@csnyder.usersys.redhat.com)
- 1142436 - unentitle is default, update output, still DRAFT
  (ggainey@redhat.com)
- 1142436 - Give sat5to6 a man-page - DRAFT (ggainey@redhat.com)
- Include ppc64le in list of archs to skip dmi (alikins@redhat.com)
- 1134963: Fix 'release --list' on some systems. (alikins@redhat.com)
- Add Fedora 21 branch to releaser. (awood@redhat.com)

* Fri Sep 12 2014 Alex Wood <awood@redhat.com> 1.13.2-1
- Added non-overriding default prod dir tests (ckozak@redhat.com)
- 1135621: fix duplicate product ids from default dir (ckozak@redhat.com)
- Remove --force option for sat5to6. (awood@redhat.com)
- Disable RHN yum plugin for unentitled Satellite 5 systems. (awood@redhat.com)
- Don't ask for org and environment with consumerid. (awood@redhat.com)
- 1128061: Don't raise logged Disconnected on unreg (alikins@redhat.com)
- 1128658: do not contact RHN if unregistered (jesusr@redhat.com)
- 1132919: Repo dialog information is updated without the need for a gui
  restart. (csnyder@csnyder.usersys.redhat.com)

* Thu Sep 04 2014 Alex Wood <awood@redhat.com> 1.13.1-1
- Make 'gettext_lint' target grok _(u"foo") strings. (alikins@redhat.com)
- Add a sat5to6 migration script.
* Thu Aug 28 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.14-1
- 1132071: Update rhsm-debug to collect product-default directory (wpoteat@redhat.com)
- 1123029: Use default product certs if present. (alikins@redhat.com)
- Latest strings from zanata. (alikins@redhat.com)

* Wed Aug 20 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.13-1
- 1124685: Handle /status without rules-version (alikins@redhat.com)
- 1125132: Label does not change to Attaching on Fristboot progress bar (wpoteat@redhat.com)
- 1128061: Stop logging expected exceptions on unreg (alikins@redhat.com)
- 1129480: don't query envs when actkey is given (ckozak@redhat.com)
- 1130637: Correct call to os.path.isfile (awood@redhat.com)

* Wed Aug 13 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.12-1
- Extract the latest strings from the code (bkearney@redhat.com)
- 1126724: Use port instead of 443 for the url help text (bkearney@redhat.com)

* Wed Jul 30 2014 Alex Wood <awood@redhat.com> 1.12.11-1
- 1124726: Man page entry for '--no-subscriptions' option (wpoteat@redhat.com)
- 1122772: yum repolist now displays warning when appropriate.
  (csnyder@redhat.com)

* Fri Jul 25 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.10-1
- Revert "1114132: subman-gui and other tools are disabled in container mode." (jesusr@redhat.com)
- Revert "include dirent.h" (jesusr@redhat.com)

* Fri Jul 25 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.9-1
- include dirent.h (jesusr@redhat.com)

* Fri Jul 25 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.8-1
- 1039577: simplify reposgui gpgcheck control (ckozak@redhat.com)
- 1046132: Makes rhsm-icon slightly less annoying. (csnyder@redhat.com)
- 1054632: Adds '7.x' to how to launch section of manual. (csnyder@redhat.com)
- 1065158: Prompt for environment on registration when necessary (ckozak@redhat.com)
- 1114126: Container mode message is written to stderr (csnyder@redhat.com)
- 1114132: subman-gui and other tools are disabled in container mode.  (csnyder@redhat.com)
- 1115499: Allow enable/disable repos in same command. (dgoodwin@redhat.com)
- 1118012: Fixes several typos in man page. (csnyder@redhat.com)
- 1121251: rhsm-debug system does not bash-complete for "--no-subscriptions" (wpoteat@redhat.com)
- 1121272: fix typo that blocked enabling repos via CLI (ckozak@redhat.com)
- cleanup and fix gui pool reselection on refresh (ckozak@redhat.com)
- Force subscription-manager yum plugin to respect the managed root (rholy@redhat.com)
- Force product-id yum plugin to respect the managed root (rholy@redhat.com)
- Display other overrides in the gui (ckozak@redhat.com)

* Thu Jul 03 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.7-1
- 1114117: Allow subscriptions to be excluded from rhsm-debug data collection (wpoteat@redhat.com)
- Remove debugging print line from managerlib (ckozak@redhat.com)

* Mon Jun 30 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.6-1
- 1022622: Modifies --no-overlap to show pools which provide products not already covered. (csnyder@redhat.com)
- Reload ostree_config after updating remotes. (alikins@redhat.com)
- Fix iniparse tidy import. (alikins@redhat.com)
- Remove noise debug logging. (alikins@redhat.com)
- Include 'tls-ca-path' for ostree remote configs. (alikins@redhat.com)
- Use iniparse.util.tidy if installed. (alikins@redhat.com)
- Fix odd ostree repo config whitespace issues. (alikins@redhat.com)
- Always update ostree refspec when adding remotes. (alikins@redhat.com)

* Thu Jun 26 2014 Adrian Likins <alikins@redhat.com> 1.12.5-1
- Merge pull request #978 from candlepin/alikins/ostree_gpg_http
  (alikins@redhat.com)
- Merge pull request #979 from candlepin/csnyder/help_message_identity_force
  (jmrodri@nc.rr.com)
- Use rhsm.baseurl for ostree urls as well. (alikins@redhat.com)
- Handle Content.gpg="http://" as gpg-verify=false (alikins@redhat.com)
- 1107810: Updates help message for identity --force. (csnyder@redhat.com)
- Merge pull request #977 from candlepin/alikins/handle_no_origin (dgoodwin@rm-
  rf.ca)
- Merge pull request #974 from cgwalters/doc-typos (jmrodri@nc.rr.com)
- Merge pull request #973 from candlepin/alikins/1112282_cond_ostree_rpm
  (jmrodri@nc.rr.com)
- make has_ostree use macro value NOT hardcoded value. (jesusr@redhat.com)
- Handle missing or empty ostree origin file. (alikins@redhat.com)
- Fix saving ostree remote configs with gpg set. (alikins@redhat.com)
- plugin/ostree: Fix doc typos (walters@verbum.org)
- Merge pull request #972 from candlepin/ckozak/fix_custom_fact_log
  (jmrodri@nc.rr.com)
- Merge pull request #968 from candlepin/alikins/setup_py (jmrodri@nc.rr.com)
- 1112282: Dont build ostree plugin subpackage < 7 (alikins@redhat.com)
- Merge pull request #966 from
  candlepin/alikins/1108257_rhel_5_workstation_special (c4kofony@gmail.com)
- Add required bz flags to tito releaser definition. (dgoodwin@redhat.com)
- 1112326: remove extra '/' from custom fact loading error logging
  (ckozak@redhat.com)
- Allow tests to run in any TZ (mstead@redhat.com)
-  Temp ignore use of subprocess.check_output (alikins@redhat.com)
- Add test cases for 'rhel-5-workstation' tags. (alikins@redhat.com)
- 1108257: special case prod tag rhel-5-workstation (alikins@redhat.com)
- Add a simple setup.py. (alikins@redhat.com)
- Merge pull request #965 from candlepin/alikins/good_enthusiasm_pep8 (dgoodwin
  @rm-rf.ca)
- Turn off verbose mode of pyqver. (alikins@redhat.com)
- make stylish cleanups for new pep8 (alikins@redhat.com)
- Add tox.ini with ignores for pep8 indention (alikins@redhat.com)

* Thu Jun 19 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.12.4-1
- Fix broken logging statement in container mode. (dgoodwin@redhat.com)
- 1067035: Move Subscription Manager version for better layout
  (wpoteat@redhat.com)

* Mon Jun 16 2014 Alex Wood <awood@redhat.com> 1.12.3-1
- Bumping required python-rhsm version (mstead@redhat.com)
- Fixing checkstyle. (mstead@redhat.com)
- TODO/FIXME cleanup. (alikins@redhat.com)
- Cleanup BaseOstreeKeyFileTest.cfgfile_data (alikins@redhat.com)
- Remove unused model.OstreeRepo (alikins@redhat.com)
- Use python-rhsm's new EntCert.key_path() (alikins@redhat.com)
- Add specific exception for refspec parse error (alikins@redhat.com)
- stylish cleanups (alikins@redhat.com)
- Add test cases for OstreeContents (alikins@redhat.com)
- Remove fixed FIXME. (alikins@redhat.com)
- Add section name to exception reading remote name. (alikins@redhat.com)
- Remove unused origin/refspec from report. (alikins@redhat.com)
- repr and report format cleanups. (alikins@redhat.com)
- Save needed ostree remote info to config file. (alikins@redhat.com)
- Mock an ent cert associated with a content. (alikins@redhat.com)
- Start passing along ent cert ssl info to ostree (alikins@redhat.com)
- Fix mismerge for OstreeContents usage (alikins@redhat.com)
- call get_path() to get path string on deploy (alikins@redhat.com)
- Remove done TODO (map gpgkey->gpg-verify) (alikins@redhat.com)
- _get_deployed_origin returns None if not a ostree install
  (alikins@redhat.com)
- Fix missed return in gi_wrapper. (dgoodwin@redhat.com)
- Rename poor choice of gi.py script. (dgoodwin@redhat.com)
- Only replace origin remote if it matches first portion of ref.
  (dgoodwin@redhat.com)
- Test subprocess error calling pygobject3 script, log output.
  (dgoodwin@redhat.com)
- Start making OstreeContent resp for finding contents. (alikins@redhat.com)
- Add models.py to spec (alikins@redhat.com)
- Make models internal data attrs '_' (alikins@redhat.com)
- Add a static map_gpg to OstreeRemote (alikins@redhat.com)
- stylish cleanups (alikins@redhat.com)
- Remove 'api' module. (alikins@redhat.com)
- Add models module, for objects we pass to plugins (alikins@redhat.com)
- OSTree package depends on pygobject3-base. (dgoodwin@redhat.com)
- Move gi introspection code to separate script. (dgoodwin@redhat.com)
- Add some missing copyright notices. (dgoodwin@redhat.com)
- Remove inj from 'api' module. (alikins@redhat.com)
- Add more tests. (alikins@redhat.com)
- Remove per class repo_file_store_class (alikins@redhat.com)
- Package ostree plugin as a sub-package. (dgoodwin@redhat.com)
- Test cases for OstreeConfig and ..RepoFileWriter (alikins@redhat.com)
- When persisting a OstreeCore copy all items. (alikins@redhat.com)
- Default empty OstreeRemotes or OstreeCore (alikins@redhat.com)
- Fix test cases to look for ostree.config (alikins@redhat.com)
- Make OstreeConfig use OstreeConfigFileStore (alikins@redhat.com)
- Remove OstreeConfigUpdater (alikins@redhat.com)
- Complete happy path test for origin remote updating. (dgoodwin@redhat.com)
- Attempt to disambiguate use of repo_config_file variables.
  (dgoodwin@redhat.com)
- Beginning tests for ostree origin updating, refactor tempfiles in tests.
  (dgoodwin@redhat.com)
- Name changes (alikins@redhat.com)
- Add method to replace ostree remote in a refspec. (dgoodwin@redhat.com)
- Get some better reporting, albeit klugey. (alikins@redhat.com)
- Add some temp kluge, OstreeRemote's not immutable (alikins@redhat.com)
- Make OstreeRemote a dict (alikins@redhat.com)
- Simplify the config model a little. (alikins@redhat.com)
- s/PluginManagerRunner/PluginHookRunner (alikins@redhat.com)
- Stylish cleanups. (alikins@redhat.com)
- Add a runiter to the fixtures mock PluginManager (alikins@redhat.com)
- We still need the entdir refresh for 'attach'. (alikins@redhat.com)
- Use PluginManager.runiter for content actions. (alikins@redhat.com)
- Add a PluginManager.runiter() method. (alikins@redhat.com)
- Update plugin docs. (alikins@redhat.com)
- Add notes, comments, docstrings. (alikins@redhat.com)
- Get ostree repo config saving working-ish (alikins@redhat.com)
- Update some missed tests. (dgoodwin@redhat.com)
- Refactor to an update content plugin. (dgoodwin@redhat.com)
- Update makefile and spec for ostree plugin. (dgoodwin@redhat.com)
- Move ostree plugin support code to subscription-manager namespace.
  (dgoodwin@redhat.com)
- Add ostree/model.py for ostree related models. (alikins@redhat.com)
- More tests for ostree/repo_file (alikins@redhat.com)
- Add src/content_plugins to coverage (alikins@redhat.com)
- Use RhsmConfigParser to read repo config (alikins@redhat.com)
- More ostree impl tests. (alikins@redhat.com)
- Use the 'api' module when importing from plugins. (alikins@redhat.com)
- Start of test for 'api' module. (alikins@redhat.com)
- Add an api module with our "exported" symbols (alikins@redhat.com)
- Use regular config parser instead of pyxdg (alikins@redhat.com)
- Add start of tests for ostree repo action (alikins@redhat.com)
- Start ostree repo action class stubs (alikins@redhat.com)
- Start ostree implementation tests (alikins@redhat.com)
- Start adding ostree implementation (alikins@redhat.com)
- Add TODO about content_plugin installs (alikins@redhat.com)
- Move OstreeContentActionInvoker to it's own module (alikins@redhat.com)
- Remove unneeded #!/usr/bin/python (alikins@redhat.com)
- Make ostree content action loaded from plugins. (alikins@redhat.com)
- Log exceptions from trying to load plugins. (alikins@redhat.com)
- Add ostree_content plugin entry point (alikins@redhat.com)
- HACK: install ostree content plugin in site-packages (alikins@redhat.com)
- Add content_plugins dir,and ostree content plugins (alikins@redhat.com)
- Remove sample yum_content plugin (alikins@redhat.com)
- Hit ContentActionClient for some test coverage. (alikins@redhat.com)
- Add test for ContentActionPluginConduit (alikins@redhat.com)
- entcertlib.repo_hook can be content type agnostic (alikins@redhat.com)
- Replace odd usage of 'repolib' name. (alikins@redhat.com)
- Load content actions from plugin class search (alikins@redhat.com)
- Add a dummy yum_content plugin for testing (alikins@redhat.com)
- Add ContentActionPluginConduit plugin. (alikins@redhat.com)
- Add ostree_action_invoker (ostree repo action) (alikins@redhat.com)
- Add ContentActionClient (alikins@redhat.com)
- 1104158: Version command needs better explanation for content
  (wpoteat@redhat.com)

* Mon Jun 16 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.12.2-1
- 1070585: GUI no longer locks on connection test. Adds cancel button.
  (csnyder@redhat.com)
- Disable CLI if we are running inside a container. (dgoodwin@redhat.com)
- Don't encourage registration in yum plugin if we have ents but no identity.
  (dgoodwin@redhat.com)
- Allow yum plugin to generate redhat.repo when unregistered.
  (dgoodwin@redhat.com)
- Rev zanata branch to 1.12.X (alikins@redhat.com)
- 1030638: Changes default resolution values in mainwindow.glade to 800x600.
  (csnyder@redhat.com)
- 1086377: Next system check-in not displaying in RHEL 5.11
  (wpoteat@redhat.com)
- Fix plugin config so conduit conf methods work. (alikins@redhat.com)
- 1058380: Subscripton Manager plugin reporting Subscription Management when
  RHN is in use (wpoteat@redhat.com)
- Add support for sphinx doc generation. (alikins@redhat.com)

* Thu Jun 05 2014 jesus m. rodriguez <jesusr@redhat.com> 1.12.1-1
- bump version to 1.12 (jesusr@redhat.com)
- Support getting release versions via API call (mstead@redhat.com)
- 855050: set default fallback window icon (ckozak@redhat.com)
- refresh ent_dir after adding/deleting certs (ckozak@redhat.com)
- 1035440: Don't rewrite redhat.repo unless it has changed (ckozak@redhat.com)
- 1097536: match-installed filter was incorrectly removed. (wpoteat@redhat.com)
- 1092754: 1094879: Remove install-num-migrate-to-rhsm tool (ckozak@redhat.com)

* Mon May 26 2014 Devan Goodwin <dgoodwin@rm-rf.ca> 1.11.7-1
- update existing repos with non-default overrides (ckozak@redhat.com)
- correct repos --list behavior (ckozak@redhat.com)
- Cache overrides when RepoFile is written (ckozak@redhat.com)
- 1098891: Apply overrides to mutable properties (ckozak@redhat.com)
- 1076359; Removes the extra l from --remove all (csnyder@redhat.com)
- 1098891: Update repos, persisting local settings when possible
  (ckozak@redhat.com)
- 1094617: Status line reporting for installed products uses incorrect date
  (wpoteat@redhat.com)
- 1097208: 1097703: Fix rhsmcertd-worker daemon (ckozak@redhat.com)
- 1086301: Fix product id product version compare (alikins@redhat.com)
- 1096777: Bad URI for remove by serial (wpoteat@redhat.com)
- 1095938: re-add at-spi locator in repos window (ckozak@redhat.com)
- 1094492: Consumer name length issues in certificate (wpoteat@redhat.com)
- Fix yum subman plugin RepoActionInvoker error. (alikins@redhat.com)
- Overrides had no "cp", the connection was named uep (ckozak@redhat.com)

* Thu May 01 2014 Alex Wood <awood@redhat.com> 1.11.6-1
- s/certmgr/action_client in spec (alikins@redhat.com)

* Thu May 01 2014 Alex Wood <awood@redhat.com> 1.11.5-1
- Removing CVS properties since CVS is dead. (awood@redhat.com)
- CertSorter syncs installed prods before super init. (alikins@redhat.com)
- Add more entcertlib class and method docs. (alikins@redhat.com)
- Reorder methods in roughly exec order (alikins@redhat.com)
- entcertlib docstring cleanup (alikins@redhat.com)
- TestDataLib -> TestBaseActionInvoker (alikins@redhat.com)
- repolib.RepoUpdateAction ->RepoUpdateActionCommand (alikins@redhat.com)
- repolib.RepoLib -> RepoActionInvoker (alikins@redhat.com)
- InstalledProductsLib -> InstalledProductsActionInvoker (alikins@redhat.com)
- IdentityCertLib -> IdentityCertActionInvoker (alikins@redhat.com)
- healiblib.HealingLib -> HealingActionInvoker (alikins@redhat.com)
- FactAction -> FactsActionCommand (alikins@redhat.com)
- FactActionReport -> FactsActionReport (alikins@redhat.com)
- FactLib -> FactsActionInvoker (alikins@redhat.com)
- entcertlib.EntCertLib -> EntCertActionInvoker (alikins@redhat.com)
- certlib.DataLib -> certlib.BaseActionInvoker (alikins@redhat.com)
- rename certmgr.py to action_client (alikins@redhat.com)
- Rename CertManager to ActionClient (alikins@redhat.com)
- Rename CertManager to CertActionClient (alikins@redhat.com)
- Update docstrings. (alikins@redhat.com)
- Remove no longer used old_install. (alikins@redhat.com)
- Add entcertlib docs (alikins@redhat.com)
- update copyright info (alikins@redhat.com)
- s/entdir/ent_dir since we use that slightly more (alikins@redhat.com)
- factsgui identity now injected at the last minute (alikins@redhat.com)
- SubManFixture's mock identity now NonCallable (alikins@redhat.com)
- test_async does not need to mock Facts (alikins@redhat.com)
- Store default inject stub Facts on SubManFixture (alikins@redhat.com)
- Remove unneeded Facts() init. (alikins@redhat.com)
- Replace Facts() with injected facts in managercli (alikins@redhat.com)
- Start replacing use of Facts() with inj'ed facts (alikins@redhat.com)
- Stop passing facts to ReleaseBackend. (alikins@redhat.com)
- Make repolib use inject ent_dir/prod_dir (alikins@redhat.com)
- Make cp_provider manage ContentConnection (alikins@redhat.com)
- Make ReleaseBackend use inj'ed ent/prod dirs (alikins@redhat.com)
- split migrates basic/consumer connection methods (alikins@redhat.com)
- migrate.py now uses inj'ed CP_PROVIDER (alikins@redhat.com)
- ReleaseBackend doesn't need a uep, remove it. (alikins@redhat.com)
- Stop passing a uep into CertManager and friends. (alikins@redhat.com)
- Don't pass cp to RepoLib from cli, use inj (alikins@redhat.com)
- update Overrides to use inject uep (alikins@redhat.com)
- Split IdentityCertLib into Lib+Action (alikins@redhat.com)
- Use the mock cp_provider inject with the fixture (alikins@redhat.com)
- certlib.DataLib doesn't need a uep now (alikins@redhat.com)
- Fix testcase to use injected uep (alikins@redhat.com)
- Use inj'ed UEP in healinglib (alikins@redhat.com)
- Use inj'ed UEP in repolib (alikins@redhat.com)
- Use inj'ed UEP in packageprofilelib (alikins@redhat.com)
- Use inject uep in installedproductslib (alikins@redhat.com)
- Remove unneeded mock Facts in test_certmgr (alikins@redhat.com)
- Make certmgr let FactLib use inj uep (alikins@redhat.com)
- Make FactActionReport use inj'ed UEP (alikins@redhat.com)
- Start letting EntCertLib use injected UEP (alikins@redhat.com)
- Move entcertlib to use inj'ed cp_proivder (alikins@redhat.com)
- Remove now wrong comment (alikins@redhat.com)
- Remove late import of repolib (alikins@redhat.com)
- Remove incorrect docstrings (alikins@redhat.com)
- Remove initial entcertlib invocation (alikins@redhat.com)
- Don't pass in a facts object, inject it (alikins@redhat.com)
- We don't use the passed in entdir, don't pass it (alikins@redhat.com)
- Handle ActionReport lists having None (alikins@redhat.com)
- Remove commented out code (alikins@redhat.com)
- Fix up for now, but need to remove these tests (alikins@redhat.com)
- certdata merge cleanups (alikins@redhat.com)
- merge cleanups (alikins@redhat.com)
- Add new files to spec (alikins@redhat.com)
- stylish cleanups (alikins@redhat.com)
- Use injected identity instead of consumer object (alikins@redhat.com)
- Update to use Caputure() instead of MockStdout (alikins@redhat.com)
- Fix v1 cert exp cert output for catcert tests (alikins@redhat.com)
- self.installed is a property now, fix references (alikins@redhat.com)
- merge cleanups (alikins@redhat.com)
- make stylish cleanups (alikins@redhat.com)
- Update repolib tests for certlib refactor (alikins@redhat.com)
- Repo/override cli tests use injected identity (alikins@redhat.com)
- Update Repos and overrides for injected identity (alikins@redhat.com)
- Update RepoLib to use new DataLib init (alikins@redhat.com)
- Fix mismerge and merge cleanups (alikins@redhat.com)
- Stylish cleanups, mostly no longer used imports (alikins@redhat.com)
- Remove unused ProductCertRepo bits (alikins@redhat.com)
- Keep certmgr update_reports as a instance variable (alikins@redhat.com)
- Remove certlib.ConsumerIdentity. (alikins@redhat.com)
- Move firstboot to use injected identity. (alikins@redhat.com)
- Move 'subscription-manager' yum plugin to inj (alikins@redhat.com)
- Remove unused ConsumerIdentity from test_unreg (alikins@redhat.com)
- Using injection in migration for prod_dir/identity (alikins@redhat.com)
- Remove _get_consumer_id from EntUpdateAction (alikins@redhat.com)
- Move old test_certlib to test_entcertlib (alikins@redhat.com)
- Fix fetch_certificates for entcert Report (alikins@redhat.com)
- Add some comments about id error logging (alikins@redhat.com)
- Add a certmgr.UnregisterCertMgr class (alikins@redhat.com)
- Add a RepoActionReport formatter (alikins@redhat.com)
- Add a RepoActionReport (alikins@redhat.com)
- More injected id, clean check_registration use (alikins@redhat.com)
- Test fixes and merge/rebase cleanup (alikins@redhat.com)
- Make string equals show expected/actual (alikins@redhat.com)
- identitycertlib now uses injected identity (alikins@redhat.com)
- certmgr tests were hitting real rpmdb (alikins@redhat.com)
- PackageProfileManager/InstalledProductsManager inj (alikins@redhat.com)
- Move PackageProfileLib and InstalledProductsLib (alikins@redhat.com)
- Make rhsm_d use injection consumer identity (alikins@redhat.com)
- Convert test_async to use SubManFixture (alikins@redhat.com)
- test_certmgr calls uep.getRelease, so mock it (alikins@redhat.com)
- Use injected consumer identity in firstboot (alikins@redhat.com)
- Use injected consume identity in factlib (alikins@redhat.com)
- Use ConsumerIdentity from identity not certlib (alikins@redhat.com)
- Fix self.exceptions reference (alikins@redhat.com)
- _valid_consumer to _inject_mock_valid_consumer (alikins@redhat.com)
- Move _[in]valid_consumer to test/fixture.py (alikins@redhat.com)
- Use injected Identity in repolib (alikins@redhat.com)
- Remove  certlib.ConsumerIdentity from managerlib (alikins@redhat.com)
- Inject identity in utils for version check (alikins@redhat.com)
- Give a name to Mock()s created in test/fixture (alikins@redhat.com)
- Re add the new slimmer fitter certlib.py (alikins@redhat.com)
- Make entcertlib uses injected identity (alikins@redhat.com)
- Split certlib into entcertlib and certlib (alikins@redhat.com)
- Make IdentityCertLib use inj IDENTITY (alikins@redhat.com)
- Move IdentityCertLib to identitycertlib.py (alikins@redhat.com)
- Split Healing* into healinglib.py (alikins@redhat.com)
- repolib.UpdateAction is now RepoUpdateAction (alikins@redhat.com)
- Checkout idcertlib._status from it's report (alikins@redhat.com)
- Inject an ActionLock, and a Facts class. (alikins@redhat.com)
- Add ActionReports, certlib cleanup, lock cleanup (alikins@redhat.com)
- The Action subclass is unneeded now. (alikins@redhat.com)
- CertManager split CertManager/HealingCertManager (alikins@redhat.com)
- HealingAction just uses an EntCertUpdateReport atm (alikins@redhat.com)
- reAction()'ify repolib, add RepoReport (alikins@redhat.com)
- reAction()'ify Factlib, add FactUpdateReport (alikins@redhat.com)
- certmgr expects a ActionReport from Action.perform (alikins@redhat.com)
- Rename CertLib->EntCertLib (alikins@redhat.com)
- Split UpdateReport into base class and sub classes (alikins@redhat.com)
- Create UpdateReport in Certlib.CertLib and pass it (alikins@redhat.com)
- Start refactoring certlib (alikins@redhat.com)
- Add product certs with os_name in certdata (alikins@redhat.com)
- Add ProductIdRepoMap as core of ProductDatabase (alikins@redhat.com)
- Add a DefaultDict (defaultdict with pretty print) (alikins@redhat.com)

* Mon Apr 28 2014 ckozak <ckozak@redhat.com> 1.11.4-1
- Move atspi locator to correct element (ckozak@redhat.com)
- 1090560: readd locator to the all subs view (ckozak@redhat.com)
- test_cert_sorter could fail based on test order (alikins@redhat.com)
- 1058383: widgets are added and removed dynamically (ckozak@redhat.com)

* Thu Apr 10 2014 Alex Wood <awood@redhat.com> 1.11.3-1
- Cleanup entbranding tests names. (alikins@redhat.com)
- Test cases for empty,none,not set brand type/name (alikins@redhat.com)
- Use a real certificate2.Product in tests cases. (alikins@redhat.com)
- Latest strings from zanata (alikins@redhat.com)

* Thu Mar 20 2014 Alex Wood <awood@redhat.com> 1.11.2-1
- Use the new Product.brand_name for brand_name (alikins@redhat.com)
- 865702: Dont render exc messages with bogus markup (alikins@redhat.com)
- 1070908: Don't count cpus without topo for lpar (alikins@redhat.com)
- 1075167: Avoid using injected values in migrate-classic-to-rhsm
  (ckozak@redhat.com)
- 1074568: Use our translations in optparser (ckozak@redhat.com)
- Man page spelling corrections (wpoteat@redhat.com)
- 1070737: correct config section for ca_cert_dir (ckozak@redhat.com)

* Thu Feb 27 2014 Alex Wood <awood@redhat.com> 1.11.1-1
- 1021069: Add reference to network usage info. (alikins@redhat.com)
- latest strings from zanata 1.11.X branch (alikins@redhat.com)
- 1061923: Remove trailing period from privacy URL (wpoteat@redhat.com)
- 1039913: rhsm-debug updates and fixes (alikins@redhat.com)
- 1061407: don't allow some translations (ckozak@redhat.com)
- 1055664: rhsm-debug now follows more config paths (alikins@redhat.com)
- 1038242: add anaconda.pid check before chroot (alikins@redhat.com)
- 1035115: Update product id certs (alikins@redhat.com)
- 864195: New output line for subscribe --auto if it can't cover all products
  (wpoteat@redhat.com)
- 1060727: Changes to rhsm-debug for sos report (wpoteat@redhat.com)
- 1044596: Don't match beta product tags for release (alikins@redhat.com)
- 851325: Tweak activation key checkbox to left (alikins@redhat.com)
- Use systemd RPM macros to make life easier. (awood@redhat.com)
- 958016: use rpm %%{optflags} and _hardended_build (alikins@redhat.com)

* Tue Feb 11 2014 ckozak <ckozak@redhat.com> 1.10.14-1
- Use glob for finding entitlement certs to remove. (dgoodwin@redhat.com)
- Make sure entitlement cert directory exists before we clean it out.
  (dgoodwin@redhat.com)
- safer default args in AsyncWidgetUpdater (ckozak@redhat.com)
- use enumerate instead of confusing myself (ckozak@redhat.com)
- Pull in latest strings from zanata (bkearney@redhat.com)
- make sure entitlement has a pool before reading it (ckozak@redhat.com)
- quickly load preferences (ckozak@redhat.com)
- 1061937: preference changes occur in the background (ckozak@redhat.com)
- use existing signals (ckozak@redhat.com)
- simplify preferences window (ckozak@redhat.com)
- Fix test failure if run on system that is registered. (dgoodwin@redhat.com)
- 1061393: Don't allow subscription-manager string to be translated
  (ckozak@redhat.com)
- 1016427: On string was missed from the extraction (bkearney@redhat.com)
- 1058495: productid yum errors on yum remove (alikins@redhat.com)
- 1026501: Preserve PKI directories and have rpm own them.
  (dgoodwin@redhat.com)
- 1058374: Fix crash on exception in managergui._show_buttons
  (ckozak@redhat.com)

* Mon Feb 03 2014 ckozak <ckozak@redhat.com> 1.10.13-1
- 1060917: catch exception thrown in firstboot (ckozak@redhat.com)
- Extract the latest strings (bkearney@redhat.com)
- 995121: require gnome-icon-theme for calendar icon (alikins@redhat.com)

* Mon Feb 03 2014 ckozak <ckozak@redhat.com> 1.10.12-1
- added testing for the pooltype cache (ckozak@redhat.com)
- 961003: Stricter matches for rhel product tags (alikins@redhat.com)
- 1059809: Cache pool types to avoid unnecessary api calls (ckozak@redhat.com)
- 1059809 Improve attach and remove performance add progress bar
  (ckozak@redhat.com)
- 908869: Fix the mis-transated options in pt-BR (bkearney@redhat.com)
- 1044596: handle http,socket,ssl fetching release (alikins@redhat.com)
- dont always print exception message (ckozak@redhat.com)
- 1044596: Make release listing handle empty data (alikins@redhat.com)
- 1020423: update help messages (jesusr@redhat.com)
- Fix incorrect patching. (awood@redhat.com)
- Mock ProductDatabase so tests can run without a productid.js file
  (awood@redhat.com)
- 825388: Properly wrap text when reaching dialog limit (mstead@redhat.com)
- 1021443: display Consumer deleted message (jesusr@redhat.com)
- Altering titles per mreid conversation. (wpoteat@redhat.com)
- 1039736: Fix missed reference to CloudForms in tooltip. (dgoodwin@redhat.com)
- Fix ta_IN translation problem. (dgoodwin@redhat.com)
- Lock timezone to EST5EDT in timezone tests. (awood@redhat.com)
- 1005329: add at-spi locator to the SLA selection table (ckozak@redhat.com)
- 1039914: Update the rhsm-debug man page (bkearney@redhat.com)
- 874169: Fix label alignment in progress UI (mstead@redhat.com)
- 1020361: Replace the use of the term Valid with Current in the status command
  (bkearney@redhat.com)
- 1028596: Add the repo-override command to the subscription-manager man page
  (bkearney@redhat.com)
- 1020522: Update the man page for subscription-manager with new list options
  (bkearney@redhat.com)
- Pull in the latest strings from zanata. (bkearney@redhat.com)
- 1057719: adding a small section on deprecated commands (dlackey@redhat.com)
- 1017354: remove msg printed to stderr via yum (alikins@redhat.com)
- 857147: Auto-subscribe window has a confusing name (wpoteat@redhat.com)
- Use dateutil.tz instead of pytz. (awood@redhat.com)
- 883486: The local time's start/end dates rendered in the list
  --available/--consumed incorrect (wpoteat@redhat.com)
- 1049037: Add conditional requires on migration data package.
  (awood@redhat.com)
- 973938: correctly handle SIGPIPE in rct (ckozak@redhat.com)
- 878089: Add line wrapping when listing subscription-manager modules
  (ckozak@redhat.com)
- 1017354: Ensure all message go to stdout, not stderr (bkearney@redhat.com)
- 851325: Anchor choose server "default" button beside the text box.
  (dgoodwin@redhat.com)
- 1039739: Add 96x96 and 256x256 icons (bkearney@redhat.com)
- 873967: Move choose server tooltips closer to the elements they assist with.
  (dgoodwin@redhat.com)
- 1044686: Make serverurl parse error detailed again (alikins@redhat.com)

* Wed Jan 22 2014 ckozak <ckozak@redhat.com> 1.10.11-1
- 1018807: Ensure virt facts are a single line (bkearney@redhat.com)
- 1007580: Print blank spaces if there is no contract number on the list
  command (bkearney@redhat.com)
- Fedora 18 is at end of life. (awood@redhat.com)
- Updated translations. (dgoodwin@redhat.com)
- 104338: add default dest dir to rhsm-debug help (alikins@redhat.com)
- 1042897: add proxy info to rhsm-debug completion (alikins@redhat.com)
- 914833: rct cat-cert output reports an Order: Subscription: field.
  (wpoteat@redhat.com)
- 1052297: delay import of site module (ckozak@redhat.com)
- set default encoding to utf-8 in rhsm-debug and migrate scripts
  (ckozak@redhat.com)
- 1048325: Set default encoding to utf-8 when running the rct script
  (ckozak@redhat.com)
- 1050850: re-evaluate system facts when checking for updates
  (ckozak@redhat.com)
- Some refactoring of rhsm-debug (alikins@redhat.com)
- Additional improvements to rhsm-debug (wpoteat@redhat.com)

* Mon Jan 06 2014 ckozak <ckozak@redhat.com> 1.10.10-1
- 1039736: Modify the remote server string to reference Satellite instead of
  CloudForms (bkearney@redhat.com)
- 916666: Change method of service detection (wpoteat@redhat.com)
- Correct at-spi name for subscription type text (ckozak@redhat.com)

* Tue Dec 17 2013 ckozak <ckozak@redhat.com> 1.10.9-1
- Check for RHSM_DISPLAY before loading any modules. (alikins@redhat.com)
- 1034429: Fix stacktrace in logs on unregister. (dgoodwin@redhat.com)
- add ServerUrlParseException strings to mapper (jesusr@redhat.com)
- 1040167: Update installed products properly (ckozak@redhat.com)
- Added atspi locator for overall status (ckozak@redhat.com)
- ExceptionMapper will now traverse object graph looking for message
  (mstead@redhat.com)
- Convert tests on stderr to use Capture context manager. (awood@redhat.com)
- Have Capture grab both stdout and stderr. (awood@redhat.com)
- Updated for readability (ckozak@redhat.com)
- replace file monitors with a single monitor (ckozak@redhat.com)
- Rename capture context manager and use new-style classes. (awood@redhat.com)
- Correct Makefile for RHEL 5. (awood@redhat.com)
- 1030604: print to stdout instead of stderr for consistency
  (mstead@redhat.com)
- display pool type in cli and gui (ckozak@redhat.com)
- 1031008: Properly handle exceptions when checking compliance
  (mstead@redhat.com)
- Change the capture() context manager to tee output. (awood@redhat.com)
- Remove mock stdout. Nosetest captures stdout by default. (awood@redhat.com)
- respect http(s)_proxy env variable for proxy information (jesusr@redhat.com)
- Created ExceptionMapper to allow sharing exception messages
  (mstead@redhat.com)

* Fri Dec 06 2013 ckozak <ckozak@redhat.com> 1.10.8-1
- 1030604: Handle 400 code for add override (mstead@redhat.com)
- Use backed to ensure a refreshed Overrides object (mstead@redhat.com)
- 1034574: Alternate message based on why no repos exist in GUI
  (mstead@redhat.com)
- 1034396: No longer require entitlements to run repo-override command
  (mstead@redhat.com)
- 1033741: Refresh Overrides CP connection when dialog is shown
  (mstead@redhat.com)
- 1033690: Updated repo-overrides not supported message (mstead@redhat.com)
- 1034649: Only allow repolib to update override cache if supported by the
  server (mstead@redhat.com)
- 1032673: Warn on add override if repo doesn't exist (mstead@redhat.com)
- 1030996: Fixed usage text for repo-override add/remove options
  (mstead@redhat.com)
- 1032243: Updated the redhat.repo warning (mstead@redhat.com)
- Use local ent certs to list attached pools (ckozak@redhat.com)
- 1021013: Change wording on firstboot address screen (alikins@redhat.com)
- 1020539: Show proxy info if no RHN in firstboot (alikins@redhat.com)
- Make zip file of consumer information for debugging (wpoteat@redhat.com)

* Thu Nov 14 2013 ckozak <ckozak@redhat.com> 1.10.7-1
- 998033: Handle Unauthorized/Forbidden exceptions in CLI/GUI
  (mstead@redhat.com)
- Remove unnecessary network calls after clean command (ckozak@redhat.com)
- Bumping the python-rhsm required version (mstead@redhat.com)
- Latest translations. (awood@redhat.com)
- Introduced an Override model object to OverrideLib (mstead@redhat.com)
- Use injected Identity instead of ConsumerIdentity in repolib
  (mstead@redhat.com)
- Catch ValueError when determining boolean value (mstead@redhat.com)
- Use a simplier method to compare two lists of dictionaries.
  (awood@redhat.com)
- Hide item when server does not support overrides. (mstead@redhat.com)
- Show message instead of repo table when no repos exist. (mstead@redhat.com)
- Made Repository Details resemble Subscription Details (mstead@redhat.com)
- Created an overrides module (mstead@redhat.com)
- Created Repository Management Dialog (mstead@redhat.com)
- Add 'repo-override' command to alter content repositories server-side.
  (awood@redhat.com)

* Thu Nov 07 2013 ckozak <ckozak@redhat.com> 1.10.6-1
- 985502: Use yum.i18n utf8_width function for string length in CLI
  (ckozak@redhat.com)
- 916666: Displayed 'Next System Check-In' is inaccuarate (wpoteat@redhat.com)
- Change wording for identity in CLI command. (dgoodwin@redhat.com)
- 1019753: Stop including a fake consumer UUID fact. (dgoodwin@redhat.com)
- 1022198: Display highest suggested quantity in contract selection
  (ckozak@redhat.com)
- Hook up the 'why register' dialog from old rhn-client-tools.
  (dgoodwin@redhat.com)
- Add screen to describe and skip registration in Fedora/EL7 firstboot.
  (dgoodwin@redhat.com)
- Fix firstboot on Fedora 19. (dgoodwin@redhat.com)
- Report distribution.version.modifier fact. ex 'beta' (ckozak@redhat.com)
- Center filter dialog on parent window when opened (mstead@redhat.com)
- Sort owner list in org selection screen (mstead@redhat.com)
- 1004318: Bash completion for rct was not handing options and file lists
  correctly. (bkearney@redhat.com)
- 1023166: Strip leading and trailing whitespaces from all usernames and
  passwords provided on the cli (bkearney@redhat.com)
- 963579: Stop hiding the Library environment. (dgoodwin@redhat.com)
- Fix layout issues with select sla screen in firstboot. (alikins@redhat.com)
- Fix the layout for "Confirm Subscriptions" screen. (alikins@redhat.com)

* Fri Oct 25 2013 ckozak <ckozak@redhat.com> 1.10.5-1
- 1021581: account/contract display nothing when no data exists
  (ckozak@redhat.com)
- Swap heading of selectsla/confirmsubs widgets. (alikins@redhat.com)
- 1006748: replace simplejson with 'ourjson' (alikins@redhat.com)

* Thu Oct 17 2013 ckozak <ckozak@redhat.com> 1.10.4-1
- 1017351: ignore dbus failures on show_window (alikins@redhat.com)
- 1016643: Fix firstboot issues with new firstboot. (alikins@redhat.com)
- 1005420: adding --ondate to manpage (dlackey@redhat.com.com)
- 1007580: Add contract number to the output of list --available
  (bkearney@redhat.com)
- 1017299: handle dmidecode module not installed (alikins@redhat.com)
- 846331: Add tooltips to the filters page (bkearney@redhat.com)
- 1015553: fix help message for no-overlap. display usage requirement
  (ckozak@redhat.com)

* Wed Oct 02 2013 ckozak <ckozak@redhat.com> 1.10.3-1
- Latest strings from zanata. (alikins@redhat.com)
- Latest string catalog. (alikins@redhat.com)
- point at the zanata 1.10.x version/branch (alikins@redhat.com)
- Run 'make update-po' on translations. (awood@redhat.com)
- Latest translations from Zanata. (awood@redhat.com)
- Merge pull request #782 from candlepin/ckozak/environment_completion
  (alikins@redhat.com)
- Merge pull request #776 from candlepin/alikins/1008462_log_virt_what
  (c4kofony@gmail.com)
- 1011712: add missing environments completion (ckozak@redhat.com)
- Merge pull request #773 from candlepin/ckozak/match_gui_filters
  (alikins@redhat.com)
- Merge pull request #787 from candlepin/awood/1006985-abort-migration
  (alikins@redhat.com)
- Use all keywords args for call to get_avail_ents (alikins@redhat.com)
- Add 'providedProducts' to test pool (alikins@redhat.com)
- stylish cleanups (alikins@redhat.com)
- removed subscribed filter, added testing (ckozak@redhat.com)
- Add some tests cases for managerlib.get_avail_ents (alikins@redhat.com)
- fix wrong index in get_filtered_pools_list (ckozak@redhat.com)
- remove unused args, remove unnecessary idcert read (ckozak@redhat.com)
- add completion for new CLI filters (ckozak@redhat.com)
- 654501: add some filtering to list available (ckozak@redhat.com)
- Merge pull request #765 from candlepin/alikins/redhataccount
  (awood@redhat.com)
- Move capture() context manager to fixtures.py (awood@redhat.com)
- Merge pull request #786 from candlepin/ckozak/cli_list_provided
  (alikins@redhat.com)
- 1006985: Abort migration when we detect different certs with the same ID.
  (awood@redhat.com)
- Merge pull request #781 from candlepin/ckozak/cat_cert_unlimited
  (alikins@redhat.com)
- 996993: add provided to list available (ckozak@redhat.com)
- Merge pull request #784 from candlepin/ckozak/gui_unentitled_string
  (alikins@redhat.com)
- 1012501: Correct number of entitled products with expired ents
  (ckozak@redhat.com)
- 1012566: rhsmd cron job 700 (ckozak@redhat.com)
- 1011703: Do not allow selection on listview (mstead@redhat.com)
- Merge pull request #779 from candlepin/alikins/flex_branding3
  (c4kofony@gmail.com)
- 1011961: -1 quantity is printed as unlimited (ckozak@redhat.com)
- Merge pull request #774 from candlepin/ckozak/fix_gui_completion
  (alikins@redhat.com)
- Make certlib repo and brand updating similar. (alikins@redhat.com)
- 1004385: remove some gtk help options (ckozak@redhat.com)
- Make BrandingInstaller run every cert install/rm (alikins@redhat.com)
- Merge pull request #778 from candlepin/ckozak/update_repolib_attach
  (alikins@redhat.com)
- keep repolib in certmgr (ckozak@redhat.com)
- 1011234: no service level displays empty string (ckozak@redhat.com)
- 1008016: update repos on certlib change (ckozak@redhat.com)
- fix traceback when poolstash is empty (ckozak@redhat.com)
- 1008462: log more virt-what output (alikins@redhat.com)
- 1008462: Log detected virt info as we detect it. (alikins@redhat.com)
- 1004341: gui completion no longer resets (ckozak@redhat.com)
- Merge pull request #761 from candlepin/ckozak/overlap_filter_ondate
  (alikins@redhat.com)
- Refactor credentials gathering. (awood@redhat.com)
- Merge pull request #771 from candlepin/alikins/cmd_name_logging
  (jmrodri@nc.rr.com)
- Merge pull request #769 from
  candlepin/ckozak/catch_exception_updating_installed (jmrodri@nc.rr.com)
- Merge remote branch 'origin/master' into alikins/redhataccount
  (awood@redhat.com)
- Merge pull request #768 from candlepin/ckozak/status_ondate_completion
  (jmrodri@nc.rr.com)
- Merge pull request #766 from candlepin/alikins/make_zanata
  (jmrodri@nc.rr.com)
- 973838: refresh redhat.repo after register (alikins@redhat.com)
- make default logger include sys.argv[0] (alikins@redhat.com)
- Merge pull request #770 from candlepin/mstead/add-virt-type-info
  (c4kofony@gmail.com)
- Add System Type to output of list --consumed (mstead@redhat.com)
- Add Type column to Confirm Subscription screen (mstead@redhat.com)
- 1008603: Catch and log connection error while updating installed products
  (ckozak@redhat.com)
- Merge pull request #767 from candlepin/ckozak/attach_suggested_quantity
  (wpoteat@redhat.com)
- 1004385: Add missing rhsm-icon debug options (ckozak@redhat.com)
- suggested quantity in list available (ckozak@redhat.com)
- Merge pull request #754 from candlepin/alikins/flex_branding2
  (c4kofony@gmail.com)
- 1001820: added ondate to completion (ckozak@redhat.com)
- cleanup comments (alikins@redhat.com)
- remove call on filter change, use None instead of now (ckozak@redhat.com)
- Adding autocomplete stuff for new migration script options.
  (awood@redhat.com)
- 767754: overlap filter ondate (ckozak@redhat.com)
- Add a 'make zanata' target that syncs zanata (alikins@redhat.com)
- Adding unit tests for new migration script options. (awood@redhat.com)
- Correct failing unit tests and add convenience method. (awood@redhat.com)
- Change brand attribute from 'os' to 'brand_type' (alikins@redhat.com)
- Make rct show branding info (alikins@redhat.com)
- Move to RHELBrandsInstaller by default. (alikins@redhat.com)
- Split RHEL specific brand install bits (alikins@redhat.com)
- Add a BrandsInstaller that handles multiple brands (alikins@redhat.com)
- Invert dependencies, and add RHEL specific impls. (alikins@redhat.com)
- Stylish cleanups. (alikins@redhat.com)
- Added new parameters to the script (tazimkolhar@gmail.com)
- clean up comments (alikins@redhat.com)
- More entbranding logging and testing. (alikins@redhat.com)
- Allow multi ents that provide identical branding (alikins@redhat.com)
- More entbranding test cases. (alikins@redhat.com)
- Add BrandPicker and Brand base class. (alikins@redhat.com)
- Add branding support to ent cert importer. (alikins@redhat.com)
- Update branding on cert sorter dir moniter event (alikins@redhat.com)
- Move all branded product logic to entbranding (alikins@redhat.com)
- make it more clear this is for RHEL branded ents (alikins@redhat.com)
- Add support for populating product branding info. (alikins@redhat.com)

* Thu Sep 12 2013 Alex Wood <awood@redhat.com> 1.10.2-1
- update translations from zanata (alikins@redhat.com)
- 1004893: update prods before compliance (ckozak@redhat.com)
- 1004908: Remove the rhn-setup-gnome dep even more. (alikins@redhat.com)
- 1004908: move rhn-setup-gnome requires to -gui subpackage
  (pbabinca@redhat.com)
- 1004385: rhsm icon completion fix (ckozak@redhat.com)
- 1004341: add gui completion (ckozak@redhat.com)
- 1001820: fix autocompletion (ckozak@redhat.com)
- rev min python version for "make stylish" to 2.6 (alikins@redhat.com)
- 994344: messaging for bad filetypes (ckozak@redhat.com)
- 995597: continue attaching if a pool cannot be found (ckozak@redhat.com)
- 1001169: fix pythonic empty string identity problems (ckozak@redhat.com)

* Thu Aug 22 2013 Alex Wood <awood@redhat.com> 1.10.1-1
- Adding Fedora 20 branch to releaser. (awood@redhat.com)
- Subscribe/unsubscribe mirror attach/remove tests (alikins@redhat.com)
- Revert "990195: remove subscribe options" (alikins@redhat.com)
- 994620: reword tooltip message (ckozak@redhat.com)
- 997935: stop making requests after unregister (ckozak@redhat.com)
- 997740: allow autoheal call more often (ckozak@redhat.com)
- Prevent name collision over the parent variable in RHEL 5 Firstboot.
  (awood@redhat.com)
- 997189: error is now a sys.exc_info() tuple. (awood@redhat.com)
- self._parent is not defined here. (awood@redhat.com)
- bump version and remove rhel-6.5 releaser (jesusr@redhat.com)
- Convert contract selection window to use a MappedListStore.
  (awood@redhat.com)
- Stripe rows whenever the My Subs or All Available tabs are shown.
  (awood@redhat.com)
- 991165: Refresh row striping after the TreeView is resorted.
  (awood@redhat.com)
- Remove unused background attribute in Installed Products tab.
  (awood@redhat.com)
- Set background color on progress bar renderer. (awood@redhat.com)
- No need to set a hint to true in glade then false in code. (awood@redhat.com)
- Remove duplicate import. (awood@redhat.com)
- Add a very simple "smoke" test script (alikins@redhat.com)
- 842402: Re-aligning Subscription Manager Gui (cschevia@redhat.com)

* Wed Aug 14 2013 jesus m. rodriguez <jesusr@redhat.com> 1.9.2-1
- 851321: Refresh/redraw tables after removing subscriptions (cschevia@redhat.com)
- 974587: allow certs with no content (ckozak@redhat.com)
- 977920, 983660: manpage updates (dlackey@redhat.com.com)
- 987579: Re-arranged preferences dialog (cschevia@redhat.com)
- 990195: remove subscribe options (ckozak@redhat.com)
- 991214: refresh ent dir, catch exception gracefully (ckozak@redhat.com)
- 991548: Display correct error message for registration failures.  (awood@redhat.com)
- 991580: add rhsmd debug to stdout (ckozak@redhat.com)
- 993202: fix default config, take advantage of rhsmconfig options (ckozak@redhat.com)
- 994266: list consumed shows expired bugs (ckozak@redhat.com)
- 994997: Fix Unknown is_guest during firstboot. (dgoodwin@redhat.com)
- Changed 'It is' to possessive 'Its' (cschevia@redhat.com)
- Remove unused WARNING_DAYS variable (ckozak@redhat.com)
- Bump python-rhsm requires to 1.9.1 for config changes. (dgoodwin@redhat.com)
- add ondate to status (ckozak@redhat.com)
- Fedora 17 is at end of life. (awood@redhat.com)

* Wed Jul 31 2013 Alex Wood <awood@redhat.com> 1.9.1-1
- latest translations from zanata (alikins@redhat.com)
- Preserve traceback when an exception is thrown from background thread.
  (awood@redhat.com)
- Remove logging of injection setup (alikins@redhat.com)
- 988411: more at-spi changes for QA (ckozak@redhat.com)
- 908521: Pull in the latest mr strings (bkearney@redhat.com)
- 928469: Pull in latest ml strings from zanata (bkearney@redhat.com)
- 927990: Pull in latest ta_IN strings from zanata (bkearney@redhat.com)
- 987579: Make clicking autoheal label work (cschevia@redhat.com)
- 988430, 988861: remove logging from write_cache to avoid segfault
  (ckozak@redhat.com)
- 966422: Do not hang firstboot if there is an exception during registration.
  (awood@redhat.com)
- 978329: catch IdentityCertException gracefully (ckozak@redhat.com)
- 988482: fix gtk warnings on gtk-2.10 (alikins@redhat.com)
- 988411: fixed at-spi locator name (ckozak@redhat.com)
- fixed dbus on rhel5 (ckozak@redhat.com)
- 987071: specify arch of librsvg dep (alikins@redhat.com)
- 987626: Remove PUTS while opening preferences dialog, fix related test
  (cschevia@redhat.com)
- 987551: correctly reconnect to rhsmd daemon (ckozak@redhat.com)
- 981611, 981565: fixed icon and text truncation (ckozak@redhat.com)
- rev zanata branch to 1.9.X (alikins@redhat.com)
- Rev master to 1.9.x (alikins@redhat.com)
- 968820: raise timeout exceptions for cli calls (alikins@redhat.com)
- 950892: add ents-nag-warning.png to docs install (alikins@redhat.com)
- add new file to spec (ckozak@redhat.com)
- 978466: fix missing socket info s390x/ppc64 (alikins@redhat.com)
- 985515: moved DbusIface to fix anaconda productId (ckozak@redhat.com)
- 983193: remove unused 'Virt Limit' cat-cert field (alikins@redhat.com)
- Correcting whitespace error. (awood@redhat.com)
- 986971: String Update: Quantity > Available (cschevia@redhat.com)
- 980724: allsubstab cleared on identity change, check redeem on register
  (ckozak@redhat.com)
- 921222: add 'status' to bash completion (alikins@redhat.com)
- 977580: Preferences dialog hide and show (cschevia@redhat.com)
- 977481: make proxy cli check require_connection (alikins@redhat.com)
- 977896: Fixes for Workstation/Desktop certs (alikins@redhat.com)
- Added comma to satisfy grammar rules (cschevia@redhat.com)
- added at-spi locator for autoheal checkbox (jmolet@redhat.com)
- 984203: Fix german translations (bkearney@redhat.com)
- 974587: Add more checks for no order portion being present
  (bkearney@redhat.com)
- 984206: Removed Spaces from String (cschevia@redhat.com)
- Remove releasers due to branching. (dgoodwin@redhat.com)
- 983670: Improved auto-attach description (cschevia@redhat.com)
- 982286: Adjusted markup removal (cschevia@redhat.com)
- 983250: 983281: certs check warning period (ckozak@redhat.com)
- Adding Fedora 19 Yum releasers. (awood@redhat.com)

* Wed Jul 10 2013 jesus m. rodriguez <jesusr@redhat.com> 1.8.13-1
- Latest translations from zanata. (dgoodwin@redhat.com)
- new strings (jesusr@redhat.com)

* Wed Jul 10 2013 jesus m. rodriguez <jesusr@redhat.com> 1.8.12-1
- 877331: Add --org and --environment options to migration script.  (awood@redhat.com)
- 915847: Clear old proxy settings if the --no-proxy option is used. (awood@redhat.com)
- 928401: Fixed translation issue in redeem dialog (cschevia@redhat.com)
- 974123: default behavior is help, no longer status (ckozak@redhat.com)
- 976689: Handle no xorg server, allow help (ckozak@redhat.com)
- 976848: 976851: thread cache write, limit disk reads, singleton
- 976865: dbus iface singleton for gui (ckozak@redhat.com)
- 976866: single instance of ProdDir and EntDir (ckozak@redhat.com)
- 976868: improve rhsmd logging (alikins@redhat.com)
- 976868: enable logging from /usr/libexec/rhsmd (alikins@redhat.com)
- 976924: empty service level and type (ckozak@redhat.com)
- 977481: added proxy options to status (ckozak@redhat.com)
- 977535: cli uses utf8 too (ckozak@redhat.com)
- 977851: 977321: Centralize CertSorter, drive updates, refresh properly
- 978322: fixed client deleting certs (ckozak@redhat.com)
- 979492: register auto-attach force recreates cert dirs (ckozak@redhat.com)
- 980209: removed injection calls from migration script (ckozak@redhat.com)
- 980640: include stacked ents in provided (ckozak@redhat.com)
- 981689: fix attach command (ckozak@redhat.com)
- 982286: Fixed empty dialog message (cschevia@redhat.com)
- latests strings from zanata and new keys.pot (alikins@redhat.com)
- Fixed Preferences dialog to be non-threaded (cschevia@redhat.com)
- updated spec to require python-rhsm v1.8.13-1 or greater (cschevia@redhat.com)
- Added auto-attach property in the preferences dialog (cschevia@redhat.com)
- Added autoheal command to subman CLI (cschevia@redhat.com)
- Add support for SUBMAN_DEBUG to log to stdout (alikins@redhat.com)
- remove logging of plugin args (alikins@redhat.com)
- Fixed auto-complete script for auto-attach command (cschevia@redhat.com)
* Thu Jun 20 2013 jesus m. rodriguez <jesusr@redhat.com> 1.8.11-1
- 844532: xen dom0 cpu topology lies, work around it (alikins@redhat.com)
- 854380: fix overlap filter (ckozak@redhat.com)
- 915847: Provide option to skip using proxy when connecting to RHSM.
- 921222: Fixed tab completion (cschevia@redhat.com)
- 922871: Call pre_product_id_install hook on product install (mstead@redhat.com)
- 924766: Show machine type when attaching 'virt only' subscriptions (wpoteat@redhat.com)
- 927340: added empty warning, block auth unless proxy enabled (ckozak@redhat.com)
- 928401: Fixed translation issue in redeem dialog (cschevia@redhat.com)
- 947485: System 'disconnected' if no cache and disconnected (ckozak@redhat.com)
- 947788: facts plugin can handle no 'facter' (alikins@redhat.com)
- 966137: stat-cert handles ent cert with no content (alikins@redhat.com)
- 972883: Add entries to productid.js during migration. (awood@redhat.com)
- 973938: Flush std out and catch errors to work around the broken pipe from the more command (bkearney@redhat.com)
- 974123: default behavior is help, no longer status (ckozak@redhat.com)
- 974587: Allow list --consumed to handle certificates with empty order sections (bkearney@redhat.com) (awood@redhat.com)
- 975164: 975186: fix certlib exception handling (ckozak@redhat.com)
- Pull PluginManager from dependency injection framework (mstead@redhat.com)
- Performance enhancements (ckozak@redhat.com)
- added cp_provider doc strings, modified test fixture (ckozak@redhat.com)
- Fix expand options so there is no border txt view (alikins@redhat.com)
- Make PluginManager lazy loading (mstead@redhat.com)

* Tue Jun 04 2013 jesus m. rodriguez <jesusr@redhat.com> 1.8.10-1
- 922825: pre_subscribe conduit now contains more data (mstead@redhat.com)
- 921222: Fixed subman auto-complete scripts (cschevia@redhat.com)
- 922806: Fix RHEL 5 firstboot issue with backButton. (dgoodwin@redhat.com)
- 960465: Subman disconnected when consumer cert is invalid (ckozak@redhat.com)
- 966747: handle a custom facts file being empty (alikins@redhat.com)
- 969280: Fix traceback on disconnected sub detach (ckozak@redhat.com)
- handle s390x's without vm info in sysinfo (alikins@redhat.com)

* Fri May 31 2013 jesus m. rodriguez <jesusr@redhat.com> 1.8.9-1
- 905136: added accessibily name for owner_label (jmolet@redhat.com)
- 928175: fixed status command after user deletion (ckozak@redhat.com)
- 950672: Added data for yellow. Added list view. (ckozak@redhat.com)
- 963796: Unified descriptions (cschevia@redhat.com)
- 966745: Correct typo in name of configuration value. (awood@redhat.com)
- 967863: Suggest package to install when mapping file is missing. (awood@redhat.com)
- 968364: show the issuer for certs in rct. (bkearney@redhat.com)
- 966262 for rct.8; 959563 for subscription-manager.8 (dlackey@redhat.com.com)
- Extract latest strings from code. (dgoodwin@redhat.com)
- close file objects deliberately (alikins@redhat.com)
- Use fnmatch to add wildcard support (bkearney@redhat.com)
- One more miss from my issuer/errata debacle (bkearney@redhat.com)
- Extend use of compliance status from cp (ckozak@redhat.com)
- Add s390 lpar specific socket counting (alikins@redhat.com)
- be extra paranoid and strip nul from /sys reads (alikins@redhat.com)
- use new cpu info method by default (alikins@redhat.com)
- Add a new method for calculating cpu sockets (alikins@redhat.com)
- Added reasons to Subscription Details (ckozak@redhat.com)
- Support enable and disable of all repos. (bkearney@redhat.com)

* Tue May 21 2013 jesus m. rodriguez <jesusr@redhat.com> 1.8.8-1
- Fix echo'ing of exit status or exception on exit (alikins@redhat.com)
- 962905: Fixing errors with quantity spinner. (awood@redhat.com)
- 961124: Allow rct dump-manifest to be called more than once (bkearney@redhat.com)
- 921249: Fix Unknown virt status being reported to server.  (dgoodwin@redhat.com)
- 905136: Make the accessability value unique (bkearney@redhat.com)
- 913635: typo (dlackey@redhat.com.com)
- 889582 (dlackey@redhat.com.com)
- 962520: require python-rhsm 1.8.11 for arches (alikins@redhat.com)
- 919706: Relax rhn-setup-gnome dependency. (dgoodwin@redhat.com)
- Add new expiring icon (bkearney@redhat.com)
- use os.linesep as imported (alikins@redhat.com)
- cleanup camelCase usage in various files (alikins@redhat.com)
- adding architecture data (ckozak@redhat.com)
- Default option is status (ckozak@redhat.com)
- changed list --status to status (ckozak@redhat.com)
- adding data to installed prods (ckozak@redhat.com)
- SORT ALL THE IMPORTS! (alikins@redhat.com)
- stylish cleanup (alikins@redhat.com)
- mock.patch ConsumerIdentity instead of monkey patch (alikins@redhat.com)

* Thu May 09 2013 jesus m. rodriguez <jesusr@redhat.com> 1.8.7-1
- 959563, 956298: for rhel 5.10 (dlackey@redhat.com.com)
- 905922: use get_int instead of get in order to consume the value as a
  booolean (bkearney@redhat.com)
- enhancements to tests (alikins@redhat.com)
- Update expected rct output for content arch info (alikins@redhat.com)
- let 'rct cat-cert' show arches info on content sets (alikins@redhat.com)
- Use the unknown icon when it is appropriate. (bkearney@redhat.com)
- Do not allow manual entry of numbers that aren't multiples of spinner
  increment. (awood@redhat.com)
- 959570: Subscription names were being mangled in the installed products page.
  (bkearney@redhat.com)
- 959124: Consistant system status between CLI and GUI (ckozak@redhat.com)
- re-added compatibility for old candlepin servers. (ckozak@redhat.com)
- 885130: Switch from using xmlrpclib to rhnlib's rpclib. (awood@redhat.com)
- 958827: fixed duplicate reasons from bundled subs, removed messages for valid
  products, refactoreed client-side reasons code (ckozak@redhat.com)
- 958775: correct info for future subscriptions (ckozak@redhat.com)
- Removing messages from compliant installed products caused by bad overconsumption (ckozak@redhat.com)
- Use server provided value to determine quantity increment. (awood@redhat.com)
- 957218: Bump system.certificate_version for cores support (mstead@redhat.com)
- 956285, 913635, 913628. still need to finalize output for 913628.  (dlackey@redhat.com.com)
- 955142: Display core limit in rct cat-cert tool (mstead@redhat.com)
- Warn when we detect we need a newer version of 'mock' (alikins@redhat.com)
- 924919: remove loging about isodate implementation (alikins@redhat.com)
- 957195: Pull in the latest or fix from zanata. (bkearney@redhat.com)
- Add the unkown icon (bkearney@redhat.com)
- Add reasons to list --installed and list --consumed.  Added list --status
  (ckozak@redhat.com)
- 908037: remove all ¶ characters from the ml.po file. Zanata was also updated
  (bkearney@redhat.com)
- 906552: Fixed mis translation of subscription-manager in pa.po and zh_CN.po.
  Zanata was also updated (bkearney@redhat.com)
- 908059: Fix a pt_BR translation which did not include the http portion of a
  url. Zanata is fixed as well (bkearney@redhat.com)
- Add F19, 5.10, 6.4 releasers. (dgoodwin@redhat.com)
- use "assert_string_equal" for multiline str asserts (alikins@redhat.com)
- add "assert_string_equals" that diffs multiline strings (alikins@redhat.com)

* Thu Apr 18 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.6-1
- Latest translations. (dgoodwin@redhat.com)
- 903298: Fix a few more examples of Register to (bkearney@redhat.com)
- 878634: Fix the final three uses of id instead of ID (bkearney@redhat.com)
- Fix string formatting done outside of gettext _() (alikins@redhat.com)
- 950892: entity typo (dlackey@redhat.com.com)
- when no parameters are given, dump manifest uses current directory
  (ckozak@redhat.com)
- fixed zipfile creation in python 2.4 (ckozak@redhat.com)
- 919561: moving cat manifest into memory (ckozak@redhat.com)
- 914717: Fields taken from pool data. (wpoteat@redhat.com)
- 924919: stop log to stderr in isodata module (alikins@redhat.com)
- 919561: refactored some code into additional methods, fixed naming
  conventions, and added test cases (ckozak@redhat.com)
- Dont log exception if a repo doesn't have productid (alikins@redhat.com)
- 919561: checking manifest zip for files outside of scope (ckozak@redhat.com)
- 919561: moved new extractall into a class that extends ZipFile
  (ckozak@redhat.com)
- 919561: fixed variable naming in new extractall method (ckozak@redhat.com)
- 919561: replaced reference to zipfile.extractall (aded in python2.6)
  (ckozak@redhat.com)

* Wed Mar 27 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.5-1
- 927875: Fix GUI bug if there is an expired certificate. (dgoodwin@redhat.com)
- 922806: Use dependency injection with firstboot module. (awood@redhat.com)
- 919512: Remove proxy options from config command. (awood@redhat.com)
- 921126: latest string updates from zanata (alikins@redhat.com)
- 919255: Remove extraneous print statement. (awood@redhat.com)
- 919584: Fix unicode error in RHEL 5. (awood@redhat.com)
- Implement entitlement/product status caching. (dgoodwin@redhat.com)
- 921245: Update installed products tab after registration. (awood@redhat.com)
- 893993: some refactoring, show_autosubscribe_output returns 0 or 1
  (ckozak@redhat.com)
- 859197: add special case for products that provide 'rhel-' tags
  (alikins@redhat.com)
- productid db now supports multiple repos per product id (alikins@redhat.com)
- let ProductData support multiple repos per product (alikins@redhat.com)
- 893993: attach --auto now prints the proper text when no products are
  installed (ckozak@redhat.com)
- 918746: Switched or ordering for disabling repos.  Will now print all
  repository validation errors (ckozak@redhat.com)
- 914717: rct cat-manifest fails to report Contract from the embedded
  entitlement cert (wpoteat@redhat.com)
- More convenient dep injection. (dgoodwin@redhat.com)
- Try to handle the really old dbus-python on rhel5 (alikins@redhat.com)
- add missing conf file for all_slots plugin (alikins@redhat.com)
- 919700: Reload consumer identity after force subscribing.
  (dgoodwin@redhat.com)
- utils.parseDate is now isodate.parse_date (alikins@redhat.com)
- Remove  ent/prod dir arguments to CLI commands. (dgoodwin@redhat.com)
- PluginsCommand does not need network cli options (alikins@redhat.com)
- Fix pluginDir config value in default config file (alikins@redhat.com)

* Fri Mar 08 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.4-1
- Pull latest strings from zanata. (dgoodwin@redhat.com)
- Use PyXML for iso8601 date on RHEL5 and dateutil after (alikins@redhat.com)
- Major switchover to server for compliance checking logic. (dgoodwin@redhat.com)
- Introduce dependency injection framework. (dgoodwin@redhat.com)
- 916369: Do not persist config changes until the action completes
  (bkearney@redhat.com)
- Fix a bug with changing installed products during healing.
  (dgoodwin@redhat.com)
- 912776: fix migration test scripts to expect get_int usage
  (alikins@redhat.com)
- 912776: cast port numbers from cli to int immediately (alikins@redhat.com)
- 912776: use config.get_int for server port as well (alikins@redhat.com)
- 905649: subscription-manager does not work with dbus-python-1.1.1-1
  (wpoteat@redhat.com)
- use ngettext for plural messages in certlib/managercli (alikins@redhat.com)
- 912776: use cfg.get_int for proxy port (alikins@redhat.com)
- 878097: update service-level org key help text (alikins@redhat.com)
- Handle manifests with no subscriptions in the archive (alikins@redhat.com)
- 878664: Add filename support to the bash completion for the rct tool.
  (bkearney@redhat.com)
- 877590: Changes to the branding messages when the user attempts to register
  twice (bkearney@redhat.com)
- New plugin framework. (alikins@redhat.com / awood@redhat.com)
- 886115: Remove line continuations within strings. (bkearney@redhat.com)
- 913302: Support Level and Support Type should be shown as Service Level and
  Service Type (bkearney@redhat.com)
- Add unknown product status state. (dgoodwin@redhat.com)
- 913703: Prefer the use of SKU over Product ID (bkearney@redhat.com)
- 913720: Use the term order number instead of subscription id
  (bkearney@redhat.com)
- 878634: Use correct capitalization for ID in the rct tool
  (bkearney@redhat.com)
- 878097: Help text for service-level command should be consistent with other
  help texts (bkearney@redhat.com)
- 906554: Add ui_repoid_vars line to yum based on the variables which are in
  the baseurl (bkearney@redhat.com)
- 912707: Remove a use of the deprecated hasNow() function.
  (bkearney@redhat.com)
- 913187: Allow older manifests to print out correctly. (bkearney@redhat.com)
- 912776: Cast proxy port to an integer. (awood@redhat.com)
- 882459: Deprecated message in help for cert-interval (wpoteat@redhat.com)
- 895447: Changed messages to distinguish between local and server-side
  removal. (wpoteat@redhat.com)
- 908671: Display the pool ID when available. (awood@redhat.com)
- 911386: Displaying combined Service Level and Type should handle empty values
  for both items (jmolet@redhat.com)

* Thu Feb 14 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.3-1
- string and string catalog update from zanata (alikins@redhat.com)
- 908954: Ensure that 'Not Set' is shown in the preferences dialog if it is not
  set (bkearney@redhat.com)
- 906214: rct --help should return 0. (bkearney@redhat.com)
- 909294: Add accessibility names to the preferences combo boxes
  (bkearney@redhat.com)
- 878097: Clarify that the --org option is ORG_KEY and not ORG_NAME
  (bkearney@redhat.com)
- Just use 0 as error for reading int keys (alikins@redhat.com)
- Old version of config entries considered to make changes backwards compatible
  (wpoteat@redhat.com)
- 882459: aftermath of bug 876753 - Change --heal-interval to --attach-interval
  in rhsmcertd (wpoteat@redhat.com)

* Fri Feb 08 2013 Bryan Kearney <bkearney@redhat.com> 1.8.2-1
- Update tito for RHEL 7.0 (bkearney@redhat.com)
- Small cleanups for test_migrate (alikins@redhat.com)
- Write repofile once instead of during every iteration. (awood@redhat.com)
- Add unit test for migration script. (awood@redhat.com)
- Adding more tests for the migration script. (awood@redhat.com)
- Bump the required version of python-rhsm to pick up the new config file
  defaults (bkearney@redhat.com)
- Modify migration script tests to run on Fedora. (awood@redhat.com)
- Give users the ability to disable package reporting (bkearney@redhat.com)
- 891377: Note in deprecated string that auto-attach-interval is a command
  option (bkearney@redhat.com)
- 901612: Yum plugin warnings should go to stderr, not stdout
  (bkearney@redhat.com)
- 903298: Replace use of 'Register to' with 'Register with'
  (bkearney@redhat.com)
- Rewrite of the migration script featuring unit tests. (awood@redhat.com)
- Remove F16 and old cvs releasers, add F18. (dgoodwin@redhat.com)

* Thu Jan 24 2013 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.1-1
- Add two manifest commands to rct. (bkearney@redhat.com)
- latest translations from zanata (alikins@redhat.com)
- 895447: The count of subscriptions removed is zero for certs that have been
  imported. (wpoteat@redhat.com)
- 895462: Message for subscription-manager repos --list for disabled repo needs
  to be modified (wpoteat@redhat.com)
- 885964: After registration, recreate the UEP connection using the identity
  cert. (awood@redhat.com)
- 869306: Add org ID to facts dialog. (awood@redhat.com)
- 888853: Put output into proper columns regardless of the output language.
  (awood@redhat.com)
- Update python-rhsm requires version (wpoteat@redhat.com)
- 888052: Add all binaries to the makefile path for gettext string extraction
  (bkearney@redhat.com)
- 851303: additional term updates (dlackey@redhat.com.com)
- 844411: Add an --insecure option to subscription-manager. (awood@redhat.com)
- 891621: Users can incorrectly enter activation keys when registering to
  hosted. (awood@redhat.com)
- 889573: Only persist serverurl and baseurl when registering.
  (awood@redhat.com)
- 889204: Encode the unicode string to utf-8 to avoid syslog errors
  (bkearney@redhat.com)
- 889621: String substitution inside gettext causes message translations to
  never be found (bkearney@redhat.com)
- 890296: Unicode characters with a - are causing printing issues for rct
  printing (bkearney@redhat.com)
- 878269 (dlackey@redhat.com.com)
- 784056: Raise a running instance of the GUI to the forefront.
  (awood@redhat.com)
- 888968: Improve the gui message formatting for SLA selection
  (bkearney@redhat.com)
- 873601: Return a non zero code if subscription manager is run with an
  incorrect command name (bkearney@redhat.com)
- 839779: Improve messaging when autosubscribe does not work because of SLA
  (bkearney@redhat.com)
- 867603: Add quantity to confirm subscriptions dialog. (awood@redhat.com)
- 888790: Rebuild UEP connection after registering with activation keys.
  (awood@redhat.com)
- 886280; 878257; 878264; 878269 (dlackey@redhat.com.com)
- 814378: disable linkify if we are running as firstboot (alikins@redhat.com)
- 886887: Take the user back to the activation key page if he enters an invalid
  key. (awood@redhat.com)
- 863572: Make forward/back insensitive when registering (alikins@redhat.com)
- 825950: updating SAM registration procedure; other term edits and updated
  screenshot (dlackey@redhat.com.com)
- 885964: Do not make a getOwner call when not necessary. (awood@redhat.com)
- Ask for the org in environments and service-level modules. (awood@redhat.com)
- 886992: Fix for bad fix for 886604, wrong path for yum repos
  (alikins@redhat.com)
- matt reid's edits to rct; bz886280; bz878257; bz878269; bz878264
  (dlackey@redhat.com.com)
- 841496: Do not use hyphens in bash completion files as these are invalid for
  identifiers in the sh shell. (bkearney@redhat.com)
- Improve logging for rhsmcertd scenarios (wpoteat@redhat.com)
- 878609: Do not use public url redirectors, instead use a redhat.com address
  (bkearney@redhat.com)
- 886604: Fix incorrect path in repos.d check (alikins@redhat.com)
- 727092: Read in the org key during registration if none is given.
  (awood@redhat.com)
- 845622: If an identity certificate has expired, there should be a friendly
  error message (wpoteat@redhat.com)
- 883123: Have the migration code use the name and the label for org and
  environment lookup. (bkearney@redhat.com)
- 886110: help blurb for --auto-attach formatted poorly (alikins@redhat.com)
- 880070: require latest python-rhsm to handle unicode issues
  (alikins@redhat.com)
- 798788: Results from subscription-manager facts --update after a server-side
  consumer was deleted. (wpoteat@redhat.com)
- 878634: Improve the consistency of capitalization of URL, ID, HTTP, and CPU
  (bkearney@redhat.com)
- 878657: Make consistent use of the term unregister instead of un-register
  (bkearney@redhat.com)
- 883735: load branding module slightly differently (jesusr@redhat.com)
- Stylish fix. (dgoodwin@redhat.com)
- 878664: Add bash completion script for rct (bkearney@redhat.com)
- 880764: Command line options which can be specified more than once should use
  the same help text (bkearney@redhat.com)
- 867070: Adjust default sizing of subscriptions pane in Installed Products
  tab. (awood@redhat.com)
- 873791: Expected exit codes from unsubscribe with multiple serial numbers
  (wpoteat@redhat.com)
- 800323: Set default output stream encoding to UTF-8. (awood@redhat.com)
- 862852: Fix double separator in redeem dialog. (dgoodwin@redhat.com)
- Display "None" if environments value is empty on consumer. (awood@redhat.com)
- 872351: Display environment in GUI facts dialog and CLI identity command.
  (awood@redhat.com)
- 881091: Remove punctuation in the help message (bkearney@redhat.com)
- Revert "878986: refactor to use curses/textwrap for format"
  (alikins@redhat.com)
- 877579: Fix -1 quantity to consume for unlimited pools. (dgoodwin@redhat.com)
- 881117: Add at-spi locator to redemption dialog. (awood@redhat.com)
- 881952: Warn and continue if encountering a failure during system deletion.
  (awood@redhat.com)
- 878820: Fix console error when yum.repos.d does not exist.
  (dgoodwin@redhat.com)
- 839772: Display "Not Set" instead of "" in SLA and release preferences.
  (awood@redhat.com)
- rev zanata branch version to 1.8.X (alikins@redhat.com)
- 878986: refactor to use curses/textwrap for format (alikins@redhat.com)
- 878986: Default to no line breaking if no stty is available
  (bkearney@redhat.com)
- 878588: Move the requires on usermode from subscription-manager-gui to
  subscription-manager (bkearney@redhat.com)
- 878648: Make the help usage formatting consistent for the rct and
  subscription manager commands (bkearney@redhat.com)
- 869046: Remove stray 'print' (jbowes@redhat.com)
- 864207: Autosubscribe should not run when all products are already
  subscribed. (wpoteat@redhat.com)
- 854702: Place the asterisk indicating editability into the quantity cell.
  (awood@redhat.com)

* Tue Nov 20 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.0-1
- Reversioning to 1.8.x stream.

* Mon Nov 19 2012 Adrian Likins <alikins@redhat.com> 1.1.10-1
- latest strings from zanata (alikins@redhat.com)
- 874623: Tell users running the version command if they are not registered.
  (awood@redhat.com)
- 873418: Add at-spi locators to the activation key window. (awood@redhat.com)

* Fri Nov 16 2012 Adrian Likins <alikins@redhat.com> 1.1.9-1
- latest strings from zanata (alikins@redhat.com)
- 864207: mark these strings for translation (alikins@redhat.com)
- 854388: use ngettext to specify contract/contracts (alikins@redhat.com)
- 876753: change rhsmcertd --heal-interval to --auto-attach-interval
  (alikins@redhat.com)
- We require python-rhsm-1.1.5 now (ram) (alikins@redhat.com)
- 876340: Move the last of the commands and help string to --auto-attach
  (bkearney@redhat.com)
- 876294: Use attach instead of subscirbe in the rhn migration tooling
  (bkearney@redhat.com)
- 856735: Move the Next Update notification to the About dialog.
  (awood@redhat.com)
- Removed stacking from RAM (mstead@redhat.com)
- Improved comments/logging/tests for RAM (mstead@redhat.com)
- Updated the entitlement_version of client (mstead@redhat.com)
- Added RAM limit to rct cat-cert output (mstead@redhat.com)
- Removing dead code (mstead@redhat.com)
- Check RAM when determining status (mstead@redhat.com)

* Tue Nov 13 2012 Adrian Likins <alikins@redhat.com> 1.1.8-1
- 862909: install rct man page (alikins@redhat.com)
- Fix to LocalTz DST determination (cduryee@redhat.com)

* Mon Nov 12 2012 Adrian Likins <alikins@redhat.com> 1.1.7-1
- 873631: Migrate correctly when there is only one org. (awood@redhat.com)
- 874147: Handle changes in python-ethool api (alikins@redhat.com)

* Thu Nov 08 2012 Adrian Likins <alikins@redhat.com> 1.1.6-1
- 872847: Change unsubscribe feedback when consumer has been deleted
  (wpoteat@redhat.com)
- 869934: make "release" related cdn usage use proper urlparse
  (alikins@redhat.com)
- 852328: Improve the server version checking (bkearney@redhat.com)
- 871146: Fix proxy errors on first yum operation after registration.
  (dgoodwin@redhat.com)
- 850430: Pressing Enter in the password entry now activates registration.
  (awood@redhat.com)
- Attach subscriptions after registration with an activation key.
  (awood@redhat.com)

* Thu Nov 01 2012 Adrian Likins <alikins@redhat.com> 1.1.5-1
- latest strings from zanata (alikins@redhat.com)

* Wed Oct 31 2012 Adrian Likins <alikins@redhat.com> 1.1.4-1
- 864177: Add the count for the first word in calculating where to break the
  line (bkearney@redhat.com)
- 785666: For bonded interfaces, find mac address of members
  (alikins@redhat.com)
- 839779: Add more context around how to cover the machine with a given SLA
  (bkearney@redhat.com)
- 864177: Attempt to detect the size of the terminal to influence how product
  names are split up. (bkearney@redhat.com)
- 864569: Make the date picker widget 10 characters wide (bkearney@redhat.com)
- 855050: Set the icon-name property on all dialogs and windows
  (bkearney@redhat.com)
- 848095: Reduce the indentation on the help text to improve the layout on
  smaller terminals. (bkearney@redhat.com)
  (wpoteat@redhat.com)
- 862848: Change the name of the button to Cancel instead of Close
  (bkearney@redhat.com)
- 867766: Unsubscribe from multiple entitlement certificates using serial
  numbers (wpoteat@redhat.com)
- Clear any cached environments when registering with activation keys.
  (awood@redhat.com)
  (bryan.kearney@gmail.com)
- Clear any cached activation key values. (awood@redhat.com)
- 869729: --autosubscribe and --activationkey should be mutually exclusive
  (wpoteat@redhat.com)
- 857191: Stacking shows a useless parent in All Available Subscriptions tab
  (wpoteat@redhat.com)
- 863133: Subscription-Manager version command should have server type listed
  first (wpoteat@redhat.com)
- updates for failed-qa issues in bz857195 (dlackey@redhat.com.com)
- Increment the hardcoded page number due to added activation key screen.
  (awood@redhat.com)
- 864555: add "menu" window hint to filters.glade (alikins@redhat.com)
- 850870: Update on-line documentation link. (awood@redhat.com)
- 817671: Add support for Activation Keys in the GUI. (awood@redhat.com)
- 840415: Print an error message if the destination directory does not exist.
  (awood@redhat.com)
- Fail fast if the user enters a bad org. (awood@redhat.com)
- Marking a string for translation. (awood@redhat.com)
- 866579: Fail fast if the user enters a bad environment. (awood@redhat.com)
- Enable logging in firstboot (alikins@redhat.com)
- 865954: Return to creds screen if consumer name is invalid
  (alikins@redhat.com)
- 852107: Make the banners the same width (bkearney@redhat.com)
- 748912: Make the error message a bit more friendly when there is no cert file
  to import (bkearney@redhat.com)
- 865590: Fix broken offline unsubscribe. (dgoodwin@redhat.com)
- 852328: Report Classic and Subscription Management consistently in the
  version and identity commands (bkearney@redhat.com)
- 864159: Add a new message in the gui when no subscriptions are available on a
  specific date. (bkearney@redhat.com)
- 850531: Change the label 'Certificate Status' to 'Status'
  (bkearney@redhat.com)
- 850533: Change the label from 'Next Update' to 'Next System Check-in'
  (bkearney@redhat.com)
- 855365: Display a singular sentence if only one subscription is removed
  (bkearney@redhat.com)
- 862885: Change the text for unlimited to Unlimited (bkearney@redhat.com)
- 864184: Make the machine type uppercase to be consistent with other output
  (bkearney@redhat.com)
- 865545: Added report log when cert has no products. (mstead@redhat.com)
- update releases.conf (alikins@redhat.com)

* Wed Oct 10 2012 Adrian Likins <alikins@redhat.com> 1.1.3-1
- 863961: Expect id cert Version to be populated in tests (alikins@redhat.com)
- 863565: Give focus to the login field during subscription registration.
  (awood@redhat.com)
- 838123: remove python2.5ism (alikins@redhat.com)
- 844072: remove use and dep of PyXML (alikins@redhat.com)
- 838123: Omit mac addresses from facts for lot and sit ipaddress types
  (bkearney@redhat.com)
- 856236: Do not allow environmenets to be specified during registration if an
  activation key is used (bkearney@redhat.com)
- 858289: Rename the desktop file to subscription-manager-gui.deskstop
  (bkearney@redhat.com)
- 808217: Add a text banner to the output of release --list
  (bkearney@redhat.com)
- 863428: Add environment support to the migration script. (awood@redhat.com)
- 862099: Fix several dialog closing issues. (dgoodwin@redhat.com)
- 854374: Removed extra spacing around help, and improved he rct text output a
  bit. (bkearney@redhat.com)
- 853572: Fix a typoin the help messages (bkearney@redhat.com)
- 859090: Remove the word technology from the branding string
  (bkearney@redhat.com)
- 862308: Subscription Manager version reports registered to value when system
  not registered (wpoteat@redhat.com)
- 861443: Re-raise GoneException in rhsmcertd-worker (mstead@redhat.com)
- 861151: make stylish cleanup (alikins@redhat.com)
- 852911: Add padding around firstboot tooltips icon. (dgoodwin@redhat.com)
- 854312: Do not install a certificate that has expired. (mstead@redhat.com)
- Make rhsm-icon work on gnome 3 (jbowes@redhat.com)
- 853885: Fix icon notification popup only displaying once.
  (dgoodwin@redhat.com)
- 853006: Wrap label in the manually subscribe firstboot screen.
  (dgoodwin@redhat.com)
- 861151: release should not list for incompatible variants
  (alikins@redhat.com)
- 861170: re.escape() values provided to the apply_hightlight() function.
  (awood@redhat.com)
- 852630: Suscription manager unsubscribe --all shows error on expired
  subscriptions (wpoteat@redhat.com)
- Freeze obsoletes version for -gnome to -gui rename (jbowes@redhat.com)
- 860084: remove unused _x from ja_JP translation (alikins@redhat.com)
- 860088: remove trailing dot from url in de_DE.po (alikins@redhat.com)
- Don't reparse entitlement certs on every search filter change
  (jbowes@redhat.com)
- 855257: fix issues with default contract quantity being wrong
  (alikins@redhat.com)
- 860088: some translations were splitting urls into two lines
  (alikins@redhat.com)
- Add to nosetest to ensure that Cert V3 check for validity passes.
  (wpoteat@redhat.com)
- 860344: Subscription-manager import --certificate fails to recognize a new
  version 3.0 certificate (wpoteat@redhat.com)
- New icon set. (awood@redhat.com)
- 853035: Fix firstboot "back" issues. (dgoodwin@redhat.com)
- Check the full version info of the yum api in productid (alikins@redhat.com)
- 847319: Left align manually subscribe firstboot message (jbowes@redhat.com)
- 860030: make server_version_check use a non authenticated call
  (alikins@redhat.com)
- 847387: Display tooltip for info icon in RHEL 5.9. (awood@redhat.com)

* Mon Sep 24 2012 Adrian Likins <alikins@redhat.com> 1.1.2-1
- 829825: Adding tests. (awood@redhat.com)
- 853876: No need to check for GoneException when getting status
  (mstead@redhat.com)
- 829825: Disable unsubscribe button when nothing is selected.
  (awood@redhat.com)
- Remove unused import. (awood@redhat.com)
- 859197: Fix product cert cleanup. (dgoodwin@redhat.com)
- 781280: Add I18N comments for some string length issues.
  (dgoodwin@redhat.com)
- 830193: Ensure logging is not diabled by RHN Classic Registration
  (bkearney@redhat.com)
- remove unused RepoFile import (alikins@redhat.com)
- 855081: Translate Arch as Arq. (bkearney@redhat.com)
- Check identity cert permissions when running CLI commands (mstead@redhat.com)
- mock all of RepoFile for the cli tests (alikins@redhat.com)
- 845349: Don't clutter the repo file with empty keys (jbowes@redhat.com)
- 845349: remove 'return' left in for debugging (jbowes@redhat.com)
- Stylish errors for mr.po (bkearney@redhat.com)
- 855085: Fixed the translation for [OPTIONS] (bkearney@redhat.com)
- 855087: Fix a mis translated [OPTIONS] in the mr.po file.
  (bkearney@redhat.com)
- Strings with the same value are not always the same instance.
  (awood@redhat.com)
- updates from sefler for bz850881 (dlackey@redhat.com.com)
- mock out utils.is_valid_server_info for tests (alikins@redhat.com)
- 846207: Print error message for each invalid repo. (awood@redhat.com)
- change test async to check for a number of thread callbacks
  (alikins@redhat.com)
- latest strings from zanata (alikins@redhat.com)

* Wed Sep 19 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.1.1-1
- updates to stat-cert for cert v3 (jbowes@redhat.com)
- rct: Check for and handle files that aren't x509 certs (jbowes@redhat.com)
- rct: remove content set count from cat-cert. use stat-cert instead.
  (jbowes@redhat.com)
- implement aliases for cli commands (jbowes@redhat.com)
- rct: add a stat-cert command (jbowes@redhat.com)
- Switch certv2 related code to certv3 (jbowes@redhat.com)
- 852107: Make banner headings equal in length (bkearney@redhat.com)
- 842768: Remove --serverurl option from redeem command. (awood@redhat.com)
- Set correct parent for these error dialogs. (awood@redhat.com)
- set_parent_window() on RegisterScreen has been removed. (awood@redhat.com)
- make regex better (jesusr@redhat.com)
- 855762: Set correct parent for error dialog boxes raised by Autobind wizard.
  (awood@redhat.com)
- 856349: rct cat-cert now printing content for all content types
  (mstead@redhat.com)
- 842768: Limit --serverurl and --baseurl to specific commands.
  (awood@redhat.com)
- 854467: Use of activation keys requires an org. (awood@redhat.com)
  (dgoodwin@rm-rf.ca)
- 854879: Fixes for Anaconda desktop/workstation product cert installation.
  (dgoodwin@redhat.com)
- 840415: Handle copyfile errors gracefully. (awood@redhat.com)
- Adding new line b/w products when printed by rct (mstead@redhat.com)
- 850920: --servicelevel and --no-auto are mutually exclusive.
  (awood@redhat.com)
- Explicitly set GMT when doing entitlement date math (cduryee@redhat.com)
- adding --unset option to service-level and release cmds
  (dlackey@redhat.com.com)
- updated images for bz840599; changed rhsmcertd intervals, bz853571
  (dlackey@redhat.com.com)
- 853233: Do not allow 68.pem and 71.pem to coexist after migration.
  (awood@redhat.com)
- 852706: Fix server side certs not being deleted client side
  (alikins@redhat.com)
- editing manpages and gnome help per UXD feedback; updating manpages for new
  command arguments; bz852323, bz850881, bz854357 (dlackey@redhat.com.com)
  rf.ca)
- 845349: Support setting unknown values in the yum repo file
  (jbowes@redhat.com)
- Add a count of content sets to entitlement certificates (bkearney@redhat.com)
- 830988: Stacking is showing an odd parent in the My Subscriptions Tab
  (wpoteat@redhat.com)

* Fri Aug 31 2012 Alex Wood <awood@redhat.com> 1.0.17-1
- Fix gettext_lint issue with concat string in rhn-migrate (alikins@redhat.com)
- 851124: Fix GUI unsubscribe. (dgoodwin@redhat.com)
- fix po version for ta_IN.po (alikins@redhat.com)
- latest strings (alikins@redhat.com)

* Thu Aug 30 2012 Alex Wood <awood@redhat.com> 1.0.16-1
- 853187: Verbiage change in install-num-migrate-to-rhsm. (awood@redhat.com)
- 852894: Abort migration if multiple JBEAP channels are detected.
  (awood@redhat.com)
- 850715: Fix malloc for Config (jbowes@redhat.com)
- 852001: output the orgs key as part of the identity command.
  (bkearney@redhat.com)
- fix "make gettext", wrong var name for the find root (alikins@redhat.com)
- 850715: Fixes based on coverity scans (bkearney@redhat.com)
- 846316: Use the full name of Subscrition Manager during first boot
  (bkearney@redhat.com)
- 851346: Remove special case channel certs before subscribing.
  (awood@redhat.com)
- 847354: When printing, translate None type into an empty string
  (bkearney@redhat.com)

* Wed Aug 29 2012 Alex Wood <awood@redhat.com> 1.0.15-1
- Replace 16x16 icon with a new version that has no background
  (bkearney@redhat.com)
- 852107: Update verbiage in migration script. (awood@redhat.com)
- 847060: Push dependency higher up in the chain (bkearney@redhat.com)
- 848534: Change the about dialog icon to be a PNG to ensure accurate
  representation. (bkearney@redhat.com)
- 841396: Select first item in My Subscriptions table by default.
  (awood@redhat.com)
- 849483: Prompt user for org name if necessary. (awood@redhat.com)
- 849644: Calls made with --no-auto were not actually registering the system.
  (awood@redhat.com)
- 849494: Fix variable name collision. (awood@redhat.com)
- 846834: Use Subscription instead of entitlement certificate
  (bkearney@redhat.com)
- 847859: Expiration highlighting was being set incorrectly. (awood@redhat.com)
- 847750: Handle bad proxy values in migration script. (awood@redhat.com)
- 841961: Ignore case when specifying the service level in migration
  (bkearney@redhat.com)
- 842020: Remove an extraneous option group for rhsmcertd (bkearney@redhat.com)
- Refactored some of the shared CLI code in 'rct' (mstead@redhat.com)

* Fri Aug 17 2012 Alex Wood <awood@redhat.com> 1.0.14-1
- 849171: Remove an extraneous print statement (bkearney@redhat.com)
- 849105: Fixed a typo in the error message (bkearney@redhat.com)
- 772161: Notifiy virt who, if running, when the identity changes
  (bkearney@redhat.com)
- Reduce reads/parses of certificates (jbowes@redhat.com)
- remove unused function 'getInstalledProductHashMap' (jbowes@redhat.com)
- 843191: handle network errors better for 'version' command
  (alikins@redhat.com)
- 826739, 827553: Combine Service Level and Service Type and move up in display
  order. (awood@redhat.com)
- 847316: Remove the menu path for Subscription Manager from the manual
  registration screen. (bkearney@redhat.com)
- 848409,848195,848190,848184: Do not print the exception when attempting to do
  the server version check (bkearney@redhat.com)
- 847795: String and terminology clean up (bkearney@redhat.com)
- 847380: Update the verbiage to prefer the term Subscription Management
  (bkearney@redhat.com)
- 846834: Updated verbiage to focus on subsriptions and not on entitlements
  (bkearney@redhat.com)
- 846105: Verbiage changes to empasize subscriptions over entitlements
  (bkearney@redhat.com)
- 836933: Handle empty spaces for servce levels (bkearney@redhat.com)
- 836932,835050: Fix the service level lifecycle (bkearney@redhat.com)
- 836932: Reduce extra loggging when setting the service level
  (bkearney@redhat.com)
- About dialog was not working due to key errors from python
  (bkearney@redhat.com)
- 833319: Updated the help text for registration and service levels
  (bkearney@redhat.com)
- 847060: Add missing requires on pygobject2 (bkearney@redhat.com)
- 828954: Fix ta_IN.po file error with options (bkearney@redhat.com)
- 842898: re-implement string fix for it.po (bkearney@redhat.com)
- 828958: Fix the accidental translation of an option (bkearney@redhat.com)
- fix up make stylish (jbowes@redhat.com)
- No longer require root to run rct (mstead@redhat.com)
- Remove manually_subscribe.py, it's class moved to rhsm_login.py
  (alikins@redhat.com)
- Bumping the required python-rhsm version (mstead@redhat.com)
- Renamed rt command to rct. (mstead@redhat.com)
- Fix test case failure on 5.9 (Exception.message) (alikins@redhat.com)
- Refactor ManuallySubscribeScreen to use new Screen api (alikins@redhat.com)
- Check passed args as None to allow empty args (mstead@redhat.com)
- Exception.message is deprecated, just let _str_ do it (alikins@redhat.com)
- use MockStdout intead of nosetests sys.stdout.getvalue() (alikins@redhat.com)

* Thu Aug 09 2012 Alex Wood <awood@redhat.com> 1.0.13-1
- Fix "Project-Id-Version" for ta_IN.po (alikins@redhat.com)
- latest strings from zanata (alikins@redhat.com)
- Remove the 'repos' unittests until they are more mockable
  (alikins@redhat.com)
- Created CLI tool for viewing certificate data. (mstead@redhat.com)
- add versionlint to "make stylish" (alikins@redhat.com)
- add versionlint, requires pyqver (alikins@redhat.com)
- Remove unused mock return values (alikins@redhat.com)
- Remove enable_grid_lines from contract details glade file
  (alikins@redhat.com)
- more test cases for ConfigCommand (alikins@redhat.com)
- 837897: Terminology Change: Service Level Agreement -> Service Level
  (wpoteat@redhat.com)
- add test cases for ConfigCommand (alikins@redhat.com)
- Better error when rm'ing config item from missing section
  (alikins@redhat.com)
- unittest coverage for managercli.CLI (alikins@redhat.com)
- Adding unit tests for migration script regexes. (awood@redhat.com)
- 812903: Autosubscribe not working for newly added product cert after Register
  (wpoteat@redhat.com)
- 845827: Update command that do not require a candlepin connection
  (alikins@redhat.com)
- 845827: Split server version checkout out to avoid errors
  (alikins@redhat.com)
- Hack to address double mapping for 180.pem and 17{6|8}.pem (awood@redhat.com)
- fix pep8 (jesusr@redhat.com)
- don't show access.redhat.com url after registering to Katello
  (jesusr@redhat.com)
- remove the explicit url search from error handling. (jesusr@redhat.com)
- Make gettext_lint also check for _(foo) usage (alikins@redhat.com)
- Remove unneeded _(somevar) (alikins@redhat.com)
- Fix NameError in migration script. (awood@redhat.com)
- bogus newline in glade file (alikins@redhat.com)
- 826874: Reenable grid lines on newer gtk (alikins@redhat.com)
- 826874: Remove enable_grid_lines from treeviews in glade (alikins@redhat.com)
- 826874: Removing more properties that don't exist on gtk2.10
  (alikins@redhat.com)
- 826874: Change gtk target version to gtk 2.10 for all glade files
  (alikins@redhat.com)
- 826874: Clean of gtk properties not in gtk2.10 in our glade files
  (alikins@redhat.com)
- Add support for migrating to Katello. (jesusr@redhat.com)
- 843191: 'version' command showed wrong info with no network
  (alikins@redhat.com)
- 843915: Multiple-specifications of --enable and --disable repos
  (wpoteat@redhat.com)
- fix Package-Id-Version in ta_IN.po (alikins@redhat.com)
- Fix es_ES.po (missing newline) (alikins@redhat.com)
- 842898: fix missing --password in it.po (alikins@redhat.com)
- 843113: latest strings from zanata (alikins@redhat.com)
- 837280: Show users that we strip out any scheme given with a proxy.
  (awood@redhat.com)
- new strings (alikins@redhat.com)
- Refactor of SubDetailsWidget and GladeWidget (alikins@redhat.com)
- 826729: Move Cert Status up to top of Product's Subscription Details
  (wpoteat@redhat.com)

* Thu Aug 02 2012 Alex Wood <awood@redhat.com> 1.0.12-1
- remove test cases that use si_LK locale (alikins@redhat.com)
- 842845: Show better error if serverurl port is non numeric
  (alikins@redhat.com)
- 838113: 'unregister' was not cleaning up repos (alikins@redhat.com)
- 842170: replace None service level/type with "" not None (alikins@redhat.com)
- 844069: Allow register --force even if ID cert is totally invalid.
  (dgoodwin@redhat.com)
- 826874: Remove use of deprecated Gtk.Notebook.set_page (alikins@redhat.com)
- 818355: Terminology Change: Contract Number -> Contract (wpoteat@redhat.com)
- 844368: productid plugin was failing on ProductCert.product
  (alikins@redhat.com)
- Ignore warning about use of dbus.dbus_bindings (alikins@redhat.com)
- 844178: Fix error message when importing a non-entitlement cert bundle.
  (dgoodwin@redhat.com)
- remove deprecated use of DateRange.hasNow() (jbowes@redhat.com)
- remove use of DateRange.hasDate() (alikins@redhat.com)

* Wed Jul 25 2012 Alex Wood <awood@redhat.com> 1.0.11-1
- Remove deprecated use of hasDate. (dgoodwin@redhat.com)
- Fix missed use of renamed method. (dgoodwin@redhat.com)
- make stylish clean (alikins@redhat.com)
- use isoformat() here instead of strftime format string (alikins@redhat.com)
- create warn and expire colors once, fix test failure (alikins@redhat.com)
- make stylish cleanups (alikins@redhat.com)
- Additional tests for date logic. (awood@redhat.com)
- Update for some minor changes in python-rhsm. (dgoodwin@redhat.com)
- add rhsm_display module (alikins@redhat.com)
- Add module to set DISPLAY if RHSM_DISPLAY is set (alikins@redhat.com)
- 837132: fix typo (alikins@redhat.com)
- Add "ctrl-X" as accelerator for proxy config (alikins@redhat.com)
- Make "Usage" consistent across rhel5/6 (alikins@redhat.com)
- Add __str__ for our fake exception. (alikins@redhat.com)
- class ClassName(): is not legal syntax on python2.4 (alikins@redhat.com)
- Exception by default doesn't pass 'args' (alikins@redhat.com)
- Linkify() doesn't work on rhel5, so disble the tests there
  (alikins@redhat.com)
- hashlib doesn't exist on 2.4, md5 is deprecated on 2.6 (alikins@redhat.com)
- use simplejson since 'json' isnt part of python 2.4 (alikins@redhat.com)
- Use ISO8601 date format in allsubs tab (alikins@redhat.com)
- Fix syntax for RHEL5. (dgoodwin@redhat.com)
- Fix awkward stretching in Subscription column. (awood@redhat.com)
- 804144: Fix awkward stretching of Product column. (awood@redhat.com)
- 814731: Change the name of the menu item to Preferences from Settings, and
  change the accelerator keys (bkearney@redhat.com)
- 837132: Clean up the error message in the yum plugin (bkearney@redhat.com)
- 837038: Fix a grammatical error in the yum plugin (bkearney@redhat.com)
- Fix certificate parsing error reporting. (dgoodwin@redhat.com)
- Removing unnecessary assignments. (awood@redhat.com)
- F15 builds can't be submitted in Fedora anymore. (dgoodwin@redhat.com)
- updating options for rhn-migrate-classic-to-rhsm per bz840152; rewriting
  rhsmcertd for different options and usage examples (dlackey@redhat.com.com)
- Account/contract number field rename. (dgoodwin@redhat.com)
- Stylish fixes. (dgoodwin@redhat.com)
- Fix a certv2 error. (dgoodwin@redhat.com)
- 829825: Alter highlighting used in My Subscriptions tab (awood@redhat.com)
- 772040: Have no overlap filter properly handles subscription dates.
  (mstead@redhat.com)
- Update order support level/type to service. (dgoodwin@redhat.com)
- Remove explicit use of certificate2 module. (dgoodwin@redhat.com)
- Fix issues introduced in certv2 refactor. (dgoodwin@redhat.com)
- Change entitlement_version fact to certificate_version. (dgoodwin@redhat.com)
- Update to use new certificate2 module and classes. (dgoodwin@redhat.com)
- Send entitlement version fact. (dgoodwin@redhat.com)

* Thu Jul 19 2012 Alex Wood <awood@redhat.com> 1.0.10-1
- 828903: Pull in the latest translation for error messages with no options
  translated (bkearney@redhat.com)
- 841011: Fix double words in the korean translations (bkearney@redhat.com)
- 828958: Untranslate the word password when it it used as an option in the
  pt_BR translations (bkearney@redhat.com)
- Fixes for translations from zanata (alikins@redhat.com)
- Latest translations from zanata (alikins@redhat.com)
- 839887: Make error message text more clear when network is disconnected
  (bkearney@redhat.com)
- 839760: Fix the screen text for preferences based on UXD feedback
  (bkearney@redhat.com)
- 818355: Rename the use of 'Contract Number' to contract in the gui
  (bkearney@redhat.com)
- 840169: The service level was incorrectly being set after auto-subscription.
  (awood@redhat.com)
- 840637: Fixed missing reference to parent window. (mstead@redhat.com)
- Import and translate error strings for 'envirovment' cmd (alikins@redhat.com)
- Removed --wait arg, delay 2 min in rhsmcertd (mstead@redhat.com)
- Interval CLI args for rhsmcertd now specified as minutes. (mstead@redhat.com)
- Update rhsmcertd.init.d to use new CLI args (mstead@redhat.com)
- Bad url format test and a refactor of parse_url (alikins@redhat.com)
- Print message when rhsmcertd is shutting down (mstead@redhat.com)
- Fixed spelling and newline issues in rhsmcertd (mstead@redhat.com)
- Handle a few new bad url formats (http//foo or http:sdf) (alikins@redhat.com)
- Add wait and now args to rhsmcertd (mstead@redhat.com)
- 839683: Add some strings from older optparse to our i18n version
  (alikins@redhat.com)
- 838146: Subscription-manager cli does not allow unsubscribe when consumer not
  registered. (wpoteat@redhat.com)
- rhsmcertd: add format specifier checking to r_log (jbowes@redhat.com)
- Improve rhsmcertd logging (jbowes@redhat.com)
- Fix bug where filter options were not persisted when the dialog was reopened.
  (awood@redhat.com)
- 838242: proxy password from the cli wasn't getting used (alikins@redhat.com)
- Adding options parsing support (work-in-progress). (mstead@redhat.com)
- Added initial check delay to rhsmcertd (mstead@redhat.com)

* Tue Jul 10 2012 Alex Wood <awood@redhat.com> 1.0.9-1
- On invalid credentials in register, return to the login screen
  (jbowes@redhat.com)
- 821065: Make SLA/subscription asyncronous (jbowes@redhat.com)
- 838942: make gui and cli use the same releaseVer check (jbowes@redhat.com)
- fixes for translations from zanata (alikins@redhat.com)
- latest strings from zanata (alikins@redhat.com)
- Remove check for date parsing not failing when we expect it to
  (alikins@redhat.com)
- Remove glade orientation properties. (awood@redhat.com)
- Moving the filter counting mechanism into the Filters class.
  (awood@redhat.com)
- Adjust expand and fill properties for the filter dialog. (awood@redhat.com)
- add za_CN.utf to list of known busted locales (alikins@redhat.com)
- 824424: Fixing AttributeError thrown when accessing online help in RHEL 5.
  (awood@redhat.com)
- Add icon to update progress window. (awood@redhat.com)
- 806986: Display SKU for available and consumed subscriptions
  (jbowes@redhat.com)
- Increase the default size of the subscriptions viewport. (awood@redhat.com)
- Add no overlapping to the default filters. (awood@redhat.com)
- Tweaks to filter options dialog. (awood@redhat.com)
- 801187: print Provides: for all subs, even with no provides
  (jbowes@redhat.com)
- The filter dialog now updates results in real time. (awood@redhat.com)
- 837106: Add a11y property for register button (jbowes@redhat.com)
- 813336: Break filter options out into a separate dialog box.
  (awood@redhat.com)
- 837036: Do not refer to options as commands (bkearney@redhat.com)
- 829495: Delete a mis-translated string to force re-translation
  (bkearney@redhat.com)
- 828966: Delete a mis-translated string to force trasnlations
  (bkearney@redhat.com)
- 767133: Remove english to english translations from bn_IN to force a new
  translation (bkearney@redhat.com)
- 829491: Remove english trnaslations for italian translations
  (bkearney@redhat.com)

* Tue Jul 03 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.0.8-1
- Add rpmlint config for tmpfiles.d (jbowes@redhat.com)
- Use the i18n_optparse.OptionParser instead of optparse (alikins@redhat.com)
- Use our i18n_optparse for the migration scripts (alikins@redhat.com)
- Look for rhn-migrate* in bin for generating string catalogs
  (alikins@redhat.com)
- 826874: add gladelint support for 'orientation' prop (alikins@redhat.com)
- 826874: Remove unneeded property 'orientation' from glade
  (alikins@redhat.com)
- 796782: add systemd tmpfiles configuration (jbowes@redhat.com)

* Thu Jun 28 2012 Alex Wood <awood@redhat.com> 1.0.7-1
- Revamp choose server screen. (dgoodwin@redhat.com)

* Thu Jun 28 2012 Alex Wood <awood@redhat.com> 1.0.6-1
- rhsmcertd no longer exits when not registered. (mstead@redhat.com)
- po file cleanups (alikins@redhat.com)
- latest strings from zanata (alikins@redhat.com)
- Free config resources in one place (mstead@redhat.com)
- rhsmcertd: free GKeyFile when done (jbowes@redhat.com)
- rhsmcertd: remove studlyCaps (jbowes@redhat.com)
- "make stylish" should failed on "swapped" in glade files (alikins@redhat.com)
- Remove 'swapped=on' from glade signal markup. (alikins@redhat.com)
- add 'fix-glade-swapped' target to de-'swapped' glade files
  (alikins@redhat.com)
- make stylish fixups (alikins@redhat.com)
- Fix at-spi label for "offline_radio" widget (alikins@redhat.com)
- shorter messages for cases where registered to RHN Classic
  (alikins@redhat.com)
- Tighten up the gettext_lint regex (alikins@redhat.com)
- Fix string that was breaking xgettext (alikins@redhat.com)
- 810998: Add a button to test a proxy connection. (awood@redhat.com)
- new messages, and remove checking of rhn serverURL (alikins@redhat.com)
- remove unused es.po file (bkearney@redhat.com)
- 829486: Removed untranslated words to force a re-translation
  (bkearney@redhat.com)
- Remove unused bn.po file (bkearney@redhat.com)
- 826856: Add check for service-level command that --org can only be used with
  --list option (bkearney@redhat.com)
- 829483: Remove english to english translation to force a re-translations
  (bkearney@redhat.com)
- Remove unused de po file (bkearney@redhat.com)
- 819665: on 'version' display if we are registered to RHN Classic
  (alikins@redhat.com)

* Tue Jun 26 2012 Alex Wood <awood@redhat.com> 1.0.5-1
- 804109: Give a specific message when providing invalid credentials.
  (awood@redhat.com)
- 810360: update wording in gnome help file (cduryee@redhat.com)
- use new bin location of files for $STYLEFILES (alikins@redhat.com)
- add 'debuglint' for checking for leftover debugger imports
  (alikins@redhat.com)
- Update make clean target (jbowes@redhat.com)
- Move py executables to bin/ (jbowes@redhat.com)
- Put no results text inside the scrolled window (jbowes@redhat.com)
- 817901: Show text when there are no subscriptions to show.
  (dgoodwin@redhat.com)
- Move initd file to etc-conf (jbowes@redhat.com)
- Move plugins to their own src dir (jbowes@repl.ca)
- More test cases for utils.parse_url (alikins@redhat.com)
- 829482: Delete unstranslated strings in order force a retranslation
  (bkearney@redhat.com)
- 811602: Fix the help output based on UXD feedback (bkearney@redhat.com)
- 828867: Removed the extra %%s string from the te translation
  (bkearney@redhat.com)
- 829479: Remove unstranslated strings to force a re-translation
  (bkearney@redhat.com)
- Delete the unused pt.po file (bkearney@redhat.com)
- 829476: Remove untranslated strings. (bkearney@redhat.com)
- 811553: Improve the text for auto subscribe during registration
  (bkearney@redhat.com)
- 829471: Fix the translation for usage, and remove a translation for %%org id
  to force a retranslation (bkearney@redhat.com)
- Remove an outdated ta.po file (bkearney@redhat.com)
- 828810: Remove extra %%s in translation (bkearney@redhat.com)
- Test to ensure that pool id is in the output for list --available
  (wpoteat@redhat.com)
- Close registration window even if it failed. (dgoodwin@redhat.com)
- 825923: Subscription-manager service-level set should say "Service level set
  to:" (wpoteat@redhat.com)
- 811594: Default behavior for ReposCommand is --list (wpoteat@redhat.com)
- 832400: service-level --unset should display proper message for unregistered
  client. (wpoteat@redhat.com)

* Tue Jun 19 2012 Alex Wood <awood@redhat.com> 1.0.4-1
- 818978: Use systemd instead of sysv when installing on F17+ and RHEL7+.
  (mstead@redhat.com)
- 827035: update identity certificate (jmrodri@gmail.com)
- registergui: make screens without guis more generic (jbowes@redhat.com)
- Incorrect field value removed on previous change (wpoteat@redhat.com)
- 829812: Add an unset command for the release command (bkearney@redhat.com)
- 823659: Update SLA text in Settings to Service Level (wpoteat@redhat.com)
- Use a temp file for finding used widgets (jbowes@redhat.com)
- clean up some unused import warnings (jbowes@redhat.com)
- default to running style checks on tests (jbowes@redhat.com)
- Make test cases stylish as well... (alikins@redhat.com)
- Fix "make stylish" (alikins@redhat.com)
- 829803: Added an unset command to service level. (bkearney@redhat.com)
- Remove reference to InstalledProductsTab.product_id_text (alikins@redhat.com)
- Add a "find-missing-widgets" target to makefile (alikins@redhat.com)
- 830949: add accessibility locators for registration widgets
  (alikins@redhat.com)
- 824979: No message for subscription-manager release --list with no
  subscriptions. (wpoteat@redhat.com)
- Added UnRegisterCommand and UnSubscribeCommand nosetests (wpoteat@redhat.com)
- registergui: get firstboot working with new new code (jbowes@repl.ca)
- registergui: Create a PreformRegisterScreen class (jbowes@repl.ca)
- registergui: add a post method for setting data on the parent
  (jbowes@repl.ca)
- registergui: create a 'pre' hook for screens (jbowes@repl.ca)
  (cduryee@redhat.com)
- 819665: print msg if user is registered to RHN Classic on "identity" command
  (cduryee@redhat.com)
  (wpoteat@redhat.com)
- Add F17 yum repo release target. (dgoodwin@redhat.com)
- fix make stylish (jbowes@redhat.com)
- 810352: Disable the expansion of the system name selection in the register
  dialog (bkearney@redhat.com)
- 824530: add test case for setting proxy cli for release (alikins@redhat.com)
- rhsm-icon codestyle cleanups (jbowes@repl.ca)
- 829900: Use the term 'Subscription Management Service' to refer to SAM, CFSE,
  etc (root@bkearney.(none))
- 829898: Make the no service level option a bit clearer as to its meaning
  (bkearney@redhat.com)
- Improve the logging so that the user only sees the approved output by default
  (bkearney@redhat.com)
- 830193: Modify the output of the yum plugin to be consistent with RHN
  (bkearney@redhat.com)
- 824530: "release" command ignoring cli proxy options (alikins@redhat.com)
- 828042,828068: Make ja_JP's Confirm Subscription unique for firstboot.
  (mstead@redhat.com)
- Updating strings from zanata (mstead@redhat.com)
- 825309: Remove the archiecture field from the table. (bkearney@redhat.com)
- 823608: Rename the software pane to product (bkearney@redhat.com)
- 810369: Prefer the term Subscription to Entitlement (bkearney@redhat.com)
- Add a warning comment about firstboot module titles (alikins@redhat.com)
- Clean up an option (bkearney@redhat.com)
- 827208: Fix the xmltag bugs in the or po file (bkearney@redhat.com)
- 827214: Clean up the XML tags in ta po file. (bkearney@redhat.com)
- Slight change in the path for the ta po file (bkearney@redhat.com)
- Slight change in the path for the ta po file (bkearney@redhat.com)
- Slight change in the path for the ml po file (bkearney@redhat.com)
- 828583: Add some spacing at the end of the file paths in the ko.po file
  (bkearney@redhat.com)
- 828816: the %%prog variable should not be translated (bkearney@redhat.com)
- 828821: Fix the addition of a new variable in the hi po file
  (bkearney@redhat.com)
- 828903: Fix translation of options in the bn po file. (bkearney@redhat.com)
- Fix part of the mis translated options (bkearney@redhat.com)
- 828965: Fix a translated option which should not have been translated
  (bkearney@redhat.com)
- 828954: fix the --pool option in the translated string (bkearney@redhat.com)
- 828958: --available should not be translated (bkearney@redhat.com)
- Add --password as an option, not a string. This cause several strings to be
  retranslated (bkearney@redhat.com)
- 828969: Fix the options in the translated string (bkearney@redhat.com)
- 828985: Fix the url in the translated string (bkearney@redhat.com)
- 828989: Fix the access url (bkearney@redhat.com)
- 818205: Release --set command should only accept values from --list.
  (awood@redhat.com)
- registergui: extract out a screen superclass (jbowes@repl.ca)
- registergui: get button label from screen class (jbowes@repl.ca)
- registergui: keep screens in a list (jbowes@repl.ca)
- registergui: pull out environment screen into its own class (jbowes@repl.ca)
- registergui: sensitivity refactor and method move (jbowes@repl.ca)
- registergui: extract out credentials_entered method (jbowes@repl.ca)
- registergui: move organization screen to its own class (jbowes@repl.ca)
- registergui: move credentials screen to its own class (jbowes@repl.ca)
- registergui: move choose server screen to its own class (jbowes@repl.ca)
- registergui: switch from GladeWrapper to GladeWidget (jbowes@repl.ca)
- registergui: Remove some unused globals (jbowes@repl.ca)

* Thu Jun 07 2012 Alex Wood <awood@redhat.com> 1.0.3-1
- 817938: Add sorting to the contract selection table. (awood@redhat.com)
- 822706: gtk widget visibility toggle compat for el5 (jbowes@repl.ca)
- 822706: Display Register button on Installed Product tab if not registered.
  (mstead@redhat.com)
- 825286: Handle unset service levels in a manner similar to unset release
  versions. (awood@redhat.com)
- 826735: Merge start/end date sub details into one row. (dgoodwin@redhat.com)
- fix make stylish (jbowes@repl.ca)
- 811593: Feedback when not providing command options is not consistent.
  (wpoteat@redhat.com)
- 806986: Subscription-Manager should refer to subscription name and product
  name. (wpoteat@redhat.com)
- 825737: Service-level --set should configure proper value for GUI
  (wpoteat@redhat.com)
- 817901: Disable the match installed products filter. (dgoodwin@redhat.com)
- Remove unecessary use of lambda. (dgoodwin@redhat.com)
- 818282: Sort virtual subscriptions to the top of contract selector.
  (dgoodwin@redhat.com)
- 818383: display better messages for yum plugin usage (cduryee@redhat.com)
- Fix logging of deleted expired certs (jbowes@repl.ca)
- Remove the constants module (jbowes@repl.ca)
- Remove useless format specifier (jbowes@repl.ca)
- 801187: condense list --consumed output (jbowes@repl.ca)
- Don't use kwargs for cli subclasses; it makes things shorter (jbowes@repl.ca)
- Remove desc cli argument, no module used it (jbowes@repl.ca)
- Use super for cli module init (jbowes@repl.ca)
- Clean up rpmlint messages (jbowes@repl.ca)
- Autogenerate the cli usage message (jbowes@repl.ca)
- Remove obsolete nose tests (jbowes@repl.ca)
- 812410: Show product name on CLI subscribe to pool. (dgoodwin@redhat.com)
- 824680: make init script status return proper exit code (alikins@redhat.com)
- fix nosetests for progress gui (jbowes@repl.ca)
- Rework urlparse calls to work with RHEL 5. (awood@redhat.com)
- 818238: Set a better progress title for sub search (jbowes@repl.ca)
- 771756: Drop "rhsm icon" from the rhsm-icon usage message (jbowes@repl.ca)
- 820294: Let candlepin handle org/env/key validation (jbowes@repl.ca)
- 818397: Rename subscription-manager-gnome to -gui (jbowes@repl.ca)
- Reduce wordiness of version command. (awood@redhat.com)
- 824333: use rhel5-friendly urlparse options (cduryee@redhat.com)
- Log the program versions when starting the GUI or making a CLI call.
  (awood@redhat.com)
- Fix the About dialog to work in RHEL 5.8 (awood@redhat.com)
- 821544: Remove the stacking id attribute from my susbcriptions since it is
  not being used currently. (bkearney@redhat.com)
- add checkcommits exception for 824100 (alikins@redhat.com)
- 824100: update zanata.xml to grab latest pt_BR.po (alikins@redhat.com)
- 822057: do not hard-code cdn to port 443 (cduryee@redhat.com)
- Display sane error on CLI if missing CA certificate. (dgoodwin@redhat.com)
- Display sane error in GUI if missing CA certificate. (dgoodwin@redhat.com)
- 812373: Terminology change for list --installed and --consumed
  (wpoteat@redhat.com)
- zanata client will push any po/*.pot files it finds. Stop.
  (alikins@redhat.com)
- 789182: Fix UnicodeEncodeError when logging. (awood@redhat.com)
- README for github and people who like to read (alikins@redhat.com)
- checkcommits exception for xgettext patch fixed in master
  (alikins@redhat.com)
- 820743: Fix these strings so xgettext finds extracts them
  (alikins@redhat.com)
- refine the regex for "make gettext_lint" (alikins@redhat.com)
- Upload el6 yum packages to another dir for compatability.
  (dgoodwin@redhat.com)

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
