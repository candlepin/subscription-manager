PREFIX ?= /
SYSCONF ?= etc
PYTHON ?= python

PKGDIR = /usr/share/rhsm/

PKGNAME = subscription-manager
VERSION = $(shell echo `grep ^Version: $(PKGNAME).spec | awk '{ print $$2 }'`)

%.pyc: %.py
	python -c "import py_compile; py_compile.compile('$<')"

rhsmcertd: src/rhsmcertd.c
	@mkdir -p bin
	cc $? -o bin/rhsmcertd

build:	rhsmcertd

install: 
	@mkdir -p ${PREFIX}/usr/share/rhsm/gui/data/icons/16x16
	@mkdir -p ${PREFIX}/usr/lib/yum-plugins/
	@mkdir -p ${PREFIX}/usr/sbin
	@mkdir -p ${PREFIX}/etc/rhsm
	@mkdir -p ${PREFIX}/etc/yum/pluginconf.d/
	@mkdir -p ${PREFIX}/usr/share/man/man8/
	@mkdir -p ${PREFIX}/var/log/rhsm
	@mkdir -p ${PREFIX}/usr/bin
	@mkdir -p ${PREFIX}/etc/init.d
	@mkdir -p ${PREFIX}/usr/share/icons/hicolor/16x16/apps
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
	cp bin/* ${PREFIX}/usr/bin
	cp src/rhsmcertd.init.d ${PREFIX}/etc/init.d/rhsmcertd
	cp man/* ${PREFIX}/usr/share/man/man8/

clean:
	rm -f *.pyc *.pyo *~ *.bak *.tar.gz

archive: clean
	@rm -rf ${PKGNAME}-%{VERSION}.tar.gz
	@rm -rf /tmp/${PKGNAME}-$(VERSION) /tmp/${PKGNAME}
	@dir=$$PWD; cd /tmp; cp -a $$dir ${PKGNAME}
	@rm -f /tmp/${PKGNAME}/${PKGNAME}-daily.spec
	@mv /tmp/${PKGNAME} /tmp/${PKGNAME}-$(VERSION)
	@dir=$$PWD; cd /tmp; tar cvzf $$dir/${PKGNAME}-$(VERSION).tar.gz --exclude \.svn ${PKGNAME}-$(VERSION)
	@rm -rf /tmp/${PKGNAME}-$(VERSION)	
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.gz"

rpm: archive
	rpmbuild -ta ${PKGNAME}-$(VERSION).tar.gz
