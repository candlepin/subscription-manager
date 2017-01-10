# Because our project includes some C artifacts like rhsmd and rhsm_icon, the standard
# Python setup.py doesn't cover all our bases.  Additionally, setuptools does not like
# to install files outside of /usr (see http://stackoverflow.com/a/13476594/6124862).
#
# Therefore the Makefile performs the master build, but please keep the following guidelines
# in mind when updating it:
#
# * If the file goes under /usr, put it in setup.py
# * Linting checks, etc. should be implemented in Python and invoked via setup.py
# * If functionality cannot be added to setup.py without extensive effort, place the
#   functionality in the Makefile.  Otherwise, add it to setup.py.
# * The ultimate goal is to have a clean build process so do things the best way, not
#   just the fastest or easiest way.

SHELL := /bin/bash
PREFIX ?= /
SYSCONF ?= etc
INSTALL_DIR = usr/share

OS = $(shell lsb_release -i | awk '{ print $$3 }' | awk -F. '{ print $$1}')
OS_VERSION = $(shell lsb_release -r | awk '{ print $$2 }' | awk -F. '{ print $$1}')
OS_DIST ?= $(shell rpm --eval='%dist')

PYTHON_VER ?= $(python -c 'import sys; print("python%s.%s" % sys.version_info[:2])')

PYTHON_SITELIB ?= usr/lib/$(PYTHON_VER)/site-packages
# Note the underscore used instead of a hyphen
PYTHON_INST_DIR = $(PREFIX)/$(PYTHON_SITELIB)/subscription_manager

# Where various bits of code live in the git repo
SRC_DIR := src/subscription_manager
RCT_SRC_DIR := src/rct
RHSM_ICON_SRC_DIR := src/rhsm_icon
DAEMONS_SRC_DIR := src/daemons
CONTENT_PLUGINS_SRC_DIR := src/content_plugins/

ANACONDA_ADDON_NAME = com_redhat_subscription_manager
ANACONDA_ADDON_MODULE_SRC_DIR := src/initial-setup/$(ANACONDA_ADDON_NAME)

# dirs we install to
SYSTEMD_INST_DIR := $(PREFIX)/usr/lib/systemd/system
RHSM_PLUGIN_DIR := $(PREFIX)/usr/share/rhsm-plugins/
RHSM_PLUGIN_CONF_DIR := $(PREFIX)/etc/rhsm/pluginconf.d/
ANACONDA_ADDON_INST_DIR := $(PREFIX)/usr/share/anaconda/addons
INITIAL_SETUP_INST_DIR := $(ANACONDA_ADDON_INST_DIR)/$(ANACONDA_ADDON_NAME)
POLKIT_ACTIONS_INST_DIR := $(PREFIX)/$(INSTALL_DIR)/polkit-1/actions
LIBEXEC_DIR ?= $(shell rpm --eval='%_libexecdir')

# If we skip install ostree plugin, unset by default
# override from spec file for rhel6
INSTALL_OSTREE_PLUGIN ?= true

# Default differences between el6 and el7
ifeq ($(OS_DIST),.el6)
   GTK_VERSION?=2
   FIRSTBOOT_MODULES_DIR?=$(PREFIX)/usr/share/rhn/up2date_client/firstboot
   INSTALL_FIRSTBOOT?=true
   INSTALL_INITIAL_SETUP?=false
   DBUS_SERVICE_FILE_TYPE?=dbus
else ifeq ($(OS),SUSE)
   GTK_VERSION?=2
   FIRSTBOOT_MODULES_DIR?=$(PREFIX)/usr/share/rhn/up2date_client/firstboot
   INSTALL_FIRSTBOOT?=true
   INSTALL_INITIAL_SETUP?=false
else
   GTK_VERSION?=3
   FIRSTBOOT_MODULES_DIR?=$(PREFIX)/usr/share/firstboot/modules
   INSTALL_FIRSTBOOT?=true
   INSTALL_INITIAL_SETUP?=true
   DBUS_SERVICE_FILE_TYPE?=systemd
endif

DBUS_SERVICES_CONF_INST_DIR := $(PREFIX)/usr/share/dbus-1/system-services
FACTS_INST_DBUS_SERVICE_FILE = $(DBUS_SERVICES_CONF_INST_DIR)/com.redhat.RHSM1.Facts.service
MAIN_INST_DBUS_SERVICE_FILE = $(DBUS_SERVICES_CONF_INST_DIR)/com.redhat.RHSM1.service
# TODO Ideally these service files would be installed by distutils, but the file we actually
# install depends on the distro we are using.  Add a --without-systemd or similar flag to the
# custom install_data class we have in setup.py
ifeq ($(DBUS_SERVICE_FILE_TYPE),dbus)
FACTS_SRC_DBUS_SERVICE_FILE = etc-conf/dbus/com.redhat.RHSM1.Facts.service-dbus
MAIN_SRC_DBUS_SERVICE_FILE = etc-conf/dbus/com.redhat.RHSM1.service-dbus
else
FACTS_SRC_DBUS_SERVICE_FILE = etc-conf/dbus/com.redhat.RHSM1.Facts.service
MAIN_SRC_DBUS_SERVICE_FILE = etc-conf/dbus/com.redhat.RHSM1.service
endif

# always true until fedora is just dnf
INSTALL_YUM_PLUGINS ?= true
YUM_PLUGINS_SRC_DIR := src/plugins

# for fc22 or newer
INSTALL_DNF_PLUGINS ?= false
DNF_PLUGINS_SRC_DIR := src/plugins

# sets a version that is more or less latest tag plus commit sha
VERSION ?= $(shell git describe | awk ' { sub(/subscription-manager-/,"")};1' )

# inherit from env if set so rpm can override
CFLAGS ?= -g -Wall
LDFLAGS ?=

RHSMCERTD_FLAGS = `pkg-config --cflags --libs glib-2.0`
ICON_FLAGS=`pkg-config --cflags --libs "gtk+-$(GTK_VERSION).0 libnotify gconf-2.0 dbus-glib-1"`

PYFILES := `find src/ test/ -name "*.py"`
BIN_FILES := bin/subscription-manager bin/subscription-manager-gui \
			 bin/rhn-migrate-classic-to-rhsm \
			 bin/rct \
			 bin/rhsm-debug
STYLEFILES=$(PYFILES) $(BIN_FILES)

.DEFAULT_GOAL := build

build: rhsmcertd rhsm-icon
# Install doesn't perform a build if it doesn't have too.  Best to clean out
# any cruft so developers don't end up install old builds.
	./setup.py clean --all
	./setup.py build --quiet --gtk-version=$(GTK_VERSION) --rpm-version=$(VERSION)

# we never "remake" this makefile, so add a target so
# we stop searching for implicit rules on how to remake it
Makefile: ;

.PHONY: clean
clean:
	rm -f *.pyc *.pyo *~ *.bak *.tar.gz
	rm -f bin/rhsmcertd
	rm -f bin/rhsm-icon
	./setup.py clean --all

rhsmcertd: $(DAEMONS_SRC_DIR)/rhsmcertd.c
	$(CC) $(CFLAGS) $(LDFLAGS) $(RHSMCERTD_FLAGS) $(DAEMONS_SRC_DIR)/rhsmcertd.c -o bin/rhsmcertd

rhsm-icon: $(RHSM_ICON_SRC_DIR)/rhsm_icon.c
	$(CC) $(CFLAGS) $(LDFLAGS) $(ICON_FLAGS) $(RHSM_ICON_SRC_DIR)/rhsm_icon.c -o bin/rhsm-icon

.PHONY: check-syntax
check-syntax:
	$(CC) -fsyntax-only $(CFLAGS) $(LDFLAGS) $(ICON_FLAGS) `find -name '*.c'`

dbus-common-install:
	install -d $(PREFIX)/etc/dbus-1/system.d
	if [ "$(DBUS_SERVICE_FILE_TYPE)" == "systemd" ]; then \
		install -d $(SYSTEMD_INST_DIR) ; \
	fi
	install -d $(PREFIX)/$(INSTALL_DIR)/dbus-1/system-services
	install -d $(PREFIX)/$(LIBEXEC_DIR)
	install -d $(PREFIX)/etc/bash_completion.d

dbus-rhsmd-service-install: dbus-common-install
	install -m 644 etc-conf/dbus/com.redhat.SubscriptionManager.conf $(PREFIX)/etc/dbus-1/system.d
	install -m 644 etc-conf/dbus/com.redhat.SubscriptionManager.service $(PREFIX)/$(INSTALL_DIR)/dbus-1/system-services
	install -m 744 $(DAEMONS_SRC_DIR)/rhsm_d.py $(PREFIX)/$(LIBEXEC_DIR)/rhsmd

dbus-facts-service-install: dbus-common-install
	install -m 644 etc-conf/dbus/com.redhat.RHSM1.Facts.conf $(PREFIX)/etc/dbus-1/system.d
	if [ "$(DBUS_SERVICE_FILE_TYPE)" == "systemd" ]; then \
		install -m 644 etc-conf/dbus/rhsm-facts.service $(SYSTEMD_INST_DIR) ; \
	fi
	install -m 644 $(FACTS_SRC_DBUS_SERVICE_FILE) $(FACTS_INST_DBUS_SERVICE_FILE)

dbus-main-service-install: dbus-common-install
	install -m 644 etc-conf/dbus/com.redhat.RHSM1.conf $(PREFIX)/etc/dbus-1/system.d
	if [ "$(DBUS_SERVICE_FILE_TYPE)" == "systemd" ]; then \
		install -m 644 etc-conf/dbus/rhsm.service $(SYSTEMD_INST_DIR) ; \
	fi
	install -m 644 $(MAIN_SRC_DBUS_SERVICE_FILE) $(MAIN_INST_DBUS_SERVICE_FILE)

.PHONY: dbus-install
dbus-install: dbus-facts-service-install dbus-rhsmd-service-install dbus-main-service-install

.PHONY: install-conf
install-conf:
	install -d $(PREFIX)/etc/{cron.daily,logrotate.d,pam.d,bash_completion.d,rhsm}
	install -d $(PREFIX)/etc/rc.d/init.d
	install -d $(PREFIX)/etc/init.d
	install -d $(PREFIX)/etc/rhsm/facts
	install -d $(PREFIX)/etc/security/console.apps
	install -m 644 etc-conf/rhsm.conf $(PREFIX)/etc/rhsm/
	install -T etc-conf/logging.conf $(PREFIX)/etc/rhsm/logging.conf
	install -m 644 etc-conf/logrotate.conf $(PREFIX)/etc/logrotate.d/subscription-manager
	install -m 644 etc-conf/subscription-manager.completion.sh $(PREFIX)/etc/bash_completion.d/subscription-manager
	install -m 644 etc-conf/rct.completion.sh $(PREFIX)/etc/bash_completion.d/rct
	install -m 644 etc-conf/rhsm-debug.completion.sh $(PREFIX)/etc/bash_completion.d/rhsm-debug
	install -m 644 etc-conf/rhn-migrate-classic-to-rhsm.completion.sh $(PREFIX)/etc/bash_completion.d/rhn-migrate-classic-to-rhsm
	install -m 644 etc-conf/subscription-manager-gui.completion.sh $(PREFIX)/etc/bash_completion.d/subscription-manager-gui
	install -m 644 etc-conf/rhsm-icon.completion.sh $(PREFIX)/etc/bash_completion.d/rhsm-icon
	install -m 644 etc-conf/rhsmcertd.completion.sh $(PREFIX)/etc/bash_completion.d/rhsmcertd
	install -d $(PREFIX)/usr/share/appdata
	install -m 644 etc-conf/subscription-manager-gui.appdata.xml $(PREFIX)/$(INSTALL_DIR)/appdata/subscription-manager-gui.appdata.xml
	install -d $(POLKIT_ACTIONS_INST_DIR)
	install -m 644 etc-conf/dbus/com.redhat.RHSM1.policy $(POLKIT_ACTIONS_INST_DIR)
	install -m 644 etc-conf/dbus/com.redhat.RHSM1.Facts.policy $(POLKIT_ACTIONS_INST_DIR)

.PHONY: install-plugins
install-plugins:
	install -d $(RHSM_PLUGIN_DIR)
	install -d $(RHSM_PLUGIN_CONF_DIR)
	install -d $(PREFIX)/etc/rhsm/ca
	install -m 644 -p etc-conf/redhat-entitlement-authority.pem $(PREFIX)/etc/rhsm/ca/redhat-entitlement-authority.pem

	if [ "$(INSTALL_YUM_PLUGINS)" = "true" ] ; then \
		echo "Installing Yum plugins" ; \
		install -d $(PREFIX)/etc/yum/pluginconf.d/ ; \
		install -d $(PREFIX)/usr/lib/yum-plugins/ ; \
		install -m 644 -p src/plugins/*.py $(PREFIX)/usr/lib/yum-plugins/ ; \
		install -m 644 etc-conf/plugin/*.conf $(PREFIX)/etc/yum/pluginconf.d/ ; \
	fi;

	if [ "$(INSTALL_DNF_PLUGINS)" = "true" ] ; then \
		echo "Installing DNF plugins" ; \
		install -d $(PREFIX)/$(PYTHON_SITELIB)/dnf-plugins/ ; \
		install -m 644 -p src/dnf-plugins/*.py $(PREFIX)/$(PYTHON_SITELIB)/dnf-plugins/ ; \
	fi;

	# ostree stuff
	if [ "$(INSTALL_OSTREE_PLUGIN)" = "true" ] ; then \
		echo "Installing ostree plugins" ; \
		install -m 644 -p \
		$(CONTENT_PLUGINS_SRC_DIR)/ostree_content.OstreeContentPlugin.conf \
		$(RHSM_PLUGIN_CONF_DIR) ; \
		install -d $(PYTHON_INST_DIR)/plugin/ostree ; \
		install -m 644 -p $(SRC_DIR)/plugin/ostree/*.py $(PYTHON_INST_DIR)/plugin/ostree ; \
	fi;

	# container stuff
	install -m 644 -p \
		$(CONTENT_PLUGINS_SRC_DIR)/container_content.ContainerContentPlugin.conf \
		$(RHSM_PLUGIN_CONF_DIR)
	install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/container_content.py $(RHSM_PLUGIN_DIR)

.PHONY: install-ga
ifeq ($(GTK_VERSION),2)
install-ga:
	$(info Using GTK $(GTK_VERSION))
	install -d $(PYTHON_INST_DIR)/ga_impls/ga_gtk2
	install -m 644 -p $(SRC_DIR)/ga_impls/__init__.py* $(PYTHON_INST_DIR)/ga_impls
	install -m 644 -p $(SRC_DIR)/ga_impls/ga_gtk2/*.py $(PYTHON_INST_DIR)/ga_impls/ga_gtk2
else
install-ga:
	$(info Using GTK $(GTK_VERSION))
	install -d $(PYTHON_INST_DIR)/ga_impls
	install -m 644 -p $(SRC_DIR)/ga_impls/__init__.py* $(PYTHON_INST_DIR)/ga_impls
	install -m 644 -p $(SRC_DIR)/ga_impls/ga_gtk3.py* $(PYTHON_INST_DIR)/ga_impls
endif

.PHONY: install-example-plugins
install-example-plugins: install-plugins
	install -m 644 -p example-plugins/*.py $(RHSM_PLUGIN_DIR)
	install -m 644 -p example-plugins/*.conf $(RHSM_PLUGIN_CONF_DIR)

.PHONY: install-firstboot
ifeq ($(INSTALL_FIRSTBOOT),true)
install-firstboot:
	$(info Installing firstboot to $(FIRSTBOOT_MODULES_DIR))
	install -d $(FIRSTBOOT_MODULES_DIR)
	install -m 644 $(SRC_DIR)/gui/firstboot/*.py* $(FIRSTBOOT_MODULES_DIR)
else
install-firstboot:
	# Override INSTALL_FIRSTBOOT variable on command line if needed
	$(info firstboot is not configured to be install)
endif

# initial-setup, as in the 'initial-setup' rpm that runs at first boot.
.PHONY: install-initial-setup
ifeq ($(INSTALL_INITIAL_SETUP),true)
install-initial-setup:
	$(info Installing initial-setup to $(INITIAL_SETUP_INST_DIR))
	install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/ostree_content.py $(RHSM_PLUGIN_DIR)
	install -d $(ANACONDA_ADDON_INST_DIR)
	install -d $(INITIAL_SETUP_INST_DIR)/gui/spokes
	install -d $(INITIAL_SETUP_INST_DIR)/{categories,ks}
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/*.py $(INITIAL_SETUP_INST_DIR)/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/gui/*.py $(INITIAL_SETUP_INST_DIR)/gui/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/categories/*.py $(INITIAL_SETUP_INST_DIR)/categories/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/gui/spokes/{*.py,*.ui} $(INITIAL_SETUP_INST_DIR)/gui/spokes/
	install -m 644 -p $(ANACONDA_ADDON_MODULE_SRC_DIR)/ks/*.py $(INITIAL_SETUP_INST_DIR)/ks/
else
install-initial-setup:
	# Set INSTALL_INITIAL_SETUP variable on command line if needed.
	$(info initial-setup is not configured to be installed)
endif

.PHONY: install-post-boot
install-post-boot: install-firstboot install-initial-setup

.PHONY: install-via-setup
install-via-setup:
	./setup.py install --root $(PREFIX) --gtk-version=$(GTK_VERSION) --rpm-version=$(VERSION)

.PHONY: install
install: install-via-setup install-files

.PHONY: install-files
install-files: dbus-install install-conf install-plugins install-post-boot install-ga
	install -d $(PREFIX)/var/log/rhsm
	install -d $(PREFIX)/var/spool/rhsm/debug
	install -d $(PREFIX)/var/run/rhsm
	install -d -m 750 $(PREFIX)/var/lib/rhsm/{cache,facts,packages}

	# Set up rhsmcertd daemon. If installing on Fedora or RHEL 7+
	# we prefer systemd over sysv as this is the new trend.
	if [ $(OS) = Fedora ] ; then \
		install -d $(PREFIX)/usr/lib/tmpfiles.d; \
		install etc-conf/rhsmcertd.service $(SYSTEMD_INST_DIR); \
		install etc-conf/subscription-manager.conf.tmpfiles \
			$(PREFIX)/usr/lib/tmpfiles.d/subscription-manager.conf; \
	elif [ $(OS) = SUSE ] ;then \
		if [ $(OS_VERSION) -lt 12 ]; then \
			install etc-conf/rhsmcertd.init.d \
				$(PREFIX)/etc/init.d/rhsmcertd; \
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
			install -d $(PREFIX)/usr/lib/tmpfiles.d; \
			install etc-conf/rhsmcertd.service $(SYSTEMD_INST_DIR); \
			install etc-conf/subscription-manager.conf.tmpfiles \
				$(PREFIX)/usr/lib/tmpfiles.d/subscription-manager.conf; \
		fi; \
	fi; \

	install -m 700 etc-conf/rhsmd.cron $(PREFIX)/etc/cron.daily/rhsmd

	# SUSE Linux does not make use of consolehelper
	if [ $(OS) != SUSE ] ;then \
		ln -sf /usr/bin/consolehelper $(PREFIX)/usr/bin/subscription-manager-gui; \
		ln -sf /usr/bin/consolehelper $(PREFIX)/usr/bin/subscription-manager; \
		\
		install -m 644 etc-conf/subscription-manager-gui.pam $(PREFIX)/etc/pam.d/subscription-manager-gui; \
		install -m 644 etc-conf/subscription-manager.pam $(PREFIX)/etc/pam.d/subscription-manager; \
		\
		install -m 644 etc-conf/subscription-manager-gui.console $(PREFIX)/etc/security/console.apps/subscription-manager-gui; \
		install -m 644 etc-conf/subscription-manager.console $(PREFIX)/etc/security/console.apps/subscription-manager; \
	fi; \

	install -m 755 bin/rhsm-icon $(PREFIX)/usr/bin/rhsm-icon
	install -m 755 bin/rhsmcertd $(PREFIX)/usr/bin/rhsmcertd

.PHONY: check
check:
	python setup.py -q nosetests -c playpen/noserc.dev

.PHONY: coverage
coverage:
ifdef ghprbPullId
	# Pull the PR id from the Jenkins environment and use it as a seed so that each PR
	# uses a consistant test ordering.
	./setup.py -q nosetests --randomly-seed=$(ghprbPullId) -c playpen/noserc.ci
else
	./setup.py -q nosetests -c playpen/noserc.ci
endif

.PHONY: gettext
gettext:
	# Extract strings from our source files. any comments on the line above
	# the string marked for translation beginning with "translators" will be
	# included in the pot file.
	./setup.py gettext

.PHONY: update-po
update-po:
	./setup.py update_trans

.PHONY: uniq-po
uniq-po:
	./setup.py uniq_trans

# just run a check to make sure these compile
.PHONY: polint
polint:
	./setup.py gettext --lint

.PHONY: just-strings
just-strings:
	-@ scripts/just_strings.py po/keys.pot

.PHONY: zanata-pull
zanata-pull:
	pushd po && zanata pull --transdir . && popd

.PHONY: zanata-push
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
.PHONY: zanata
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

.PHONY: stylish
stylish: lint

.PHONY: install-pip-requirements
install-pip-requirements:
	@pip install -r test-requirements.txt

.PHONY: jenkins
jenkins: install-pip-requirements build stylish coverage

.PHONY: set-versions
# Empty task retained for legacy compatibility with CI environment
set-versions: ;
