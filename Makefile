# Because our project includes some C artifacts like rhsmcertd, the standard
# Python setup.py doesn't cover all our bases.  Additionally, setuptools does not like
# to install files outside of /usr (see http://stackoverflow.com/a/13476594/6124862).
#
# Therefore the Makefile performs the main build, but please keep the following guidelines
# in mind when updating it:
#
# * If the file goes under /usr, put it in setup.py
# * Linting checks, etc. should be implemented in Python and invoked via setup.py
# * If functionality cannot be added to setup.py without extensive effort, place the
#   functionality in the Makefile.  Otherwise, add it to setup.py.
# * The ultimate goal is to have a clean build process so do things the best way, not
#   just the fastest or easiest way.

SHELL := /bin/bash
PYTHON ?= python
DESTDIR ?= /
PREFIX ?= /usr/local
SYSCONF ?= etc
INSTALL_DIR = $(PREFIX)/share
RUN_DIR ?= /run

OS = $(shell test -f /etc/os-release && source /etc/os-release; echo $$ID)
OS_DIST ?= $(shell rpm --eval='%dist')

PYTHON_VER ?= $(shell $(PYTHON) -c 'import sys; print("python%s.%s" % sys.version_info[:2])')

ifeq ($(OS_DIST), debian)
  PYTHON_SITELIB ?= $(PREFIX)/lib/$(PYTHON_VER)/site-packages
else
  PYTHON_SITELIB ?= $(PREFIX)/lib64/$(PYTHON_VER)/site-packages
endif
DNF_PLUGIN_PYTHON_SITELIB ?= $(PREFIX)/lib/$(PYTHON_VER)/site-packages
# Note the underscore used instead of a hyphen
PYTHON_INST_DIR = $(PYTHON_SITELIB)/subscription_manager

# Where various bits of code live in the git repo
SRC_DIR := src/subscription_manager
RCT_SRC_DIR := src/rct
DAEMONS_SRC_DIR := src/daemons
CONTENT_PLUGINS_SRC_DIR := src/content_plugins/

# dirs we install to
SYSTEMD_INST_DIR := $(PREFIX)/lib/systemd/system
RHSM_PLUGIN_DIR := $(PREFIX)/share/rhsm-plugins/
RHSM_PLUGIN_CONF_DIR := /etc/rhsm/pluginconf.d/
POLKIT_ACTIONS_INST_DIR := $(INSTALL_DIR)/polkit-1/actions
COMPLETION_DIR ?= $(INSTALL_DIR)/bash-completion/completions/
LIBEXEC_DIR ?= $(shell rpm --eval='%_libexecdir')

# If we skip install ostree plugin, unset by default
# override from spec file for rhel6
INSTALL_OSTREE_PLUGIN ?= true

# Container plugin should not be installed since RHEL 8. It is override
# from spec file
INSTALL_CONTAINER_PLUGIN ?= true

# for fc22 or newer
INSTALL_DNF_PLUGINS ?= false
DNF_PLUGINS_SRC_DIR := src/plugins

INSTALL_ZYPPER_PLUGINS ?= false

# sets a version that is more or less latest tag plus commit sha
VERSION ?= $(shell git describe | awk ' { sub(/subscription-manager-/,"")};1' )

# inherit from env if set so rpm can override
CFLAGS ?= -g -Wall
LDFLAGS ?=

RHSMCERTD_CFLAGS = `pkg-config --cflags glib-2.0`
RHSMCERTD_LDFLAGS = `pkg-config --libs glib-2.0`

PYFILES := `find src/ test/ -name "*.py"`
BIN_FILES := bin/subscription-manager \
			 bin/rct \
			 bin/rhsm-debug

STYLEFILES=$(PYFILES) $(BIN_FILES)

.DEFAULT_GOAL := build

build: rhsmcertd
	EXCLUDE_PACKAGES="$(EXCLUDE_PACKAGES)" $(PYTHON) ./setup.py clean --all
	EXCLUDE_PACKAGES="$(EXCLUDE_PACKAGES)" $(PYTHON) ./setup.py build --quiet --pkg-version=$(VERSION)

# we never "remake" this makefile, so add a target so
# we stop searching for implicit rules on how to remake it
Makefile: ;

.PHONY: clean
clean:
	rm -f *.pyc *.pyo *~ *.bak *.tar.gz
	rm -f bin/rhsmcertd
	$(PYTHON) ./setup.py clean --all
	rm -rf cover/ htmlcov/ build/ dist/

.PHONY: mkdir-bin
mkdir-bin:
	mkdir -p bin

rhsmcertd: mkdir-bin $(DAEMONS_SRC_DIR)/rhsmcertd.c
	$(CC) $(CFLAGS) $(RHSMCERTD_CFLAGS) -DLIBEXECDIR='"$(LIBEXEC_DIR)"' $(DAEMONS_SRC_DIR)/rhsmcertd.c -o bin/rhsmcertd $(LDFLAGS) $(RHSMCERTD_LDFLAGS)

.PHONY: check-syntax
check-syntax:
	$(CC) -fsyntax-only $(CFLAGS) $(LDFLAGS) `find -name '*.c'`

dbus-common-install:
	install -d $(DESTDIR)/etc/dbus-1/system.d
	install -d $(DESTDIR)/$(INSTALL_DIR)/dbus-1/system-services
	install -d $(DESTDIR)/$(LIBEXEC_DIR)
	install -d $(DESTDIR)/$(COMPLETION_DIR)

dbus-facts-service-install: dbus-common-install
	install -m 644 etc-conf/dbus/system.d/com.redhat.RHSM1.Facts.conf $(DESTDIR)/etc/dbus-1/system.d

dbus-main-service-install: dbus-common-install
	install -m 644 etc-conf/dbus/system.d/com.redhat.RHSM1.conf $(DESTDIR)/etc/dbus-1/system.d

.PHONY: dbus-install
dbus-install: dbus-facts-service-install dbus-main-service-install

.PHONY: install-conf
install-conf:
	install -d $(DESTDIR)/etc/{cron.daily,logrotate.d,pam.d,rhsm}
	install -d $(DESTDIR)/$(COMPLETION_DIR)
	install -d $(DESTDIR)/etc/rc.d/init.d
	install -d $(DESTDIR)/etc/init.d
	install -d $(DESTDIR)/etc/rhsm/{facts,syspurpose}
	install -d $(DESTDIR)/etc/security/console.apps
	install -m 644 etc-conf/rhsm.conf $(DESTDIR)/etc/rhsm/
	install -m 644 etc-conf/logrotate.conf $(DESTDIR)/etc/logrotate.d/subscription-manager
	install -m 644 etc-conf/subscription-manager.completion.sh $(DESTDIR)/$(COMPLETION_DIR)/subscription-manager
	install -m 644 etc-conf/rct.completion.sh $(DESTDIR)/$(COMPLETION_DIR)/rct
	install -m 644 etc-conf/rhsm-debug.completion.sh $(DESTDIR)/$(COMPLETION_DIR)/rhsm-debug
	install -m 644 etc-conf/rhsmcertd.completion.sh $(DESTDIR)/$(COMPLETION_DIR)/rhsmcertd
	install -d $(DESTDIR)/$(POLKIT_ACTIONS_INST_DIR)
	install -m 644 etc-conf/dbus/polkit/com.redhat.RHSM1.policy $(DESTDIR)/$(POLKIT_ACTIONS_INST_DIR)
	install -m 644 etc-conf/dbus/polkit/com.redhat.RHSM1.Facts.policy $(DESTDIR)/$(POLKIT_ACTIONS_INST_DIR)
	install -m 644 etc-conf/syspurpose/valid_fields.json $(DESTDIR)/etc/rhsm/syspurpose/valid_fields.json; \
	if [ "$(INSTALL_ZYPPER_PLUGINS)" = "true" ] ; then \
	    install -m 644 etc-conf/zypper.conf $(DESTDIR)/etc/rhsm/; \
	fi;

.PHONY: install-plugins
install-plugins:
	install -d $(DESTDIR)/$(RHSM_PLUGIN_DIR)
	install -d $(DESTDIR)/$(RHSM_PLUGIN_CONF_DIR)

	if [ "$(INSTALL_ZYPPER_PLUGINS)" = "true" ] ; then \
	  echo "Installing zypper plugins" ; \
		install -d $(DESTDIR)/etc/rhsm/zypper.repos.d ; \
		install -d $(DESTDIR)/$(PREFIX)/lib/zypp/plugins/services ; \
		install -m 755 -p src/plugins/zypper/services/* $(DESTDIR)/$(PREFIX)/lib/zypp/plugins/services ; \
	fi;

	if [ "$(INSTALL_DNF_PLUGINS)" = "true" ] ; then \
		echo "Installing DNF plugins" ; \
		install -d $(DESTDIR)/$(DNF_PLUGIN_PYTHON_SITELIB)/dnf-plugins/ ; \
		install -d $(DESTDIR)/etc/dnf/plugins/ ; \
		install -m 644 -p src/plugins/dnf/product_id.py \
		    $(DESTDIR)/$(DNF_PLUGIN_PYTHON_SITELIB)/dnf-plugins/product-id.py ; \
		install -m 644 -p src/plugins/dnf/subscription_manager.py \
		    $(DESTDIR)/$(DNF_PLUGIN_PYTHON_SITELIB)/dnf-plugins/subscription-manager.py ; \
		install -m 644 -p src/plugins/dnf/upload_profile.py \
		    $(DESTDIR)/$(DNF_PLUGIN_PYTHON_SITELIB)/dnf-plugins/upload-profile.py ; \
		install -m 644 etc-conf/plugin/product-id.conf $(DESTDIR)/etc/dnf/plugins/ ; \
		install -m 644 etc-conf/plugin/subscription-manager.conf $(DESTDIR)/etc/dnf/plugins/ ; \
	fi;

	# ostree stuff
	if [ "$(INSTALL_OSTREE_PLUGIN)" = "true" ] ; then \
		echo "Installing ostree plugins" ; \
		install -m 644 -p \
		$(CONTENT_PLUGINS_SRC_DIR)/ostree_content.OstreeContentPlugin.conf \
		$(DESTDIR)/$(RHSM_PLUGIN_CONF_DIR) ; \
		install -d $(DESTDIR)/$(PYTHON_INST_DIR)/plugin/ostree ; \
		install -m 644 -p $(SRC_DIR)/plugin/ostree/*.py $(DESTDIR)/$(PYTHON_INST_DIR)/plugin/ostree ; \
		install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/ostree_content.py $(DESTDIR)/$(RHSM_PLUGIN_DIR) ; \
	fi;

	# container stuff
	if [ "$(INSTALL_CONTAINER_PLUGIN)" = "true" ] ; then \
		echo "Installing container plugins" ; \
		install -m 644 -p \
			$(CONTENT_PLUGINS_SRC_DIR)/container_content.ContainerContentPlugin.conf \
			$(DESTDIR)/$(RHSM_PLUGIN_CONF_DIR) ; \
		install -m 644 $(CONTENT_PLUGINS_SRC_DIR)/container_content.py $(DESTDIR)/$(RHSM_PLUGIN_DIR) ;\
	fi;

.PHONY: install-example-plugins
install-example-plugins: install-plugins
	install -m 644 -p example-plugins/*.py $(DESTDIR)/$(RHSM_PLUGIN_DIR)
	install -m 644 -p example-plugins/*.conf $(DESTDIR)/$(RHSM_PLUGIN_CONF_DIR)

.PHONY: install-via-setup
install-via-setup: install-subpackages-via-setup
	EXCLUDE_PACKAGES="$(EXCLUDE_PACKAGES)" $(PYTHON) ./setup.py install --root $(DESTDIR) --pkg-version=$(VERSION) --prefix=$(PREFIX) \
	$(SETUP_PY_INSTALL_PARAMS)
	mkdir -p $(DESTDIR)/$(PREFIX)/sbin/
	mkdir -p $(DESTDIR)/$(LIBEXEC_DIR)/
	mv $(DESTDIR)/$(PREFIX)/bin/subscription-manager $(DESTDIR)/$(PREFIX)/sbin/
	mv $(DESTDIR)/$(PREFIX)/bin/rhsmcertd-worker $(DESTDIR)/$(LIBEXEC_DIR)/
	mv $(DESTDIR)/$(PREFIX)/bin/rhsm-service $(DESTDIR)/$(LIBEXEC_DIR)/
	mv $(DESTDIR)/$(PREFIX)/bin/rhsm-facts-service $(DESTDIR)/$(LIBEXEC_DIR)/
	mv $(DESTDIR)/$(PREFIX)/bin/rhsm-package-profile-uploader $(DESTDIR)/$(LIBEXEC_DIR)/
	find $(DESTDIR)/$(PYTHON_SITELIB) -name requires.txt -exec sed -i '/dbus-python/d' {} \;


.PHONY: install-subpackages-via-setup
install-subpackages-via-setup:
	for subpackage in $(SUBPACKAGES); \
	do \
	    pushd $$subpackage; \
	    $(PYTHON) ./setup.py install --root=$(DESTDIR) --prefix=$(PREFIX); \
		popd; \
	done;

.PHONY: install
install: install-via-setup install-files


.PHONY: install-files
install-files: dbus-install install-conf install-plugins
	install -d $(DESTDIR)/var/log/rhsm
	install -d $(DESTDIR)/var/spool/rhsm/debug
	install -d $(DESTDIR)${RUN_DIR}/rhsm
	install -d -m 750 $(DESTDIR)/var/lib/rhsm/{cache,facts,packages,repo_server_val}
	install -d -m 750 $(DESTDIR)/var/cache/cloud-what

	# Set up rhsmcertd daemon.
	install -d $(DESTDIR)/$(SYSTEMD_INST_DIR)
	install -d $(DESTDIR)/$(PREFIX)/lib/tmpfiles.d
	install -m 644 etc-conf/rhsmcertd.service $(DESTDIR)/$(SYSTEMD_INST_DIR)
	install -m 644 etc-conf/subscription-manager.conf.tmpfiles \
		$(DESTDIR)/$(PREFIX)/lib/tmpfiles.d/subscription-manager.conf

	# Install configuration file with system users and group (only rhsm group ATM)
	install -d $(DESTDIR)/$(PREFIX)/lib/sysusers.d
	install -m 644 etc-conf/rhsm-sysuser.conf $(DESTDIR)/$(PREFIX)/lib/sysusers.d/rhsm.conf

	if [ -f /etc/redhat-release ]; then \
		install -m 644 etc-conf/subscription-manager.pam $(DESTDIR)/etc/pam.d/subscription-manager; \
		install -m 644 etc-conf/subscription-manager.console $(DESTDIR)/etc/security/console.apps/subscription-manager; \
	fi; \

	install -m 755 bin/rhsmcertd $(DESTDIR)/$(PREFIX)/bin/rhsmcertd

.PHONY: check
check:
	pytest test/

.PHONY: version_check
version_check:
# needs https://github.com/alikins/pyqver
	-@TMPFILE=`mktemp` || exit 1; \
	pyqver2.py -v -m 2.5  $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

.PHONY: coverage
coverage:
ifdef ghprbPullId
	# Pull the PR id from the Jenkins environment and use it as a seed so that each PR
	# uses a consistant test ordering.
	$(PYTHON) -m coverage run -m pytest --randomly-seed=$(ghprbPullId) test/
else
	$(PYTHON) -m coverage run -m pytest test/
endif

.PHONY: gettext
gettext:
	# Extract strings from our source files. any comments on the line above
	# the string marked for translation beginning with "translators" will be
	# included in the pot file.
	$(PYTHON) ./setup.py gettext

.PHONY: update-po
update-po:
	$(PYTHON) ./setup.py update_trans

.PHONY: uniq-po
uniq-po:
	$(PYTHON) ./setup.py uniq_trans

# just run a check to make sure these compile
.PHONY: polint
polint:
	$(PYTHON) ./setup.py gettext --lint

.PHONY: just-strings
just-strings:
	-@ scripts/just_strings.py po/keys.pot

# do all the bits to find new strings to translate
.PHONY: translations
translations: gettext update-po
	echo "# pofiles should be ready to commit and push"

# generate a en_US.po with long strings for testing
gen-test-long-po:
	-@ scripts/gen_test_en_po.py --long po/en_US.po

.PHONY: lint
lint:
	$(PYTHON) ./setup.py lint

.PHONY: flake8
flake8:
	$(PYTHON) ./setup.py flake8

.PHONY: rpmlint
rpmlint:
	$(PYTHON) ./setup.py lint_rpm

.PHONY: stylish
stylish: lint

.PHONY: install-pip-requirements
install-pip-requirements:
	@pip install -I -r test-requirements.txt

.PHONY: jenkins
jenkins: install-pip-requirements build stylish coverage

.PHONY: set-versions
# Empty task retained for legacy compatibility with CI environment
set-versions: ;
