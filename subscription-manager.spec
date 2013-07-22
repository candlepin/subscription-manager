# Prefer systemd over sysv on Fedora 17+ and RHEL 7+
%define use_systemd (0%{?fedora} && 0%{?fedora} >= 17) || (0%{?rhel} && 0%{?rhel} >= 7)
%define use_dateutil (0%{?fedora} && 0%{?fedora} >= 17) || (0%{?rhel} && 0%{?rhel} >= 6)


%define rhsm_plugins_dir   /usr/share/rhsm-plugins

# A couple files are for RHEL 5 only:
%if 0%{?rhel} == 5
%define el5 1
%endif

Name: subscription-manager
Version: 1.8.13
Release: 1%{?dist}
Summary: Tools and libraries for subscription and repository management
Group:   System Environment/Base
License: GPLv2

# How to create the source tarball:
#
# git clone git://git.fedorahosted.org/git/subscription-manager.git/
# yum install tito
# tito build --tag subscription-manager-$VERSION-$RELEASE --tgz
Source0: %{name}-%{version}.tar.gz
URL:     https://fedorahosted.org/subscription-manager/
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:  python-ethtool
Requires:  python-simplejson
Requires:  python-iniparse
Requires:  pygobject2
Requires:  virt-what
Requires:  python-rhsm >= 1.8.14-1
Requires:  dbus-python
Requires:  yum >= 3.2.19-15
Requires:  usermode
# dateutil is better than our version
# built using PyXML utils, but PyXML is
# deprecated for f17+, and dateutil doesn't
# exist on rhel5
%if %use_dateutil
# we are building for fedora >= 12 or rhel >= 6
Requires: python-dateutil
%else
Requires: PyXML
%endif


%{?el5:Requires: rhn-setup-gnome}
# There's no dmi to read on these arches, so don't pull in this dep.
%ifnarch ppc ppc64 s390 s390x
Requires:  python-dmidecode
%endif

Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts

%if %use_systemd
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
%endif

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
Requires: usermode-gtk
Requires: dbus-x11
Requires(post): scrollkeeper
Requires(postun): scrollkeeper

# Renamed from -gnome, so obsolete it properly
Obsoletes: %{name}-gnome < 1.0.3-1
Provides: %{name}-gnome = %{version}-%{release}

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
Requires: rhn-setup-gnome

# Fedora can figure this out automatically, but RHEL cannot:
Requires: librsvg2


%description -n subscription-manager-firstboot
This package contains the firstboot screens for subscription manager.

%package -n subscription-manager-migration
Summary: Migration scripts for moving to certificate based subscriptions
Group: System Environment/Base
Requires: %{name} = %{version}-%{release}
Requires: rhnlib

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

desktop-file-validate \
        %{buildroot}/etc/xdg/autostart/rhsm-icon.desktop

desktop-file-validate \
        %{buildroot}/usr/share/applications/subscription-manager-gui.desktop
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
%{_sysconfdir}/bash_completion.d/rct
%{_sysconfdir}/bash_completion.d/rhn-migrate-classic-to-rhsm
%{_sysconfdir}/bash_completion.d/rhsm-icon
%{_sysconfdir}/bash_completion.d/rhsmcertd

%{_sysconfdir}/cron.daily/rhsmd
%{_datadir}/dbus-1/system-services/com.redhat.SubscriptionManager.service

%dir %{_datadir}/rhsm
%dir %{_datadir}/rhsm/subscription_manager

%{_datadir}/rhsm/subscription_manager/async.py*
%{_datadir}/rhsm/subscription_manager/base_plugin.py*
%{_datadir}/rhsm/subscription_manager/branding
%{_datadir}/rhsm/subscription_manager/cache.py*
%{_datadir}/rhsm/subscription_manager/certdirectory.py*
%{_datadir}/rhsm/subscription_manager/certlib.py*
%{_datadir}/rhsm/subscription_manager/certmgr.py*
%{_datadir}/rhsm/subscription_manager/cert_sorter.py*
%{_datadir}/rhsm/subscription_manager/cli.py*
%{_datadir}/rhsm/subscription_manager/dbus_interface.py*
%{_datadir}/rhsm/subscription_manager/factlib.py*
%{_datadir}/rhsm/subscription_manager/facts.py*
%{_datadir}/rhsm/subscription_manager/hwprobe.py*
%{_datadir}/rhsm/subscription_manager/isodate.py*
%{_datadir}/rhsm/subscription_manager/i18n_optparse.py*
%{_datadir}/rhsm/subscription_manager/i18n.py*
%{_datadir}/rhsm/subscription_manager/identity.py*
%{_datadir}/rhsm/subscription_manager/injection.py*
%{_datadir}/rhsm/subscription_manager/injectioninit.py*
%{_datadir}/rhsm/subscription_manager/__init__.py*
%{_datadir}/rhsm/subscription_manager/jsonwrapper.py*
%{_datadir}/rhsm/subscription_manager/listing.py*
%{_datadir}/rhsm/subscription_manager/lock.py*
%{_datadir}/rhsm/subscription_manager/logutil.py*
%{_datadir}/rhsm/subscription_manager/managercli.py*
%{_datadir}/rhsm/subscription_manager/managerlib.py*
%{_datadir}/rhsm/subscription_manager/plugins.py*
%{_datadir}/rhsm/subscription_manager/productid.py*
%{_datadir}/rhsm/subscription_manager/release.py*
%{_datadir}/rhsm/subscription_manager/repolib.py*
%{_datadir}/rhsm/subscription_manager/utils.py*
%{_datadir}/rhsm/subscription_manager/validity.py*
%{_datadir}/rhsm/subscription_manager/reasons.py*
%{_datadir}/rhsm/subscription_manager/cp_provider.py*
%{_datadir}/rhsm/subscription_manager/file_monitor.py*

# subscription-manager plugins
%dir %{rhsm_plugins_dir}
%dir %{_sysconfdir}/rhsm/pluginconf.d
# add default plugins here when we have some

# yum plugins
# Using _prefix + lib here instead of libdir as that evaluates to /usr/lib64 on x86_64,
# but yum plugins seem to normally be sent to /usr/lib/:
%{_prefix}/lib/yum-plugins/subscription-manager.py*
%{_prefix}/lib/yum-plugins/product-id.py*


%attr(755,root,root) %{_sbindir}/subscription-manager
%attr(755,root,root) %{_bindir}/subscription-manager
%attr(755,root,root) %{_bindir}/rhsmcertd
%attr(755,root,root) %{_libexecdir}/rhsmcertd-worker
%attr(755,root,root) %{_libexecdir}/rhsmd
%attr(755,root,root) %dir %{_var}/run/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm
%attr(755,root,root) %dir %{_var}/lib/rhsm/facts
%attr(755,root,root) %dir %{_var}/lib/rhsm/packages
%attr(755,root,root) %dir %{_var}/lib/rhsm/cache
%{_sysconfdir}/pam.d/subscription-manager
%{_sysconfdir}/security/console.apps/subscription-manager

%if %use_systemd
    %attr(644,root,root) %{_unitdir}/rhsmcertd.service
    %attr(644,root,root) %{_prefix}/lib/tmpfiles.d/%{name}.conf
%else
    %attr(755,root,root) %{_initrddir}/rhsmcertd
%endif

# Incude rt CLI tool
%dir %{_datadir}/rhsm/rct
%{_datadir}/rhsm/rct/__init__.py*
%{_datadir}/rhsm/rct/cli.py*
%{_datadir}/rhsm/rct/*commands.py*
%{_datadir}/rhsm/rct/printing.py*
%attr(755,root,root) %{_bindir}/rct

%doc
%{_mandir}/man8/subscription-manager.8*
%{_mandir}/man8/rhsmcertd.8*
%{_mandir}/man8/rct.8*
%doc LICENSE


%files -n subscription-manager-gui
%defattr(-,root,root,-)
%dir %{_datadir}/rhsm/subscription_manager/gui
%dir %{_datadir}/rhsm/subscription_manager/gui/data
%dir %{_datadir}/rhsm/subscription_manager/gui/data/icons
%{_datadir}/rhsm/subscription_manager/gui/*
%{_datadir}/rhsm/subscription_manager/gui/data/icons/*.svg
%{_datadir}/applications/subscription-manager-gui.desktop
%{_datadir}/icons/hicolor/16x16/apps/*.png
%{_datadir}/icons/hicolor/22x22/apps/*.png
%{_datadir}/icons/hicolor/24x24/apps/*.png
%{_datadir}/icons/hicolor/32x32/apps/*.png
%{_datadir}/icons/hicolor/48x48/apps/*.png
%{_datadir}/icons/hicolor/scalable/apps/*.svg
%attr(755,root,root) %{_sbindir}/subscription-manager-gui
%attr(755,root,root) %{_bindir}/subscription-manager-gui

%{_bindir}/rhsm-icon
%{_sysconfdir}/xdg/autostart/rhsm-icon.desktop

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

%if 0%{?rhel} < 6
  %if 0%{?fedora} <= 12
    # we are building for fedora <= 12 or rhel < 6
    %{_prefix}/share/firstboot/modules/rhsm_login.py*
  %endif
%endif

%files -n subscription-manager-migration
%defattr(-,root,root,-)
%dir %{_datadir}/rhsm/subscription_manager/migrate
%{_datadir}/rhsm/subscription_manager/migrate/__init__.py*
%{_datadir}/rhsm/subscription_manager/migrate/migrate.py*
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
        /bin/systemctl --no-reload disable rhsmcertd.service > /dev/null 2>&1 || :
        /bin/systemctl stop rhsmcertd.service > /dev/null 2>&1 || :
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
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
    if [ $1 -eq 1 ] ; then
        /bin/systemctl try-restart rhsmcertd.service >/dev/null 2>&1 || :
    fi
%endif

%changelog
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
