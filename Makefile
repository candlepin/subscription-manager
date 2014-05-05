SHELL := /bin/bash
PREFIX ?=
SYSCONF ?= etc
PYTHON ?= python

INSTALL_DIR = usr/share
INSTALL_MODULE = rhsm
PKGNAME = subscription_manager
CODE_DIR = $(PREFIX)/$(INSTALL_DIR)/$(INSTALL_MODULE)/$(PKGNAME)
OS = $(shell lsb_release -i | awk '{ print $$3 }' | awk -F. '{ print $$1}')
OS_VERSION = $(shell lsb_release -r | awk '{ print $$2 }' | awk -F. '{ print $$1}')
BIN_DIR := bin/
BIN_FILES := $(BIN_DIR)/subscription-manager $(BIN_DIR)/subscription-manager-gui \
			 $(BIN_DIR)/rhn-migrate-classic-to-rhsm \
			 $(BIN_DIR)/rct \
			 $(BIN_DIR)/rhsm-debug
SYSTEMD_INST_DIR := $(PREFIX)/usr/lib/systemd/system

RHSM_PLUGIN_DIR := $(PREFIX)/usr/share/rhsm-plugins/
RHSM_PLUGIN_CONF_DIR := $(PREFIX)/etc/rhsm/pluginconf.d/

BASE_SRC_DIR := src
SRC_DIR := $(BASE_SRC_DIR)/subscription_manager
RCT_CODE_DIR := $(PREFIX)/$(INSTALL_DIR)/$(INSTALL_MODULE)/rct
RCT_SRC_DIR := $(BASE_SRC_DIR)/rct
RD_CODE_DIR := $(PREFIX)/$(INSTALL_DIR)/$(INSTALL_MODULE)/rhsm_debug
RD_SRC_DIR := $(BASE_SRC_DIR)/rhsm_debug
RHSM_ICON_SRC_DIR := $(BASE_SRC_DIR)/rhsm_icon
DAEMONS_SRC_DIR := $(BASE_SRC_DIR)/daemons
EXAMPLE_PLUGINS_SRC_DIR := example-plugins/
CONTENT_PLUGINS_SRC_DIR := $(BASE_SRC_DIR)/content_plugins/

# FIXME: setup.py, distutils, etc
RHSM_CONTENT_PLUGINS_DIR := /usr/lib/python2.7/site-packages/rhsm_content_plugins/

YUM_PLUGINS_SRC_DIR := $(BASE_SRC_DIR)/plugins
ALL_SRC_DIRS := $(SRC_DIR) $(RCT_SRC_DIR) $(RD_SRC_DIR) $(DAEMONS_SRC_DIR) $(CONTENT_PLUGINS_SRC_DIR) $(EXAMPLE_PLUGINS_SRC_DIR) $(YUM_PLUGINS_SRC_DIR)

CFLAGS ?= -g -Wall

%.pyc: %.py
	python -c "import py_compile; py_compile.compile('$<')"

build:	rhsmcertd rhsm-icon

# we never "remake" this makefile, so add a target so
# we stop searching for implicit rules on how to remake it
Makefile: ;

bin:
	mkdir bin

RHSMCERTD_FLAGS = `pkg-config --cflags --libs glib-2.0`

PYFILES := `find $(ALL_SRC_DIRS) -name "*.py"`
EXAMPLE_PLUGINS_PYFILES := `find "$(EXAMPLE_PLUGINS_SRC_DIR)/*.py"`
# Ignore certdata.py from style checks as tabs and trailing
# whitespace are required for testing.
TESTFILES=`find  test/ \( ! -name certdata.py ! -name manifestdata.py \) -name "*.py"`
STYLEFILES=$(PYFILES) $(BIN_FILES) $(TESTFILES)
GLADEFILES=`find src/subscription_manager/gui/data -name "*.glade"`

rhsmcertd: $(DAEMONS_SRC_DIR)/rhsmcertd.c bin
	$(CC) $(CFLAGS) $(RHSMCERTD_FLAGS) $(DAEMONS_SRC_DIR)/rhsmcertd.c -o bin/rhsmcertd

check-syntax:
	$(CC) $(CFLAGS) $(ICON_FLAGS) -o nul -S $(CHK_SOURCES)


ICON_FLAGS = `pkg-config --cflags --libs gtk+-2.0 libnotify gconf-2.0 dbus-glib-1`

rhsm-icon: $(RHSM_ICON_SRC_DIR)/rhsm_icon.c bin
	$(CC) $(CFLAGS) $(ICON_FLAGS) -o bin/rhsm-icon $(RHSM_ICON_SRC_DIR)/rhsm_icon.c;\

dbus-service-install:
	install -d $(PREFIX)/etc/dbus-1/system.d
	install -d $(PREFIX)/$(INSTALL_DIR)/dbus-1/system-services
	install -d $(PREFIX)/usr/libexec
	install -d $(PREFIX)/etc/bash_completion.d
	install -m 644 etc-conf/com.redhat.SubscriptionManager.conf \
		$(PREFIX)/etc/dbus-1/system.d
	install -m 644 etc-conf/com.redhat.SubscriptionManager.service \
		$(PREFIX)/$(INSTALL_DIR)/dbus-1/system-services
	install -m 744 $(DAEMONS_SRC_DIR)/rhsm_d.py \
		$(PREFIX)/usr/libexec/rhsmd

install-conf:
	install etc-conf/rhsm.conf $(PREFIX)/etc/rhsm/
	install -T etc-conf/logrotate.conf $(PREFIX)/etc/logrotate.d/subscription-manager
	install etc-conf/plugin/*.conf $(PREFIX)/etc/yum/pluginconf.d/
	install -m 644 etc-conf/subscription-manager.completion.sh $(PREFIX)/etc/bash_completion.d/subscription-manager
	install -m 644 etc-conf/rct.completion.sh $(PREFIX)/etc/bash_completion.d/rct
	install -m 644 etc-conf/rhsm-debug.completion.sh $(PREFIX)/etc/bash_completion.d/rhsm-debug
	install -m 644 etc-conf/rhn-migrate-classic-to-rhsm.completion.sh $(PREFIX)/etc/bash_completion.d/rhn-migrate-classic-to-rhsm
	install -m 644 etc-conf/rhsm-icon.completion.sh $(PREFIX)/etc/bash_completion.d/rhsm-icon
	install -m 644 etc-conf/rhsmcertd.completion.sh $(PREFIX)/etc/bash_completion.d/rhsmcertd

install-help-files:
	install -d $(PREFIX)/$(INSTALL_DIR)/gnome/help/subscription-manager
	install -d $(PREFIX)/$(INSTALL_DIR)/gnome/help/subscription-manager/C
	install -d \
		$(PREFIX)/$(INSTALL_DIR)/gnome/help/subscription-manager/C/figures
	install -d $(PREFIX)/$(INSTALL_DIR)/omf/subscription-manager
	install docs/subscription-manager.xml \
		$(PREFIX)/$(INSTALL_DIR)/gnome/help/subscription-manager/C
	install docs/legal.xml \
		$(PREFIX)/$(INSTALL_DIR)/gnome/help/subscription-manager/C
	install docs/figures/*.png \
		$(PREFIX)/$(INSTALL_DIR)/gnome/help/subscription-manager/C/figures
	install docs/subscription-manager-C.omf \
		$(PREFIX)/$(INSTALL_DIR)/omf/subscription-manager


install-content-plugins:
	install -d $(RHSM_PLUGIN_DIR)
	install -d $(RHSM_PLUGIN_DIR)/ostree
	# top level plugin entry point
	install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/ostree_content.py $(RHSM_PLUGIN_DIR)

	# plugin support code could live anywhere on python path
	# for now install it with core subman code
	# FIXME: install to site-packages, or add setup.py's etc
	# install to /usr/lib/python2.7/site-packages/rhsm_content_plugins/
	install -d $(RHSM_CONTENT_PLUGINS_DIR)

	install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/__init__.py $(RHSM_CONTENT_PLUGINS_DIR)/
	install -d $(RHSM_CONTENT_PLUGINS_DIR)/ostree
	install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/ostree/*.py $(RHSM_CONTENT_PLUGINS_DIR)/ostree

install-content-plugins-conf:
	install -d $(RHSM_PLUGIN_CONF_DIR)
	install -m 644 -p $(CONTENT_PLUGINS_SRC_DIR)/ostree_content.OstreeContentPlugin.conf $(RHSM_PLUGIN_CONF_DIR)

install-plugins: install-content-plugins
	install -d $(RHSM_PLUGIN_DIR)
#	install -m 644 -p src/rhsm-plugins/*.py $(RHSM_PLUGIN_DIR)

install-plugins-conf:install-content-plugins-conf
	install -d $(RHSM_PLUGIN_CONF_DIR)
#	install -m 644 -p src/rhsm-plugins/*.conf $(RHSM_PLUGIN_CONF_DIR)

.PHONY: install-example-plugins
install-example-plugins: install-example-plugins-files install-example-plugins-conf

install-example-plugins-files:
	install -d $(RHSM_PLUGIN_DIR)
	install -m 644 -p $(EXAMPLE_PLUGINS_SRC_DIR)/*.py $(RHSM_PLUGIN_DIR)

install-example-plugins-conf:
	install -d $(RHSM_PLUGIN_CONF_DIR)
	install -m 644 -p $(EXAMPLE_PLUGINS_SRC_DIR)/*.conf $(RHSM_PLUGIN_CONF_DIR)

.PHONY: install
install: install-files install-conf install-help-files install-plugins-conf

install-files: dbus-service-install compile-po desktop-files install-plugins
	install -d $(CODE_DIR)/gui/data/icons
	install -d $(CODE_DIR)/branding
	install -d $(CODE_DIR)/migrate
	install -d $(PREFIX)/$(INSTALL_DIR)/locale/
	install -d $(PREFIX)/usr/lib/yum-plugins/
	install -d $(PREFIX)/usr/sbin
	install -d $(PREFIX)/etc/rhsm
	install -d $(PREFIX)/etc/rhsm/facts
	install -d $(PREFIX)/etc/xdg/autostart
	install -d $(PREFIX)/etc/cron.daily
	install -d $(PREFIX)/etc/pam.d
	install -d $(PREFIX)/etc/logrotate.d
	install -d $(PREFIX)/etc/security/console.apps
	install -d $(PREFIX)/etc/yum/pluginconf.d/
	install -d $(PREFIX)/$(INSTALL_DIR)/man/man8/
	install -d $(PREFIX)/$(INSTALL_DIR)/applications
	install -d $(PREFIX)/var/log/rhsm
	install -d $(PREFIX)/var/spool/rhsm/debug
	install -d $(PREFIX)/var/run/rhsm
	install -d $(PREFIX)/var/lib/rhsm/facts
	install -d $(PREFIX)/var/lib/rhsm/packages
	install -d $(PREFIX)/var/lib/rhsm/cache
	install -d $(PREFIX)/usr/bin
	install -d $(PREFIX)/etc/rc.d/init.d
	install -d $(PREFIX)/usr/share/icons/hicolor/16x16/apps
	install -d $(PREFIX)/usr/share/icons/hicolor/22x22/apps
	install -d $(PREFIX)/usr/share/icons/hicolor/24x24/apps
	install -d $(PREFIX)/usr/share/icons/hicolor/32x32/apps
	install -d $(PREFIX)/usr/share/icons/hicolor/48x48/apps
	install -d $(PREFIX)/usr/share/icons/hicolor/96x96/apps
	install -d $(PREFIX)/usr/share/icons/hicolor/256x256/apps
	install -d $(PREFIX)/usr/share/icons/hicolor/scalable/apps
	install -d $(PREFIX)/usr/share/rhsm/subscription_manager/gui/firstboot

	# Adjust firstboot screen location for RHEL 6:
	if [ $(OS_VERSION) -le 6 ]; then \
		install -d $(PREFIX)/usr/share/rhn/up2date_client/firstboot; \
	else \
		install -d $(PREFIX)/usr/share/firstboot/modules; \
	fi; \

	install -d $(PREFIX)/usr/libexec
	install -m 755 $(DAEMONS_SRC_DIR)/rhsmcertd-worker.py \
		$(PREFIX)/usr/libexec/rhsmcertd-worker

	cp -R po/build/* $(PREFIX)/$(INSTALL_DIR)/locale/

	install -m 644 -p $(SRC_DIR)/*.py $(CODE_DIR)
	install -m 644 -p $(SRC_DIR)/gui/*.py $(CODE_DIR)/gui
	install -m 644 -p $(SRC_DIR)/migrate/*.py $(CODE_DIR)/migrate
	install -m 644 -p $(SRC_DIR)/branding/*.py $(CODE_DIR)/branding
	install -m 644 -p src/plugins/*.py $(PREFIX)/usr/lib/yum-plugins/
	install -m 644 etc-conf/subscription-manager-gui.completion.sh $(PREFIX)/etc/bash_completion.d/subscription-manager-gui

	install -m 644 $(SRC_DIR)/gui/data/*.glade $(CODE_DIR)/gui/data/

	#icons
	install -m 644 $(SRC_DIR)/gui/data/icons/hicolor/16x16/apps/*.png \
		$(PREFIX)/usr/share/icons/hicolor/16x16/apps
	install -m 644 $(SRC_DIR)/gui/data/icons/hicolor/22x22/apps/*.png \
		$(PREFIX)/usr/share/icons/hicolor/22x22/apps
	install -m 644 $(SRC_DIR)/gui/data/icons/hicolor/24x24/apps/*.png \
		$(PREFIX)/usr/share/icons/hicolor/24x24/apps
	install -m 644 $(SRC_DIR)/gui/data/icons/hicolor/32x32/apps/*.png \
		$(PREFIX)/usr/share/icons/hicolor/32x32/apps
	install -m 644 $(SRC_DIR)/gui/data/icons/hicolor/48x48/apps/*.png \
		$(PREFIX)/usr/share/icons/hicolor/48x48/apps
	install -m 644 $(SRC_DIR)/gui/data/icons/hicolor/96x96/apps/*.png \
		$(PREFIX)/usr/share/icons/hicolor/96x96/apps
	install -m 644 $(SRC_DIR)/gui/data/icons/hicolor/256x256/apps/*.png \
		$(PREFIX)/usr/share/icons/hicolor/256x256/apps
	install -m 644 $(SRC_DIR)/gui/data/icons/hicolor/scalable/apps/*.svg \
		$(PREFIX)/usr/share/icons/hicolor/scalable/apps
	install -m 644 $(SRC_DIR)/gui/data/icons/*.svg \
		$(CODE_DIR)/gui/data/icons

	install bin/subscription-manager $(PREFIX)/usr/sbin
	install bin/rhn-migrate-classic-to-rhsm  $(PREFIX)/usr/sbin
	install bin/subscription-manager-gui $(PREFIX)/usr/sbin
	install bin/rhsmcertd $(PREFIX)/usr/bin

	# Set up rhsmcertd daemon. If installing on Fedora 17+ or RHEL 7+
	# we prefer systemd over sysv as this is the new trend.
	if [ $(OS) = Fedora ] ; then \
		if [ $(OS_VERSION) -lt 17 ]; then \
			install etc-conf/rhsmcertd.init.d \
				$(PREFIX)/etc/rc.d/init.d/rhsmcertd; \
		else \
			install -d $(SYSTEMD_INST_DIR); \
			install -d $(PREFIX)/usr/lib/tmpfiles.d; \
			install etc-conf/rhsmcertd.service $(SYSTEMD_INST_DIR); \
			install etc-conf/subscription-manager.conf.tmpfiles \
				$(PREFIX)/usr/lib/tmpfiles.d/subscription-manager.conf; \
		fi; \
	else \
		if [ $(OS_VERSION) -lt 7 ]; then \
			install etc-conf/rhsmcertd.init.d \
				$(PREFIX)/etc/rc.d/init.d/rhsmcertd; \
		else \
			install -d $(SYSTEMD_INST_DIR); \
			install -d $(PREFIX)/usr/lib/tmpfiles.d; \
			install etc-conf/rhsmcertd.service $(SYSTEMD_INST_DIR); \
			install etc-conf/subscription-manager.conf.tmpfiles \
				$(PREFIX)/usr/lib/tmpfiles.d/subscription-manager.conf; \
		fi; \
	fi; \

	# RHEL 6 Customizations:
	if [ $(OS_VERSION) -le 6 ]; then \
		install -m644 $(SRC_DIR)/gui/firstboot/*.py $(PREFIX)/usr/share/rhn/up2date_client/firstboot;\
	else \
		install -m644 $(SRC_DIR)/gui/firstboot/*.py $(PREFIX)/usr/share/firstboot/modules/;\
	fi;\

	install -m 644 man/rhn-migrate-classic-to-rhsm.8 $(PREFIX)/$(INSTALL_DIR)/man/man8/
	install -m 644 man/rhsmcertd.8 $(PREFIX)/$(INSTALL_DIR)/man/man8/
	install -m 644 man/rhsm-icon.8 $(PREFIX)/$(INSTALL_DIR)/man/man8/
	install -m 644 man/subscription-manager.8 $(PREFIX)/$(INSTALL_DIR)/man/man8/
	install -m 644 man/subscription-manager-gui.8 $(PREFIX)/$(INSTALL_DIR)/man/man8/
	install -m 644 man/rct.8 $(PREFIX)/$(INSTALL_DIR)/man/man8/
	install -m 644 man/rhsm-debug.8 $(PREFIX)/$(INSTALL_DIR)/man/man8/

	install -m 644 etc-conf/rhsm-icon.desktop \
		$(PREFIX)/etc/xdg/autostart;\
	install bin/rhsm-icon $(PREFIX)/usr/bin;\

	install -m 700 etc-conf/rhsmd.cron \
		$(PREFIX)/etc/cron.daily/rhsmd
	install -m 644 etc-conf/subscription-manager-gui.desktop \
		$(PREFIX)/$(INSTALL_DIR)/applications

	ln -sf /usr/bin/consolehelper $(PREFIX)/usr/bin/subscription-manager-gui
	ln -sf /usr/bin/consolehelper $(PREFIX)/usr/bin/subscription-manager

	install -m 644 etc-conf/subscription-manager-gui.pam \
		$(PREFIX)/etc/pam.d/subscription-manager-gui
	install -m 644 etc-conf/subscription-manager-gui.console \
		$(PREFIX)/etc/security/console.apps/subscription-manager-gui

	install -m 644 etc-conf/subscription-manager.pam \
		$(PREFIX)/etc/pam.d/subscription-manager
	install -m 644 etc-conf/subscription-manager.console \
		$(PREFIX)/etc/security/console.apps/subscription-manager

	install -d $(RCT_CODE_DIR)
	install -m 644 -p $(RCT_SRC_DIR)/*.py $(RCT_CODE_DIR)
	install bin/rct $(PREFIX)/usr/bin

	install -d $(RD_CODE_DIR)
	install -m 644 -p $(RD_SRC_DIR)/*.py $(RD_CODE_DIR)
	install bin/rhsm-debug $(PREFIX)/usr/bin



check:
	nosetests

smoke:
	test/smoke.sh

coverage:
	nosetests --with-cover --cover-package subscription_manager --cover-erase

coverage-xunit:
	nosetests --with-xunit --with-cover --cover-package subscription_manager --cover-erase

coverage-html: coverage
	coverage html

coverage-html-old:
	nosetests --with-cover --cover-package subscription_manager --cover-html --cover-html-dir test/html --cover-erase

coverage-xml: coverage
	coverage xml

coverage-jenkins: coverage-xunit
	coverage html
	coverage xml

clean:
	rm -f *.pyc *.pyo *~ *.bak *.tar.gz
	rm -f bin/rhsmcertd
	rm -f bin/rhsm-icon

checkcommits:
	scripts/checkcommits.sh

desktop-files: etc-conf/rhsm-icon.desktop \
				etc-conf/subscription-manager-gui.desktop

%.desktop: %.desktop.in po
	intltool-merge -d po $< $@

po/POTFILES.in:
	# generate the POTFILES.in file expected by intltool. it wants one
	# file per line, but we're lazy.
	find $(SRC_DIR)/ $(RCT_SRC_DIR) $(RD_SRC_DIR) $(DAEMONS_SRC_DIR) $(YUM_PLUGINS_SRC_DIR) -name "*.py" > po/POTFILES.in
	find $(SRC_DIR)/gui/data/ -name "*.glade" >> po/POTFILES.in
	find $(BIN_DIR) -name "*-to-rhsm" >> po/POTFILES.in
	find $(BIN_DIR) -name "subscription-manager*" >> po/POTFILES.in
	find $(BIN_DIR) -name "rct" >> po/POTFILES.in
	find $(BIN_DIR) -name "rhsm-debug" >> po/POTFILES.in
	find src/ -name "*.c" >> po/POTFILES.in
	find etc-conf/ -name "*.desktop.in" >> po/POTFILES.in
	find $(RCT_SRC_DIR)/ -name "*.py" >> po/POTFILES.in
	find $(RD_SRC_DIR)/ -name "*.py" >> po/POTFILES.in
	echo $$(echo `pwd`|rev | sed -r 's|[^/]+|..|g') | sed 's|$$|$(shell find /usr/lib*/python2* -name "optparse.py")|' >> po/POTFILES.in

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

# just run a check to make sure these compile
polint:
	# This is just informational, most zanata po files dont pass
	for lang in $(basename $(notdir $(wildcard po/*.po))) ; do \
		msgfmt -c -o /dev/null po/$$lang.po ; \
	done ;

just-strings:
	-@ scripts/just_strings.py po/keys.pot

zanata-pull:
	pushd po && zanata pull --transdir . && popd

zanata-push:
	pushd po; \
	ls -al; \
	if [ -z $(shell find -name "*.pot" | grep -v keys.pot) ] ; then \
		zanata push ; \
	else 	\
		echo "po/ has more than one *.pot file, please clean up" ; \
	fi; \
	popd

# do all the zanata bits
zanata: gettext zanata-push zanata-pull update-po
	echo "# pofiles should be ready to commit and push"

# generate a en_US.po with long strings for testing
gen-test-long-po:
	-@ scripts/gen_test_en_po.py --long po/en_US.po

pyflakes:
# pyflakes doesn't have a config file, cli options, or a ignore tag
# and the variants of "redefination" we get now aren't really valid
# and other tools detect the valid cases, so ignore these
#
	@TMPFILE=`mktemp` || exit 1; \
	pyflakes $(STYLEFILES) |  grep -v "redefinition of unused.*from line.*" |  grep -v "'site' imported but unused" |  tee $$TMPFILE; \
	! test -s $$TMPFILE

pylint:
	@PYTHONPATH="src/:/usr/share/rhn:../python-rhsm/src/:/usr/share/rhsm" pylint --rcfile=pylintrc $(STYLEFILES)

tablint:
	@! GREP_COLOR='7;31' grep --color -nP "^\W*\t" $(STYLEFILES)

trailinglint:
	@! GREP_COLOR='7;31'  grep --color -nP "[ \t]$$" $(STYLEFILES)

.PHONY: whitespacelint
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

# find any signals defined in glade and make sure we use them somewhere
# this would be better if we could statically extract the used signals from
# the code.
find-missing-signals:
	@TMPFILE=`mktemp` || exit 1; \
	DEFINED_SIGNALS=`mktemp` ||exit 1; \
	perl -n -e "if (/<signal name=\"(.*?)\" handler=\"(.*?)\"/) { print(\"\$$2\n\")}" $(GLADEFILES) > $$DEFINED_SIGNALS; \
	while read line; do grep -F  "$$line" $(PYFILES) > /dev/null; STAT="$$?"; if [ "$$STAT" -ne "0" ] ; then echo "$$line"; fi;  done < $$DEFINED_SIGNALS | tee $$TMPFILE; \
	! test -s $$TMPFILE
# try to clean up the "swapped=no" signal thing in
# glade files, since rhel6 hates it
# also remove unneeded 'orientation' property for vbox's
# since it causes warnings on RHEL5
fix-glade:
	perl -pi -e 's/(swapped=\".*?\")//' $(GLADEFILES)
	perl -pi -e 's/^.*property\s*name=\"orientation\">vertical.*$$//' $(GLADEFILES)


# look for python string formats that are known to break xgettext
# namely constructs of the forms: _("a" + "b")
#                                 _("a" + \
#                                   "b")
#  also look for _(a) usages
gettext_lint:
	@TMPFILE=`mktemp` || exit 1; \
	pcregrep -n --color=auto -M "_\(.*[\'|\"].*?[\'|\"]\s*\+.*?(?s)\s*[\"|\'].*?(?-s)[\"|\'].*?\)"  $(STYLEFILES) | tee $$TMPFILE; \
	pcregrep -n --color=auto -M "[^_]_\([^\'\"].*?[\'\"]?\)" $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

#see bz #826874, causes issues on older libglade
gladelint:
	@TMPFILE=`mktemp` || exit 1; \
	grep -nP  "swapped=\"no\"" $(GLADEFILES) | tee $$TMPFILE; \
    grep -nP "property name=\"orientation\"" $(GLADEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

INDENT_IGNORE = "E121,E122,E123,E124,E125,E126,E127,E128"
pep8:
	@TMPFILE=`mktemp` || exit 1; \
	pep8 --ignore E501,$(INDENT_IGNORE) --exclude ".#*" --repeat src $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

rpmlint:
	@TMPFILE=`mktemp` || exit 1; \
	rpmlint -f rpmlint.config subscription-manager.spec | grep -v "^.*packages and .* specfiles checked\;" | tee $$TMPFILE; \
	! test -s $$TMPFILE

versionlint:
	@TMPFILE=`mktemp` || exit 1; \
	pyqver2.py -m 2.7 -v  $(STYLEFILES) | grep -v hashlib | tee $$TMPFILE; \
	! test -s $$TMPFILE

.PHONY: stylish
stylish: versionlint gladelint find-missing-widgets find-missing-signals pyflakes whitespacelint pep8 gettext_lint rpmlint debuglint

jenkins: stylish coverage-jenkins


