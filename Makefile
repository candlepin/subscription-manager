SHELL := /bin/bash
PREFIX ?=
SYSCONF ?= etc
PYTHON_SITELIB ?= usr/lib/python2.7/site-packages

INSTALL_DIR = usr/share
INSTALL_MODULE = rhsm
PKGNAME = subscription_manager
ANACONDA_ADDON_NAME = com_redhat_subscription_manager

# where most of our python modules live. Note this is not on
# the default python system path. If you are importing modules from here, and
# you can't commit to this repo, you should feel bad and stop doing that.
PYTHON_INST_DIR = $(PREFIX)/$(PYTHON_SITELIB)/$(PKGNAME)

OS = $(shell lsb_release -i | awk '{ print $$3 }' | awk -F. '{ print $$1}')
OS_VERSION = $(shell lsb_release -r | awk '{ print $$2 }' | awk -F. '{ print $$1}')
OS_DIST ?= $(shell rpm --eval='%dist')
BIN_FILES := bin/subscription-manager bin/subscription-manager-gui \
			 bin/rhn-migrate-classic-to-rhsm \
			 bin/rct \
			 bin/rhsm-debug

# Where various bits of code live in the git repo
BASE_SRC_DIR := src
SRC_DIR := $(BASE_SRC_DIR)/subscription_manager
RCT_SRC_DIR := $(BASE_SRC_DIR)/rct
RD_SRC_DIR := $(BASE_SRC_DIR)/rhsm_debug
RHSM_ICON_SRC_DIR := $(BASE_SRC_DIR)/rhsm_icon
DAEMONS_SRC_DIR := $(BASE_SRC_DIR)/daemons
EXAMPLE_PLUGINS_SRC_DIR := example-plugins/
CONTENT_PLUGINS_SRC_DIR := $(BASE_SRC_DIR)/content_plugins/
ANACONDA_ADDON_SRC_DIR := $(BASE_SRC_DIR)/initial-setup
ANACONDA_ADDON_MODULE_SRC_DIR := $(ANACONDA_ADDON_SRC_DIR)/$(ANACONDA_ADDON_NAME)

# dirs we install to
SYSTEMD_INST_DIR := $(PREFIX)/usr/lib/systemd/system
RHSM_PLUGIN_DIR := $(PREFIX)/usr/share/rhsm-plugins/
RHSM_PLUGIN_CONF_DIR := $(PREFIX)/etc/rhsm/pluginconf.d/
ANACONDA_ADDON_INST_DIR := $(PREFIX)/usr/share/anaconda/addons
INITIAL_SETUP_INST_DIR := $(ANACONDA_ADDON_INST_DIR)/$(ANACONDA_ADDON_NAME)

# If we skip install ostree plugin, unset by default
# override from spec file for rhel6
INSTALL_OSTREE_PLUGIN ?= true

# Default differences between el6 and el7
ifeq ($(OS_DIST),.el6)
   GTK_VERSION?=2
   FIRSTBOOT_MODULES_DIR?=$(PREFIX)/usr/share/rhn/up2date_client/firstboot
   INSTALL_FIRSTBOOT?=true
   INSTALL_INITIAL_SETUP?=false
else
   GTK_VERSION?=3
   FIRSTBOOT_MODULES_DIR?=$(PREFIX)/usr/share/firstboot/modules
   INSTALL_FIRSTBOOT?=true
   INSTALL_INITIAL_SETUP?=true
endif

# always true until fedora is just dnf
INSTALL_YUM_PLUGINS ?= true
YUM_PLUGINS_SRC_DIR := $(BASE_SRC_DIR)/plugins

# for fc22 or newer
INSTALL_DNF_PLUGINS ?= false
DNF_PLUGINS_SRC_DIR := $(BASE_SRC_DIR)/plugins

ALL_SRC_DIRS := $(SRC_DIR) $(RCT_SRC_DIR) $(RD_SRC_DIR) $(DAEMONS_SRC_DIR) $(CONTENT_PLUGINS_SRC_DIR) $(EXAMPLE_PLUGINS_SRC_DIR) $(YUM_PLUGINS_SRC_DIR) $(DNF_PLUGINS_SRC_DIR)

# sets a version that is more or less latest tag plus commit sha
VERSION ?= $(shell git describe | awk ' { sub(/subscription-manager-/,"")};1' )

# inherit from env if set so rpm can override
CFLAGS ?= -g -Wall
LDFLAGS ?=

build: set-versions rhsmcertd rhsm-icon
	./setup.py build

# we never "remake" this makefile, so add a target so
# we stop searching for implicit rules on how to remake it
Makefile: ;

clean: clean-versions
	rm -f *.pyc *.pyo *~ *.bak *.tar.gz
	rm -f bin/rhsmcertd
	rm -f bin/rhsm-icon
	./setup.py clean --all

bin:
	mkdir bin

RHSMCERTD_FLAGS = `pkg-config --cflags --libs glib-2.0`

ICON_FLAGS=`pkg-config --cflags --libs "gtk+-$(GTK_VERSION).0 libnotify gconf-2.0 dbus-glib-1"`

PYFILES := `find $(ALL_SRC_DIRS) -name "*.py"`
# Ignore certdata.py from style checks as tabs and trailing
# whitespace are required for testing.
TESTFILES=`find  test/ \( ! -name certdata.py ! -name manifestdata.py \) -name "*.py"`
STYLEFILES=$(PYFILES) $(BIN_FILES) $(TESTFILES)

rhsmcertd: $(DAEMONS_SRC_DIR)/rhsmcertd.c bin
	$(CC) $(CFLAGS) $(LDFLAGS) $(RHSMCERTD_FLAGS) $(DAEMONS_SRC_DIR)/rhsmcertd.c -o bin/rhsmcertd

check-syntax:
	$(CC) $(CFLAGS) $(LDFLAGS) $(ICON_FLAGS) -o nul -S $(CHK_SOURCES)

rhsm-icon: $(RHSM_ICON_SRC_DIR)/rhsm_icon.c bin
	$(CC) $(CFLAGS) $(LDFLAGS) $(ICON_FLAGS) $(RHSM_ICON_SRC_DIR)/rhsm_icon.c -o bin/rhsm-icon

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
	install -T etc-conf/logging.conf $(PREFIX)/etc/rhsm/logging.conf
	install etc-conf/plugin/*.conf $(PREFIX)/etc/yum/pluginconf.d/
	install -m 644 etc-conf/subscription-manager.completion.sh $(PREFIX)/etc/bash_completion.d/subscription-manager
	install -m 644 etc-conf/rct.completion.sh $(PREFIX)/etc/bash_completion.d/rct
	install -m 644 etc-conf/rhsm-debug.completion.sh $(PREFIX)/etc/bash_completion.d/rhsm-debug
	install -m 644 etc-conf/rhn-migrate-classic-to-rhsm.completion.sh $(PREFIX)/etc/bash_completion.d/rhn-migrate-classic-to-rhsm
	install -m 644 etc-conf/rhsm-icon.completion.sh $(PREFIX)/etc/bash_completion.d/rhsm-icon
	install -m 644 etc-conf/rhsmcertd.completion.sh $(PREFIX)/etc/bash_completion.d/rhsmcertd
	install -m 644 etc-conf/subscription-manager-gui.appdata.xml $(PREFIX)/$(INSTALL_DIR)/appdata/subscription-manager-gui.appdata.xml

install-content-plugin-ostree:
	if [ "$(INSTALL_OSTREE_PLUGIN)" = "true" ] ; then \
		install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/ostree_content.py $(RHSM_PLUGIN_DIR) ; \
	fi;

install-content-plugins-conf-ostree:
	if [ "$(INSTALL_OSTREE_PLUGIN)" = "true" ] ; then \
		install -m 644 -p \
		$(CONTENT_PLUGINS_SRC_DIR)/ostree_content.OstreeContentPlugin.conf \
		$(RHSM_PLUGIN_CONF_DIR) ; \
	fi;

install-content-plugin-container:
	install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/container_content.py $(RHSM_PLUGIN_DIR)

install-content-plugins-conf-container:
	install -m 644 -p \
		$(CONTENT_PLUGINS_SRC_DIR)/container_content.ContainerContentPlugin.conf \
		$(RHSM_PLUGIN_CONF_DIR)

install-content-plugins-dir:
	install -d $(RHSM_PLUGIN_DIR)

install-content-plugins-conf-dir:
	install -d $(RHSM_PLUGIN_CONF_DIR)

install-content-plugins-ca:
	install -d $(PREFIX)/etc/rhsm/ca
	install -m 644 -p etc-conf/redhat-entitlement-authority.pem $(PREFIX)/etc/rhsm/ca/redhat-entitlement-authority.pem

install-content-plugins-conf: install-content-plugins-conf-dir install-content-plugins-conf-ostree install-content-plugins-conf-container install-content-plugins-ca

install-content-plugins: install-content-plugins-dir install-content-plugin-ostree install-content-plugin-container

install-plugins-conf-dir:
	install -d $(RHSM_PLUGIN_CONF_DIR)

install-plugins-conf: install-plugins-conf-dir install-content-plugins-conf

install-plugins-dir:
	install -d $(RHSM_PLUGIN_DIR)

install-plugins: install-plugins-dir install-content-plugins

.PHONY: install-ga-dir
install-ga-dir:
	install -d $(PYTHON_INST_DIR)/ga_impls

# Install our gtk2/gtk3 compat modules
# just the gtk3 stuff
.PHONY: install-ga-gtk3
install-ga-gtk3: install-ga-dir
	install -m 644 -p $(SRC_DIR)/ga_impls/__init__.py* $(PYTHON_INST_DIR)/ga_impls
	install -m 644 -p $(SRC_DIR)/ga_impls/ga_gtk3.py* $(PYTHON_INST_DIR)/ga_impls

.PHONY: install-ga-gtk2
install-ga-gtk2: install-ga-dir
	install -d $(PYTHON_INST_DIR)/ga_impls/ga_gtk2
	install -m 644 -p $(SRC_DIR)/ga_impls/__init__.py* $(PYTHON_INST_DIR)/ga_impls
	install -m 644 -p $(SRC_DIR)/ga_impls/ga_gtk2/*.py $(PYTHON_INST_DIR)/ga_impls/ga_gtk2

.PHONY: install-ga
ifeq ($(GTK_VERSION),2)
 install-ga: install-ga-gtk2
else
 install-ga: install-ga-gtk3
endif

.PHONY: install-example-plugins
install-example-plugins:
	install -d $(RHSM_PLUGIN_DIR)
	install -m 644 -p $(EXAMPLE_PLUGINS_SRC_DIR)/*.py $(RHSM_PLUGIN_DIR)
	install -d $(RHSM_PLUGIN_CONF_DIR)
	install -m 644 -p $(EXAMPLE_PLUGINS_SRC_DIR)/*.conf $(RHSM_PLUGIN_CONF_DIR)

# initial-setup, as in the 'initial-setup' rpm that runs at first boot.
.PHONY: install-initial-setup-real
install-initial-setup-real:
	echo "installing initial-setup" ; \
	install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/ostree_content.py $(RHSM_PLUGIN_DIR)
	install -d $(ANACONDA_ADDON_INST_DIR)
	install -d $(INITIAL_SETUP_INST_DIR)
	install -d $(INITIAL_SETUP_INST_DIR)/gui
	install -d $(INITIAL_SETUP_INST_DIR)/gui/spokes
	install -d $(INITIAL_SETUP_INST_DIR)/categories
	install -d $(INITIAL_SETUP_INST_DIR)/ks
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/*.py $(INITIAL_SETUP_INST_DIR)/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/gui/*.py $(INITIAL_SETUP_INST_DIR)/gui/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/categories/*.py $(INITIAL_SETUP_INST_DIR)/categories/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/gui/spokes/*.py $(INITIAL_SETUP_INST_DIR)/gui/spokes/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/gui/spokes/*.ui $(INITIAL_SETUP_INST_DIR)/gui/spokes/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/ks/*.py $(INITIAL_SETUP_INST_DIR)/ks/

.PHONY: install-firstboot-real
install-firstboot-real:
	echo "Installing firstboot to $(FIRSTBOOT_MODULES_DIR)"; \
	install -d $(FIRSTBOOT_MODULES_DIR); \
	install -m644 $(SRC_DIR)/gui/firstboot/*.py* $(FIRSTBOOT_MODULES_DIR)/;\

.PHONY: install-firstboot
ifeq ($(INSTALL_FIRSTBOOT),true)
install-firstboot: install-firstboot-real
else
install-firstboot: ;
endif

.PHONY: install-initial-setup
ifeq ($(INSTALL_INITIAL_SETUP),true)
install-initial-setup: install-initial-setup-real
else
install-initial-setup: ;
endif

.PHONY: install-post-boot
install-post-boot: install-firstboot install-initial-setup

.PHONY: install-via-setup
install-via-setup:
	./setup.py install --root $(PREFIX)

.PHONY: install
install: install-via-setup install-files install-conf install-plugins-conf

set-versions:
	sed -e 's/RPM_VERSION/$(VERSION)/g' -e 's/GTK_VERSION/$(GTK_VERSION)/g' $(SRC_DIR)/version.py.in > $(SRC_DIR)/version.py
	sed -e 's/RPM_VERSION/$(VERSION)/g' $(RCT_SRC_DIR)/version.py.in > $(RCT_SRC_DIR)/version.py

clean-versions:
	rm -rf $(SRC_DIR)/version.py
	rm -rf $(RCT_SRC_DIR)/version.py

install-files: set-versions dbus-service-install install-plugins install-post-boot install-ga
	install -d $(PYTHON_INST_DIR)/plugin/ostree
	install -d $(PYTHON_INST_DIR)/firstboot
	install -d $(PREFIX)/etc/rc.d/init.d
	install -d $(PREFIX)/etc/rhsm/facts
	install -d $(PREFIX)/etc/cron.daily
	install -d $(PREFIX)/etc/pam.d
	install -d $(PREFIX)/etc/logrotate.d
	install -d $(PREFIX)/etc/security/console.apps
	install -d $(PREFIX)/var/log/rhsm
	install -d $(PREFIX)/var/spool/rhsm/debug
	install -d $(PREFIX)/var/run/rhsm
	install -d $(PREFIX)/var/lib/rhsm/facts
	install -d $(PREFIX)/var/lib/rhsm/packages
	install -d $(PREFIX)/var/lib/rhsm/cache
	install -d $(PREFIX)/usr/share/appdata

	install -m 644 etc-conf/subscription-manager-gui.completion.sh $(PREFIX)/etc/bash_completion.d/subscription-manager-gui

	if [ "$(INSTALL_OSTREE_PLUGIN)" = "true" ] ; then \
		install -m 644 -p $(SRC_DIR)/plugin/ostree/*.py $(PYTHON_INST_DIR)/plugin/ostree ; \
	fi
	if [ "$(INSTALL_YUM_PLUGINS)" = "true" ] ; then \
		echo "YUM" ; \
		install -d $(PREFIX)/etc/yum/pluginconf.d/ ; \
		install -d $(PREFIX)/usr/lib/yum-plugins/ ; \
		install -m 644 -p src/plugins/*.py $(PREFIX)/usr/lib/yum-plugins/ ; \
	fi ; \
	if [ "$(INSTALL_DNF_PLUGINS)" = "true" ] ; then \
		echo "DNF" ; \
		install -d $(PREFIX)/$(PYTHON_SITELIB)/dnf-plugins/ ; \
		install -m 644 -p src/dnf-plugins/*.py $(PREFIX)/$(PYTHON_SITELIB)/dnf-plugins/ ; \
	fi ; \

	# Set up rhsmcertd daemon. If installing on Fedora or RHEL 7+
	# we prefer systemd over sysv as this is the new trend.
	if [ $(OS) = Fedora ] ; then \
		install -d $(SYSTEMD_INST_DIR); \
		install -d $(PREFIX)/usr/lib/tmpfiles.d; \
		install etc-conf/rhsmcertd.service $(SYSTEMD_INST_DIR); \
		install etc-conf/subscription-manager.conf.tmpfiles \
			$(PREFIX)/usr/lib/tmpfiles.d/subscription-manager.conf; \
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

	install -m 700 etc-conf/rhsmd.cron $(PREFIX)/etc/cron.daily/rhsmd

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

	install -m 755 bin/rhsm-icon $(PREFIX)/usr/bin/rhsm-icon
	install -m 755 bin/rhsmcertd $(PREFIX)/usr/bin/rhsmcertd

check:
	python setup.py -q nosetests -c playpen/noserc.dev

smoke:
	test/smoke.sh

coverage: coverage-jenkins

coverage-html: coverage-jenkins

.PHONY: coverage-jenkins
coverage-jenkins:
	./setup.py -q nosetests -c playpen/noserc.ci

gettext:
	# Extract strings from our source files. any comments on the line above
	# the string marked for translation beginning with "translators" will be
	# included in the pot file.
	./setup.py gettext

update-po:
	./setup.py update_trans

uniq-po:
	./setup.py uniq_trans

# just run a check to make sure these compile
polint:
	./setup.py gettext --lint

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

.PHONY: lint
lint:
	./setup.py lint

.PHONY: flake8
flake8:
	./setup.py flake8

.PHONY: rpmlint
rpmlint:
	./setup.py lint_rpm

# We target python 2.6, hence -m 2.7 is the earliest python features to warn about use of.
# See https://github.com/alikins/pyqver for pyqver.
# Since plugin/ostree is for python 2.7+ systems only, we can ignore the warning there.
.PHONY: versionlint
versionlint:
	@TMPFILE=`mktemp` || exit 1; \
	pyqver2.py -m 2.7 -l $(STYLEFILES) | grep -v hashlib | grep -v plugin/ostree.*check_output | tee $$TMPFILE; \
	! test -s $$TMPFILE

.PHONY: stylish
stylish: lint versionlint

.PHONY: install-pip-requirements
install-pip-requirements:
	@pip install -r test-requirements.txt

.PHONY: jenkins
jenkins: install-pip-requirements build stylish coverage-jenkins
