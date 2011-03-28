PREFIX ?= /
SYSCONF ?= etc
PYTHON ?= python

INSTALL_DIR= /usr/share/
INSTALL_MODULE = /rhsm/
PKGNAME = subscriptionmanager
CODE_DIR = ${PREFIX}/${INSTALL_DIR}/${INSTALL_MODULE}/${PKGNAME}/
VERSION = $(shell echo `grep ^Version: $(PKGNAME).spec | awk '{ print $$2 }'`)

CFLAGS = -Wall -g

%.pyc: %.py
	python -c "import py_compile; py_compile.compile('$<')"

build:	rhsmcertd rhsm-compliance-icon

bin:
	mkdir bin

rhsmcertd: src/rhsmcertd.c bin
	${CC} ${CFLAGS} src/rhsmcertd.c -o bin/rhsmcertd

COMPLIANCE_FLAGS=`pkg-config --cflags --libs gtk+-2.0 libnotify`

rhsm-compliance-icon: src/compliance/rhsm_compliance_icon.c bin
	${CC} ${CFLAGS} ${COMPLIANCE_FLAGS} -o bin/rhsm-compliance-icon \
		src/compliance/rhsm_compliance_icon.c

dbus-service-install:
	install -d ${PREFIX}/etc/dbus-1/system.d
	install -d ${PREFIX}/${INSTALL_DIR}/dbus-1/system-services
	install -d ${PREFIX}/usr/libexec
	install -m 644 etc-conf/com.redhat.SubscriptionManager.conf \
		${PREFIX}/etc/dbus-1/system.d
	install -m 644 etc-conf/com.redhat.SubscriptionManager.service \
		${PREFIX}/${INSTALL_DIR}/dbus-1/system-services
	install -m 744 src/compliance/rhsm_compliance_d.py \
		${PREFIX}/usr/libexec/rhsm-complianced

install-conf:
	install etc-conf/rhsm.conf ${PREFIX}/etc/rhsm/
	install -T etc-conf/logrotate.conf ${PREFIX}/etc/logrotate.d/subscription-manager
	install etc-conf/plugin/*.conf ${PREFIX}/etc/yum/pluginconf.d/
	install -m 644 etc-conf/ca/*.pem ${PREFIX}/etc/rhsm/ca/

install: install-files install-conf

install-files: dbus-service-install compile-po
	install -d ${CODE_DIR}/gui/data/icons/scalable
	install -d ${PREFIX}/${INSTALL_DIR}/locale/
	install -d ${PREFIX}/usr/lib/yum-plugins/
	install -d ${PREFIX}/usr/sbin
	install -d ${PREFIX}/etc/rhsm
	install -d ${PREFIX}/etc/rhsm/facts
	install -d ${PREFIX}/etc/rhsm/ca
	install -d ${PREFIX}/etc/xdg/autostart
	install -d ${PREFIX}/etc/cron.daily
	install -d ${PREFIX}/etc/pam.d
	install -d ${PREFIX}/etc/logrotate.d
	install -d ${PREFIX}/etc/security/console.apps
	install -d ${PREFIX}/etc/yum/pluginconf.d/
	install -d ${PREFIX}/${INSTALL_DIR}/man/man8/
	install -d ${PREFIX}/${INSTALL_DIR}/applications
	install -d ${PREFIX}/var/log/rhsm
	install -d ${PREFIX}/var/run/rhsm
	install -d ${PREFIX}/var/lib/rhsm/facts
	install -d ${PREFIX}/usr/bin
	install -d ${PREFIX}/etc/init.d
	install -d ${PREFIX}/${INSTALL_DIR}/icons/hicolor/scalable/apps
	install -d ${PREFIX}/${INSTALL_DIR}/firstboot/modules

	cp -R po/build/* ${PREFIX}/${INSTALL_DIR}/locale/

	install -m 644 -p src/*.py ${CODE_DIR}
	install -m 644 -p src/gui/*.py ${CODE_DIR}/gui
	install -m 644 -p src/plugin/*.py ${PREFIX}/usr/lib/yum-plugins/

	install -m 644 src/gui/data/*.glade ${CODE_DIR}/gui/data/
	install -m 644 src/gui/data/icons/*.svg ${CODE_DIR}/gui/data/icons/
	install -m 644 src/gui/data/icons/scalable/*.svg ${CODE_DIR}/gui/data/icons/scalable/
	ln -sf /${CODE_DIR}/gui/data/icons/scalable/subscription-manager.svg ${PREFIX}/${INSTALL_DIR}/icons/hicolor/scalable/apps/
	install src/subscription-manager ${PREFIX}/usr/sbin
	install src/subscription-manager-gui ${PREFIX}/usr/sbin
	install bin/* ${PREFIX}/usr/bin
	install src/rhsmcertd.init.d ${PREFIX}/etc/init.d/rhsmcertd
	install -m 644 man/* ${PREFIX}/${INSTALL_DIR}/man/man8/
	install -m644 src/gui/firstboot/*.py ${PREFIX}/${INSTALL_DIR}/firstboot/modules
	install -m 644 etc-conf/rhsm-compliance-icon.desktop \
		${PREFIX}/etc/xdg/autostart
	install -m 755 etc-conf/rhsm-complianced.cron \
		${PREFIX}/etc/cron.daily/rhsm-complianced
	install -m 644 etc-conf/subscription-manager.desktop \
		${PREFIX}/${INSTALL_DIR}/applications	
	ln -sf /usr/bin/consolehelper ${PREFIX}/usr/bin/subscription-manager-gui
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
	# Extract strings from our source files. any comments on the line above
	# the string marked for translation beginning with "translators" will be
	# included in the pot file.
	xgettext -ctranslators -s --language=Python -o po/keys.pot \
		$(shell find src/ -name "*.py")
	xgettext -ctranslators -s -k_ -kN_ --language=C -j -o po/keys.pot \
		src/compliance/*.c
	xgettext -ctranslators -s --language=Glade -j -o po/keys.pot \
		src/gui/data/*.glade

update-po:
	for f in $(shell find po/ -name "*.po") ; do \
		msgmerge -N --backup=none -U $$f po/keys.pot ; \
	done

# Compile translations
compile-po:
	for lang in $(basename $(notdir $(wildcard po/*.po))) ; do \
		echo $$lang ; \
		mkdir -p po/build/$$lang/LC_MESSAGES/ ; \
		msgfmt -c --statistics -o po/build/$$lang/LC_MESSAGES/rhsm.mo po/$$lang.po ; \
	done

pyflakes:
	@TMPFILE=`mktemp` || exit 1; \
	find -name \*.py | xargs pyflakes | tee $$TMPFILE; \
	! test -s $$TMPFILE

tablint:
	@! find -name \*py | xargs grep -nP "^\W*\t"

trailinglint:
	@! find -name \*py | xargs grep -nP "[ \t]$$"

whitespacelint: tablint trailinglint

pep8:
	@TMPFILE=`mktemp` || exit 1; \
	pep8 --repeat src | tee $$TMPFILE; \
	! test -s $$TMPFILE


stylish: pyflakes whitespacelint pep8 
