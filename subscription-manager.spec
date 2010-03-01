Name: subscription-manager      
Version: 0.4
Release: 1
Summary: Supported tools and libraries for subscription and repo Management       

Group:   System Environment/Base         
License: GPL       
Source0: %{name}-%{version}.tar.gz       
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
Requires: python-dmidecode
Requires:  python-ethtool 
Requires:  python-simplejson
Requires:  m2crypto 
Requires: yum >= 3.2.19-15
#Requires: pygtk2 pygtk2-libglade gnome-python2 gnome-python2-canvas
#Requires: usermode-gtk

%description
Subscription Manager package provides programs and libraries to allow users to manager subscriptions and repos from a unified entitlement or a deployment Platform.

%prep
%setup -q

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
cp -R src/*.py $RPM_BUILD_ROOT/usr/share/rhsm
cp -R src/plugin/*.py $RPM_BUILD_ROOT/usr/lib/yum-plugins/
cp src/subscription-manager-cli $RPM_BUILD_ROOT/usr/sbin
cp etc-conf/rhsm.conf $RPM_BUILD_ROOT/etc/rhsm/
cp etc-conf/rhsmplugin.conf $RPM_BUILD_ROOT/etc/yum/pluginconf.d/
#cp man/* $RPM_BUILD_ROOT/%{_mandir}/man8/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)

# dirs
%dir /usr/share/rhsm

#files
/usr/share/rhsm/__init__.*
/usr/share/rhsm/connection.*
/usr/share/rhsm/managercli.*
/usr/share/rhsm/repolib.*
/usr/lib/yum-plugins/rhsmplugin.*
/usr/share/rhsm/certificate.*
/usr/share/rhsm/certlib.*
/usr/share/rhsm/hwprobe.*
/usr/share/rhsm/config.*
/usr/share/rhsm/logutil.*
#/usr/share/rhsm/rhsmcertd.*
%attr(755,root,root) %{_sbindir}/subscription-manager-cli
%attr(700,root,root) %dir %{_var}/log/rhsm

# config files
%attr(644,root,root) /etc/rhsm/rhsm.conf
%attr(644,root,root) /etc/yum/pluginconf.d/rhsmplugin.conf

%doc

%changelog
* Mon Mar 01 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.4-1
- new build

* Thu Feb 25 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-4
- new build

* Tue Feb 23 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-2
- more changes to probe dmidecode to get hardware info

* Mon Feb 22 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-1
- packaging subscription-manager

