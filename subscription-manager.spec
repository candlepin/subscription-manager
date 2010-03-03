Name: subscription-manager      
Version: 0.7
Release: 1
Summary: Supported tools and libraries for subscription and repo Management       
Group:   System Environment/Base         
License: GPL       
Source0: %{name}-%{version}.tar.gz       
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: %{_arch}
Requires: python-dmidecode
Requires:  python-ethtool 
Requires:  python-simplejson
Requires:  m2crypto 
Requires: yum >= 3.2.19-15
Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
#Requires: pygtk2 pygtk2-libglade gnome-python2 gnome-python2-canvas
#Requires: usermode-gtk

%description
Subscription Manager package provides programs and libraries to allow users to manager subscriptions and repos from a unified entitlement or a deployment Platform.

%prep
%setup -q

%build
mkdir bin
cc src/rhsmcertd.c -o bin/rhsmcertd

%install
# TODO: Need clean/Makefile
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/share/rhsm
mkdir -p $RPM_BUILD_ROOT/usr/lib/yum-plugins/
mkdir -p $RPM_BUILD_ROOT/usr/sbin
mkdir -p $RPM_BUILD_ROOT/etc/rhsm
mkdir -p $RPM_BUILD_ROOT/etc/yum/pluginconf.d/
mkdir -p $RPM_BUILD_ROOT/%{_mandir}/man8/
mkdir -p $RPM_BUILD_ROOT/var/log/rhsm 
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/init.d
cp -R src/*.py $RPM_BUILD_ROOT/usr/share/rhsm
cp -R src/plugin/*.py $RPM_BUILD_ROOT/usr/lib/yum-plugins/
cp src/subscription-manager-cli $RPM_BUILD_ROOT/usr/sbin
cp etc-conf/rhsm.conf $RPM_BUILD_ROOT/etc/rhsm/
cp etc-conf/rhsmplugin.conf $RPM_BUILD_ROOT/etc/yum/pluginconf.d/
cp bin/* $RPM_BUILD_ROOT/%{_bindir}
cp src/rhsmcertd.init.d $RPM_BUILD_ROOT/%{_sysconfdir}/init.d/rhsmcertd
#cp man/* $RPM_BUILD_ROOT/%{_mandir}/man8/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)

# dirs
%dir /usr/share/rhsm

#files
/usr/share/rhsm/__init__.py*
/usr/share/rhsm/connection.py*
/usr/share/rhsm/managercli.py*
/usr/share/rhsm/managerlib.py*
/usr/share/rhsm/repolib.py*
/usr/lib/yum-plugins/rhsmplugin.py*
/usr/share/rhsm/certificate.py*
/usr/share/rhsm/certlib.py*
/usr/share/rhsm/hwprobe.py*
/usr/share/rhsm/config.py*
/usr/share/rhsm/logutil.py*
/usr/share/rhsm/OptionsCli.py*
/usr/share/rhsm/managergui.py*
/usr/share/rhsm/messageWindow.py*
#/usr/share/rhsm/rhsmcertd.*
%attr(755,root,root) %{_sbindir}/subscription-manager-cli
%attr(700,root,root) %dir %{_var}/log/rhsm
%attr(755,root,root) %{_bindir}/rhsmcertd
%attr(755,root,root) %{_sysconfdir}/init.d/rhsmcertd

# config files
%attr(644,root,root) /etc/rhsm/rhsm.conf
%attr(644,root,root) /etc/yum/pluginconf.d/rhsmplugin.conf

%post
chkconfig --add rhsmcertd
/sbin/service rhsmcertd start

%preun
if [ $1 = 0 ] ; then
   /sbin/service rhsmcertd stop >/dev/null 2>&1
   /sbin/chkconfig --del rhsmcertd
fi

%changelog
* Tue Mar 02 2010 Jeff Ortel <jortel@redhat.com>
* fixing busted preun

* Tue Mar 02 2010 Jeff Ortel <jortel@redhat.com> 0.6-2
- add changes to build and install rhsmcertd

* Tue Mar 02 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.7-1
- bug#568433 - Flushed out hardware info

* Mon Mar 01 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.5-1
- new build

* Thu Feb 25 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-4
- new build

* Tue Feb 23 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-2
- more changes to probe dmidecode to get hardware info

* Mon Feb 22 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-1
- packaging subscription-manager

