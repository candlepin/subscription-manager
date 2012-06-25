PREFIX ?=
SYSCONF ?= etc
PYTHON ?= python

INSTALL_DIR= usr/share
INSTALL_MODULE = rhsm
PKGNAME = subscription_manager
CODE_DIR = ${PREFIX}/${INSTALL_DIR}/${INSTALL_MODULE}/${PKGNAME}
VERSION = $(shell echo `grep ^Version: $(PKGNAME).spec | awk '{ print $$2 }'`)
OS = $(shell lsb_release -i | awk '{ print $$3 }' | awk -F. '{ print $$1}')
OS_VERSION = $(shell lsb_release -r | awk '{ print $$2 }' | awk -F. '{ print $$1}')
BIN_FILES = src/subscription-manager src/subscription-manager-gui \
			src/rhn-migrate-classic-to-rhsm \
			src/install-num-migrate-to-rhsm
SYSTEMD_INST_DIR=${PREFIX}/usr/lib/systemd/system

#this is the compat area for firstboot versions. If it's 6-compat, set to 6.
SRC_DIR = src/subscription_manager

CFLAGS = -Wall -g

%.pyc: %.py
	python -c "import py_compile; py_compile.compile('$<')"

build:	rhsmcertd rhsm-icon

bin:
	mkdir bin

RHSMCERTD_FLAGS=`pkg-config --cflags --libs glib-2.0`

PYFILES=`find  src/ -name "*.py"`
TESTFILES=`find test/ -name "*.py"`
STYLEFILES=$(PYFILES) $(BIN_FILES) $(TESTFILES)
GLADEFILES=`find src/subscription_manager/gui/data -name "*.glade"`

rhsmcertd: src/rhsmcertd.c bin
	${CC} ${CFLAGS} ${RHSMCERTD_FLAGS} src/rhsmcertd.c -o bin/rhsmcertd

check-syntax:
	${CC} ${CFLAGS} ${ICON_FLAGS} -o nul -S $(CHK_SOURCES)


ICON_FLAGS=`pkg-config --cflags --libs gtk+-2.0 libnotify gconf-2.0`

rhsm-icon: src/rhsm_icon.c bin
	# RHSM Status icon needs to be skipped in Fedora 15+ and RHEL7+:
	if [ ${OS} = Fedora ]; then \
		if [ ${OS_VERSION} -lt 15 ]; then \
			${CC} ${CFLAGS} ${ICON_FLAGS} -o bin/rhsm-icon src/rhsm_icon.c;\
		fi;\
	else \
		if [ ${OS_VERSION} -lt 7 ]; then \
			${CC} ${CFLAGS} ${ICON_FLAGS} -o bin/rhsm-icon src/rhsm_icon.c;\
		fi;\
	fi;\

dbus-service-install:
	install -d ${PREFIX}/etc/dbus-1/system.d
	install -d ${PREFIX}/${INSTALL_DIR}/dbus-1/system-services
	install -d ${PREFIX}/usr/libexec
	install -d ${PREFIX}/etc/bash_completion.d
	install -m 644 etc-conf/com.redhat.SubscriptionManager.conf \
		${PREFIX}/etc/dbus-1/system.d
	install -m 644 etc-conf/com.redhat.SubscriptionManager.service \
		${PREFIX}/${INSTALL_DIR}/dbus-1/system-services
	install -m 744 src/rhsm_d.py \
		${PREFIX}/usr/libexec/rhsmd

install-conf:
	install etc-conf/rhsm.conf ${PREFIX}/etc/rhsm/
	install -T etc-conf/logrotate.conf ${PREFIX}/etc/logrotate.d/subscription-manager
	install etc-conf/plugin/*.conf ${PREFIX}/etc/yum/pluginconf.d/
	install -m 644 etc-conf/subscription-manager.completion.sh ${PREFIX}/etc/bash_completion.d/subscription-manager

install-help-files:
	install -d ${PREFIX}/${INSTALL_DIR}/gnome/help/subscription-manager
	install -d ${PREFIX}/${INSTALL_DIR}/gnome/help/subscription-manager/C
	install -d \
		${PREFIX}/${INSTALL_DIR}/gnome/help/subscription-manager/C/figures
	install -d ${PREFIX}/${INSTALL_DIR}/omf/subscription-manager
	install docs/subscription-manager.xml \
		${PREFIX}/${INSTALL_DIR}/gnome/help/subscription-manager/C
	install docs/legal.xml \
		${PREFIX}/${INSTALL_DIR}/gnome/help/subscription-manager/C
	install docs/figures/rhsm-subscribe-prod.png \
		${PREFIX}/${INSTALL_DIR}/gnome/help/subscription-manager/C/figures
	install docs/figures/rhsm-status.png \
		${PREFIX}/${INSTALL_DIR}/gnome/help/subscription-manager/C/figures
	install docs/subscription-manager-C.omf \
		${PREFIX}/${INSTALL_DIR}/omf/subscription-manager

install: install-files install-conf install-help-files

install-files: dbus-service-install compile-po desktop-files
	install -d ${CODE_DIR}/gui/data/icons/scalable
	install -d ${CODE_DIR}/branding
	install -d ${PREFIX}/${INSTALL_DIR}/locale/
	install -d ${PREFIX}/usr/lib/yum-plugins/
	install -d ${PREFIX}/usr/sbin
	install -d ${PREFIX}/etc/rhsm
	install -d ${PREFIX}/etc/rhsm/facts
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
	install -d ${PREFIX}/var/lib/rhsm/packages
	install -d ${PREFIX}/var/lib/rhsm/cache
	install -d ${PREFIX}/usr/bin
	install -d ${PREFIX}/etc/rc.d/init.d
	install -d ${PREFIX}/usr/share/icons/hicolor/scalable/apps
	install -d ${PREFIX}/usr/share/rhn/up2date_client/firstboot/
	if [ ${OS_VERSION} = 5 ]; then install -d ${PREFIX}/usr/share/firstboot/modules; fi

	install -d ${PREFIX}/usr/libexec
	install -m 755 src/rhsmcertd-worker.py \
		${PREFIX}/usr/libexec/rhsmcertd-worker

	cp -R po/build/* ${PREFIX}/${INSTALL_DIR}/locale/

	install -m 644 -p ${SRC_DIR}/*.py ${CODE_DIR}
	install -m 644 -p ${SRC_DIR}/gui/*.py ${CODE_DIR}/gui
	install -m 644 -p ${SRC_DIR}/branding/*.py ${CODE_DIR}/branding
	install -m 644 -p ${SRC_DIR}/plugin/*.py ${PREFIX}/usr/lib/yum-plugins/

	install -m 644 ${SRC_DIR}/gui/data/*.glade ${CODE_DIR}/gui/data/
	install -m 644 ${SRC_DIR}/gui/data/icons/*.svg ${CODE_DIR}/gui/data/icons/
	install -m 644 ${SRC_DIR}/gui/data/icons/scalable/*.svg ${CODE_DIR}/gui/data/icons/scalable/
	ln -sf  /usr/share/${INSTALL_MODULE}/${PKGNAME}/gui/data/icons/scalable/subscription-manager.svg ${PREFIX}/${INSTALL_DIR}/icons/hicolor/scalable/apps/
	install src/subscription-manager ${PREFIX}/usr/sbin
	install src/rhn-migrate-classic-to-rhsm  ${PREFIX}/usr/sbin
	if [ ${OS_VERSION} = 5 ]; then install src/install-num-migrate-to-rhsm ${PREFIX}/usr/sbin; fi
	install src/subscription-manager-gui ${PREFIX}/usr/sbin
	install bin/* ${PREFIX}/usr/bin

	# Set up rhsmcertd daemon. If installing on Fedora 17+ or RHEL 7+
	# we prefer systemd over sysv as this is the new trend.
	if [ ${OS} = Fedora ] ; then \
		if [ ${OS_VERSION} -lt 17 ]; then \
			install src/rhsmcertd.init.d ${PREFIX}/etc/rc.d/init.d/rhsmcertd; \
		else \
			install -d ${SYSTEMD_INST_DIR}; \
			install etc-conf/rhsmcertd.service ${SYSTEMD_INST_DIR}; \
		fi; \
	else \
		if [ ${OS_VERSION} -lt 7 ]; then \
			install src/rhsmcertd.init.d ${PREFIX}/etc/rc.d/init.d/rhsmcertd; \
		else \
			install -d ${SYSTEMD_INST_DIR}; \
			install etc-conf/rhsmcertd.service ${SYSTEMD_INST_DIR}; \
		fi; \
	fi; \

	# RHEL 5 Customizations:
	if [ ${OS_VERSION} = 5 ]; then \
		install -m644 ${SRC_DIR}/gui/firstboot/*.py ${PREFIX}/usr/share/rhn/up2date_client/firstboot;\
		ln -sf  /usr/share/rhn/up2date_client/firstboot/rhsm_login.py ${PREFIX}/usr/share/firstboot/modules/;\
		ln -sf  /usr/share/rhn/up2date_client/firstboot/rhsm_confirm_subs.py ${PREFIX}/usr/share/firstboot/modules/;\
		ln -sf  /usr/share/rhn/up2date_client/firstboot/rhsm_select_sla.py ${PREFIX}/usr/share/firstboot/modules/;\
		ln -sf  /usr/share/rhn/up2date_client/firstboot/rhsm_manually_subscribe.py ${PREFIX}/usr/share/firstboot/modules/;\
	else \
		install -m644 ${SRC_DIR}/gui/firstboot/*.py ${PREFIX}/usr/share/rhn/up2date_client/firstboot;\
	fi;\

	install -m 644 man/rhn-migrate-classic-to-rhsm.8 ${PREFIX}/${INSTALL_DIR}/man/man8/
	install -m 644 man/rhsmcertd.8 ${PREFIX}/${INSTALL_DIR}/man/man8/
	install -m 644 man/rhsm-icon.8 ${PREFIX}/${INSTALL_DIR}/man/man8/
	install -m 644 man/subscription-manager.8 ${PREFIX}/${INSTALL_DIR}/man/man8/
	install -m 644 man/subscription-manager-gui.8 ${PREFIX}/${INSTALL_DIR}/man/man8/
	if [ ${OS_VERSION} = 5 ]; then install -m 644 man/install-num-migrate-to-rhsm.8 ${PREFIX}/${INSTALL_DIR}/man/man8/; fi

	# RHSM Status icon needs to be skipped in Fedora 15+ and RHEL7+:
	if [ ${OS} = Fedora ]; then \
		if [ ${OS_VERSION} -lt 15 ]; then \
			install -m 644 etc-conf/rhsm-icon.desktop \
				${PREFIX}/etc/xdg/autostart;\
		fi;\
	else \
		if [ ${OS_VERSION} -lt 7 ]; then \
			install -m 644 etc-conf/rhsm-icon.desktop \
				${PREFIX}/etc/xdg/autostart;\
		fi;\
	fi;\

	install -m 755 etc-conf/rhsmd.cron \
		${PREFIX}/etc/cron.daily/rhsmd
	install -m 644 etc-conf/subscription-manager.desktop \
		${PREFIX}/${INSTALL_DIR}/applications

	ln -sf /usr/bin/consolehelper ${PREFIX}/usr/bin/subscription-manager-gui
	ln -sf /usr/bin/consolehelper ${PREFIX}/usr/bin/subscription-manager

	install -m 644 etc-conf/subscription-manager-gui.pam \
		${PREFIX}/etc/pam.d/subscription-manager-gui
	install -m 644 etc-conf/subscription-manager-gui.console \
		${PREFIX}/etc/security/console.apps/subscription-manager-gui

	install -m 644 etc-conf/subscription-manager.pam \
		${PREFIX}/etc/pam.d/subscription-manager
	install -m 644 etc-conf/subscription-manager.console \
		${PREFIX}/etc/security/console.apps/subscription-manager



check:
	nosetests

coverage:
	nosetests --with-cover --cover-package subscription_manager --cover-erase

coverage-xunit:
	nosetests --with-xunit --with-cover --cover-package subscription_manager --cover-erase

coverage-html: coverage
	coverage html --include "${SRC_DIR}/*"

coverage-html-old:
	nosetests --with-cover --cover-package subscription_manager --cover-html --cover-html-dir test/html --cover-erase

coverage-xml: coverage
	coverage xml --include "${SRC_DIR}/*"

coverage-jenkins: coverage-xunit
	coverage html --include "${SRC_DIR}/*"
	coverage xml --include "${SRC_DIR}/*"

clean:
	rm -f *.pyc *.pyo *~ *.bak *.tar.gz

checkcommits:
	scripts/checkcommits.sh

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

desktop-files: etc-conf/rhsm-icon.desktop \
				etc-conf/subscription-manager.desktop

%.desktop: %.desktop.in po
	intltool-merge -d po $< $@

po/POTFILES.in:
	# generate the POTFILES.in file expected by intltool. it wants one
	# file per line, but we're lazy.
	find ${SRC_DIR}/ -name "*.py" > po/POTFILES.in
	find ${SRC_DIR}/gui/data/ -name "*.glade" >> po/POTFILES.in
	find src/ -name "*-to-rhsm" >> po/POTFILES.in
	find src/ -name "*.c" >> po/POTFILES.in
	find etc-conf/ -name "*.desktop.in" >> po/POTFILES.in

.PHONY: po/POTFILES.in %.desktop

gettext: po/POTFILES.in
	# Extract strings from our source files. any comments on the line above
	# the string marked for translation beginning with "translators" will be
	# included in the pot file.
	cd po && \
	intltool-update --pot -g keys

update-po:
	for f in $(shell find po/ -name "*.po") ; do \
		msgmerge -N --backup=none -U $$f po/keys.pot ; \
	done

uniq-po:
	for f in $(shell find po/ -name "*.po") ; do \
		msguniq $$f -o $$f ; \
	done

# Compile translations
compile-po:
	for lang in $(basename $(notdir $(wildcard po/*.po))) ; do \
		echo $$lang ; \
		mkdir -p po/build/$$lang/LC_MESSAGES/ ; \
		msgfmt -c --statistics -o po/build/$$lang/LC_MESSAGES/rhsm.mo po/$$lang.po ; \
	done

just-strings:
	-@ scripts/just_strings.py po/keys.pot

zanata-pull:
	cd po && zanata po pull --srcdir  ..

zanata-push:
	cd po
	if [ -z $(shell find -name "*.pot" | grep -v keys.pot) ] ; then \
		zanata po push --srcdir . ; \
	else 	\
		echo "po/ has more than one *.pot file, please clean up" ; \
	fi

# generate a en_US.po with long strings for testing
gen-test-long-po:
	-@ scripts/gen_test_en_po.py --long po/en_US.po

pyflakes:
# pyflakes doesn't have a config file, cli options, or a ignore tag
# and the variants of "redefination" we get now aren't really valid
# and other tools detect the valid cases, so ignore these
#
	@TMPFILE=`mktemp` || exit 1; \
	pyflakes $(STYLEFILES) |  grep -v "redefinition of unused.*from line.*" |  tee $$TMPFILE; \
	! test -s $$TMPFILE

pylint:
	@PYTHONPATH="src/:/usr/share/rhn:../python-rhsm/src/:/usr/share/rhsm" pylint --rcfile=pylintrc $(STYLEFILES)

tablint:
	@! GREP_COLOR='7;31' grep --color -nP "^\W*\t" $(STYLEFILES)

trailinglint:
	@! GREP_COLOR='7;31'  grep --color -nP "[ \t]$$" $(STYLEFILES)

whitespacelint: tablint trailinglint

# look for things that are likely debugging code left in by accident
debuglint:
	@! GREP_COLOR='7;31' grep --color -nP "pdb.set_trace|pydevd.settrace|import ipdb|import pdb|import pydevd" $(STYLEFILES)

# find widgets used via get_widget
# find widgets used as passed to init of SubscriptionManagerTab,
# find the widgets we actually find in the glade files
# see if any used ones are not defined
find-missing-widgets:
	@TMPFILE=`mktemp` || exit 1; \
	USED_WIDGETS=`mktemp` ||exit 1; \
	DEFINED_WIDGETS=`mktemp` ||exit 1; \
	perl -n -e "if (/get_widget\([\'|\"](.*?)[\'|\"]\)/) { print(\"\$$1\n\")}" $(STYLEFILES) > $$USED_WIDGETS; \
	pcregrep -h -o  -M  "(?:widgets|widget_names) = \[.*\s*.*?\s*.*\]" $(STYLEFILES) | perl -0 -n -e "my @matches = /[\'|\"](.*?)[\'|\"]/sg ; $$,=\"\n\"; print(@matches);" >> $$USED_WIDGETS; \
	perl -n -e "if (/<widget class=\".*?\" id=\"(.*?)\">/) { print(\"\$$1\n\")}" $(GLADEFILES) > $$DEFINED_WIDGETS; \
	while read line; do grep -F "$$line" $$DEFINED_WIDGETS > /dev/null ; STAT="$$?"; if [ "$$STAT" -ne "0" ] ; then echo "$$line"; fi;  done < $$USED_WIDGETS | tee $$TMPFILE; \
	! test -s $$TMPFILE

# look for python string formats that are known to break xgettext
# namely constructs of the forms: _("a" + "b")
#                                 _("a" + \
#                                   "b")
gettext_lint:
	@TMPFILE=`mktemp` || exit 1; \
	pcregrep -n --color=auto -M  "_\(.*[\'|\"].*[\'|\"]\s*\+.*?\s*[\"|\'].*[\"|\'].*\)"  $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

pep8:
	@TMPFILE=`mktemp` || exit 1; \
	pep8 --ignore E501 --exclude ".#*" --repeat src $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

rpmlint:
	@TMPFILE=`mktemp` || exit 1; \
	rpmlint -f rpmlint.config subscription-manager.spec | grep -v "^.*packages and .* specfiles checked\;" | tee $$TMPFILE; \
	! test -s $$TMPFILE

stylish: find-missing-widgets pyflakes whitespacelint pep8 gettext_lint rpmlint debuglint

jenkins: stylish coverage-jenkins


