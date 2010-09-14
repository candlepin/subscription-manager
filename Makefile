PREFIX ?= /
SYSCONF ?= etc
PYTHON ?= python

PKGNAME = subscription-manager
VERSION = $(shell echo `grep ^Version: $(PKGNAME).spec | awk '{ print $$2 }'`)

CFLAGS = -Wall -g

%.pyc: %.py
	python -c "import py_compile; py_compile.compile('$<')"

build:	rhsmcertd rhsm-compliance-icon

bin:
	@mkdir -p bin

rhsmcertd: src/rhsmcertd.c bin
	cc src/rhsmcertd.c -o bin/rhsmcertd

COMPLIANCE_FLAGS=`pkg-config --cflags --libs gtk+-2.0 unique-1.0 libnotify`

rhsm-compliance-icon: src/compliance/rhsm_compliance_icon.c bin
	${CC} ${CFLAGS} ${COMPLIANCE_FLAGS} -o bin/rhsm-compliance-icon \
		src/compliance/rhsm_compliance_icon.c

dbus-service-install:
	@mkdir -p ${PREFIX}/etc/dbus-1/system.d
	@mkdir -p ${PREFIX}/usr/share/dbus-1/system-services
	@mkdir -p ${PREFIX}/usr/libexec
	install -m 644 etc-conf/com.redhat.SubscriptionManager.conf \
		${PREFIX}/etc/dbus-1/system.d
	install -m 644 etc-conf/com.redhat.SubscriptionManager.service \
		${PREFIX}/usr/share/dbus-1/system-services
	install -m 744 src/compliance/rhsm_compliance_d.py \
		${PREFIX}/usr/libexec/rhsm-complianced

install: dbus-service-install compile_pos
	@mkdir -p ${PREFIX}/usr/share/rhsm/gui/data/icons/16x16
	@mkdir -p ${PREFIX}/usr/share/rhsm/translations
	@mkdir -p ${PREFIX}/usr/lib/yum-plugins/
	@mkdir -p ${PREFIX}/usr/sbin
	@mkdir -p ${PREFIX}/etc/rhsm
	@mkdir -p ${PREFIX}/etc/rhsm/facts
	@mkdir -p ${PREFIX}/etc/xdg/autostart
	@mkdir -p ${PREFIX}/etc/cron.daily
	@mkdir -p ${PREFIX}/etc/pam.d
	@mkdir -p ${PREFIX}/etc/security/console.apps
	@mkdir -p ${PREFIX}/etc/yum/pluginconf.d/
	@mkdir -p ${PREFIX}/usr/share/man/man8/
	@mkdir -p ${PREFIX}/var/log/rhsm
	@mkdir -p ${PREFIX}/var/lib/rhsm/facts
	@mkdir -p ${PREFIX}/usr/bin
	@mkdir -p ${PREFIX}/etc/init.d
	@mkdir -p ${PREFIX}/usr/share/icons/hicolor/16x16/apps
	@mkdir -p ${PREFIX}/usr/share/firstboot/
	@mkdir -p ${PREFIX}/usr/share/firstboot/modules
	cp -R po/build/* ${PREFIX}/usr/share/rhsm/translations
	cp -R src/*.py ${PREFIX}/usr/share/rhsm
	cp -R src/gui/*.py ${PREFIX}/usr/share/rhsm/gui
	cp -R src/gui/data/*.glade ${PREFIX}/usr/share/rhsm/gui/data/
	cp -R src/gui/data/icons/*.png ${PREFIX}/usr/share/rhsm/gui/data/icons/
	cp -R src/gui/data/icons/16x16/subsmgr.png ${PREFIX}/usr/share/icons/hicolor/16x16/apps/
	cp -R src/plugin/*.py ${PREFIX}/usr/lib/yum-plugins/
	cp src/subscription-manager-cli ${PREFIX}/usr/sbin
	cp src/subscription-manager-gui ${PREFIX}/usr/sbin
	cp etc-conf/rhsm.conf ${PREFIX}/etc/rhsm/
	cp etc-conf/rhsmplugin.conf ${PREFIX}/etc/yum/pluginconf.d/
	cp etc-conf/pidplugin.conf ${PREFIX}/etc/yum/pluginconf.d/
	cp bin/* ${PREFIX}/usr/bin
	cp src/rhsmcertd.init.d ${PREFIX}/etc/init.d/rhsmcertd
	cp man/* ${PREFIX}/usr/share/man/man8/
	cp src/gui/firstboot/*.py ${PREFIX}/usr/share/firstboot/modules
	install -m 755 etc-conf/rhsm-compliance-icon.desktop \
		${PREFIX}/etc/xdg/autostart
	install -m 755 etc-conf/rhsm-complianced.cron \
		${PREFIX}/etc/cron.daily/rhsm-complianced
	ln -sf consolehelper ${PREFIX}/usr/bin/subscription-manager-gui
	install -m 644 etc-conf/subscription-manager-gui.pam \
		${PREFIX}/etc/pam.d/subscription-manager-gui
	install -m 644 etc-conf/subscription-manager-gui.console \
		${PREFIX}/etc/security/console.apps/subscription-manager-gui

check:
	nosetests


clean:
	rm -f *.pyc *.pyo *~ *.bak *.tar.gz

archive: clean
	@rm -rf ${PKGNAME}-%{VERSION}.tar.gz
	@rm -rf /tmp/${PKGNAME}-$(VERSION) /tmp/${PKGNAME}
	@rm -rf po/build
	@dir=$$PWD; cd /tmp; cp -a $$dir ${PKGNAME}
	@rm -f /tmp/${PKGNAME}/${PKGNAME}-daily.spec
	@mv /tmp/${PKGNAME} /tmp/${PKGNAME}-$(VERSION)
	@dir=$$PWD; cd /tmp; tar cvzf $$dir/${PKGNAME}-$(VERSION).tar.gz --exclude \.svn ${PKGNAME}-$(VERSION)
	@rm -rf /tmp/${PKGNAME}-$(VERSION)	
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.gz"

rpm: archive
	rpmbuild -ta ${PKGNAME}-$(VERSION).tar.gz

gettext:
	# Extract glade strings into .h files:
	for f in $(shell find src/ -name "*.glade") ; do \
		intltool-extract --type=gettext/glade $$f; \
	done
	# Extract strings from Python and glade.h:
	# TODO: glade.h files are getting written out into source tree, 
	# how should we deal with these?
	xgettext --language=Python --keyword=_ --keyword=N_ -ktrc:1c,2 -ktrnc:1c,2,3 -ktr -kmarktr -ktrn:1,2 -o po/keys.pot $(shell find src/ -name "*.py") src/gui/data/*.glade.h
	for f in $(shell find po/ -name "*.po") ; do \
		msgmerge -N --backup=none -U $$f po/keys.pot ; \
	done

# Compile translations
# TODO: look for .po files instead of hardcoding, couldn't get this to work:
#		basename $$f .po ; \
	
LANGUAGES = en_CA en_US
compile_pos:
	for lang in $(LANGUAGES) ; do \
		echo $$lang ; \
		mkdir -p po/build/$$lang/LC_MESSAGES/ ; \
		msgfmt -c --statistics -o po/build/$$lang/LC_MESSAGES/rhsm.mo po/$$lang.po ; \
	done

