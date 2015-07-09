# For optional building of ostree-plugin sub package. Unrelated to systemd
# but the same versions apply at the moment.
%global rhsm_plugins_dir  /usr/share/rhsm-plugins
%global _hardened_build 1
%{!?__global_ldflags: %global __global_ldflags -Wl,-z,relro -Wl,-z,now}

%define install_ostree INSTALL_OSTREE_PLUGIN=true

# makefile will guess, but be specific.
%define gtk_version GTK_VERSION=3

%define post_boot_tool INSTALL_INITIAL_SETUP=true INSTALL_FIRSTBOOT=false

Name: subscription-manager
Version: 1.15.6
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
Requires:  python-rhsm >= 1.15.0
Requires:  dbus-python
Requires:  yum >= 3.2.19-15
Requires:  usermode
Requires:  python-dateutil
Requires: gobject-introspection
Requires: pygobject3-base

# There's no dmi to read on these arches, so don't pull in this dep.
%ifnarch ppc ppc64 s390 s390x
Requires:  python-dmidecode
%endif

Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

BuildRequires: python-devel
BuildRequires: gettext
BuildRequires: intltool
BuildRequires: libnotify-devel
BuildRequires: desktop-file-utils
BuildRequires: redhat-lsb
BuildRequires: scrollkeeper
BuildRequires: GConf2-devel
BuildRequires: gtk3-devel
# We need the systemd RPM macros
BuildRequires: systemd


%description
The Subscription Manager package provides programs and libraries to allow users
to manage subscriptions and yum repositories from the Red Hat entitlement
platform.

%package -n subscription-manager-plugin-ostree
Summary: A plugin for handling OSTree content.
Group: System Environment/Base

Requires: pygobject3-base
# plugin needs a slightly newer version of python-iniparse for 'tidy'
Requires:  python-iniparse >= 0.4

%description -n subscription-manager-plugin-ostree
Enables handling of content of type 'ostree' in any certificates
from the server. Populates /ostree/repo/config as well as updates
the remote in the currently deployed .origin file.

# container/docker package
%package -n subscription-manager-plugin-container
Summary: A plugin for handling container content.
Group: System Environment/Base

%description -n subscription-manager-plugin-container
Enables handling of content of type 'containerImage' in any certificates
from the server. Populates /etc/docker/certs.d appropriately.

%package -n subscription-manager-gui
Summary: A GUI interface to manage Red Hat product subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}

Requires: pygobject3
Requires: gtk3
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

%package -n subscription-manager-firstboot
Summary: Firstboot screens for subscription manager
Group: System Environment/Base
Requires: %{name}-gui = %{version}-%{release}

# Fedora can figure this out automatically, but RHEL cannot:
Requires: librsvg2

%description -n subscription-manager-firstboot
This package contains the firstboot screens for subscription-manager.

%package -n subscription-manager-initial-setup-addon
Summary: initial-setup screens for subscription-manager
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}
Requires: initial-setup
Obsoletes: subscription-manager-firstboot < 1.15.3-1

%description -n subscription-manager-initial-setup-addon
This package contains the initial-setup screens for subscription-manager.

%package -n subscription-manager-migration
Summary: Migration scripts for moving to certificate based subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}
Requires: rhnlib
Requires: subscription-manager-migration-data

%description -n subscription-manager-migration
This package contains scripts that aid in moving to certificate based
subscriptions

%prep
%setup -q

%build
make -f Makefile \
    VERSION=%{version}-%{release} \
    CFLAGS="%{optflags}" \
    LDFLAGS="%{__global_ldflags}" \
    OS_DIST="%{dist}" \
    %{?gtk_version}

%install
rm -rf %{buildroot}
make -f Makefile install \
    VERSION=%{version}-%{release} \
    PREFIX=%{buildroot} \
    MANPATH=%{_mandir} \
    OS_VERSION=%{?fedora}%{?rhel} \
    OS_DIST=%{dist} \
    %{?gtk_version} \
    %{?install_ostree} \
    %{?post_boot_tool}

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
%{_unitdir}/rhsmcertd.service
%{_tmpfilesdir}/%{name}.conf

# our config dirs and files
%attr(755,root,root) %dir %{_sysconfdir}/rhsm
%attr(644,root,root) %config(noreplace) %{_sysconfdir}/rhsm/rhsm.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/rhsm/logging.conf

%attr(755,root,root) %dir %{_sysconfdir}/rhsm/facts

%attr(755,root,root) %dir %{_sysconfdir}/pki/consumer
%attr(755,root,root) %dir %{_sysconfdir}/pki/entitlement

%config(noreplace) %{_sysconfdir}/dbus-1/system.d/com.redhat.SubscriptionManager.conf

# PAM config
%{_sysconfdir}/pam.d/subscription-manager
%{_sysconfdir}/security/console.apps/subscription-manager

# remove the repo file when we are deleted
%ghost %{_sysconfdir}/yum.repos.d/redhat.repo

# yum plugin config
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/*.conf

# misc system config
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/logrotate.d/subscription-manager
%attr(700,root,root) %{_sysconfdir}/cron.daily/rhsmd
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
%dir %{_datadir}/rhsm
%dir %{_datadir}/rhsm/subscription_manager
%dir %{_datadir}/rhsm/subscription_manager/branding
%dir %{_datadir}/rhsm/subscription_manager/model
%dir %{_datadir}/rhsm/subscription_manager/plugin

# code, python modules and packages
%{_datadir}/rhsm/subscription_manager/*.py*

%{_datadir}/rhsm/subscription_manager/branding/*.py*
%{_datadir}/rhsm/subscription_manager/model/*.py*
%{_datadir}/rhsm/subscription_manager/plugin/*.py*

# our gtk2/gtk3 compat modules
%dir %{_datadir}/rhsm/subscription_manager/ga_impls
%{_datadir}/rhsm/subscription_manager/ga_impls/__init__.py*
%{_datadir}/rhsm/subscription_manager/ga_impls/ga_gtk3.py*

# subscription-manager plugins
%dir %{rhsm_plugins_dir}
%dir %{_sysconfdir}/rhsm/pluginconf.d

# yum plugins
# Using _prefix + lib here instead of libdir as that evaluates to /usr/lib64 on x86_64,
# but yum plugins seem to normally be sent to /usr/lib/:
%{_prefix}/lib/yum-plugins/*.py*

# Incude rt CLI tool
%dir %{_datadir}/rhsm/rct
%{_datadir}/rhsm/rct/__init__.py*
%{_datadir}/rhsm/rct/cli.py*
%{_datadir}/rhsm/rct/*commands.py*
%{_datadir}/rhsm/rct/printing.py*
%{_datadir}/rhsm/rct/version.py*
%attr(755,root,root) %{_bindir}/rct

# Include consumer debug CLI tool
%dir %{_datadir}/rhsm/rhsm_debug
%{_datadir}/rhsm/rhsm_debug/__init__.py*
%{_datadir}/rhsm/rhsm_debug/cli.py*
%{_datadir}/rhsm/rhsm_debug/*commands.py*
%attr(755,root,root) %{_bindir}/rhsm-debug

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
%dir %{_datadir}/rhsm/subscription_manager/gui
%dir %{_datadir}/rhsm/subscription_manager/gui/data
%dir %{_datadir}/rhsm/subscription_manager/gui/data/ui
%dir %{_datadir}/rhsm/subscription_manager/gui/data/glade
%dir %{_datadir}/rhsm/subscription_manager/gui/data/icons
%{_datadir}/rhsm/subscription_manager/gui/data/ui/*.ui
%{_datadir}/rhsm/subscription_manager/gui/data/glade/*.glade
%{_datadir}/rhsm/subscription_manager/gui/data/icons/*.svg
%{_datadir}/applications/subscription-manager-gui.desktop
%{_datadir}/icons/hicolor/*/apps/*.png
%{_datadir}/icons/hicolor/*/apps/*.svg
%{_datadir}/appdata/subscription-manager-gui.appdata.xml

# code and modules
%{_datadir}/rhsm/subscription_manager/gui/*.py*

# gui system config files
%{_sysconfdir}/xdg/autostart/rhsm-icon.desktop
%{_sysconfdir}/pam.d/subscription-manager-gui
%{_sysconfdir}/security/console.apps/subscription-manager-gui
%{_sysconfdir}/bash_completion.d/subscription-manager-gui

%doc
%{_mandir}/man8/subscription-manager-gui.8*
%{_mandir}/man8/rhsm-icon.8*
%doc LICENSE


%files -n subscription-manager-plugin-ostree
%defattr(-,root,root,-)
%{_sysconfdir}/rhsm/pluginconf.d/ostree_content.OstreeContentPlugin.conf
%{rhsm_plugins_dir}/ostree_content.py*
%{_datadir}/rhsm/subscription_manager/plugin/ostree/*.py*


%files -n subscription-manager-plugin-container
%defattr(-,root,root,-)
%{_sysconfdir}/rhsm/pluginconf.d/container_content.ContainerContentPlugin.conf
%{rhsm_plugins_dir}/container_content.py*
%{_datadir}/rhsm/subscription_manager/plugin/container.py*
# Copying Red Hat CA cert into each directory:
%attr(755,root,root) %dir %{_sysconfdir}/docker/certs.d/cdn.redhat.com
%attr(644,root,root) %{_sysconfdir}/rhsm/ca/redhat-entitlement-authority.pem
%attr(644,root,root) %{_sysconfdir}/docker/certs.d/cdn.redhat.com/redhat-entitlement-authority.crt


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


%files -n subscription-manager-migration
%defattr(-,root,root,-)
%dir %{_datadir}/rhsm/subscription_manager/migrate
%{_datadir}/rhsm/subscription_manager/migrate/*.py*
%attr(755,root,root) %{_sbindir}/rhn-migrate-classic-to-rhsm

%doc
%{_mandir}/man8/rhn-migrate-classic-to-rhsm.8*
%doc LICENSE

%post
%systemd_post rhsmcertd.service

if [ -x /bin/dbus-send ] ; then
  dbus-send --system --type=method_call --dest=org.freedesktop.DBus / org.freedesktop.DBus.ReloadConfig > /dev/null 2>&1 || :
fi


%preun
if [ $1 -eq 0 ] ; then
    %systemd_preun rhsmcertd.service
    if [ -x /bin/dbus-send ] ; then
        dbus-send --system --type=method_call --dest=org.freedesktop.DBus / org.freedesktop.DBus.ReloadConfig > /dev/null 2>&1 || :
    fi
fi

%postun
%systemd_postun_with_restart rhsmcertd.service

%changelog
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
- Add support for content plugins
- Add ostree content plugin
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
- refactor certlib and friends (alikins@redhat.com)

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

