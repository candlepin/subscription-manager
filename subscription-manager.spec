Name: subscription-manager      
Version: 0.1
Release: 2
Summary: Supported tools and libraries for subscription and repo Management       

Group:   System Environment/Base         
License: GPL       
Source0: %{name}-%{version}-%{release}.tar.gz       
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
Requires: python-dmidecode
Requires  python-ethtool 
Requires  python-simplejson
Requires:  m2crypto 
Requires: yum >= 3.2.19-15

%description
Subscription Manager package provides programs and libraries to allow users to manager subscriptions and repos from a unified entitlement or a deployment Platform.

%prep
%setup -q

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/share/rhsm
mkdir -p $RPM_BUILD_ROOT/usr/sbin
mkdir -p $RPM_BUILD_ROOT/etc/rhsm
mkdir -p $RPM_BUILD_ROOT/%{_mandir}/man8/
cp -R src/*.py $RPM_BUILD_ROOT/usr/share/rhsm
cp src/subscription-manager-cli $RPM_BUILD_ROOT/usr/sbin
cp etc-conf/* $RPM_BUILD_ROOT/etc/rhsm/
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
/usr/share/rhsm/rhsmplugin.*
/usr/share/rhsm/certificate.*
/usr/share/rhsm/certlib.*
/usr/share/rhsm/hardware.*
/usr/share/rhsm/config.*
/usr/share/rhsm/logutil.*
%attr(755,root,root) %{_sbindir}/subscription-manager-cli
%attr(770,root,root) %dir %{_var}/log/rhsm

# config files
%attr(644,root,root) /etc/rhsm/rhsm.conf

%doc

%changelog
* Tue Feb 23 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-1
- more changes to probe dmidecode to get hardware info

* Mon Feb 22 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.1-1
- packaging subscription-manager

