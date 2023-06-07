# one example file in src/lib to check if it was already checked out
LIB_TEST=src/lib/cockpit-po-plugin.js

all: $(LIB_TEST)
	NODE_ENV=$(NODE_ENV) npm run build

clean:
	rm -rf dist/
	rm -rf _install

install: all
	mkdir -p /usr/share/cockpit/subscription-manager
	cp -r dist/* /usr/share/cockpit/subscription-manager

# when building a distribution tarball, call webpack with a 'production' environment
dist-gzip: NODE_ENV=production
dist-gzip: clean all
	mkdir -p _install/usr/share/cockpit
	cp -r dist/ _install/usr/share/cockpit/subscription-manager
	mkdir -p _install/usr/share/metainfo/
	cp *.metainfo.xml _install/usr/share/metainfo/
	(cd _install; find -type f) | tar -C _install/ --mtime "$(stat -c '%Y' package.json)" --owner root --group root -cf subscription-manager-cockpit.tar -T -
	gzip -n subscription-manager-cockpit.tar
	rm -rf _install

srpm: dist-gzip
	rpmbuild -bs \
	  --define "_sourcedir `pwd`" \
	  --define "_srcrpmdir `pwd`" \
	  subscription-manager-cockpit.spec

rpm: dist-gzip
	mkdir -p "`pwd`/output"
	mkdir -p "`pwd`/rpmbuild"
	rpmbuild -bb \
	  --define "_sourcedir `pwd`" \
	  --define "_specdir `pwd`" \
	  --define "_builddir `pwd`/rpmbuild" \
	  --define "_srcrpmdir `pwd`" \
	  --define "_rpmdir `pwd`/output" \
	  --define "_buildrootdir `pwd`/build" \
	  subscription-manager-cockpit.spec
	find `pwd`/output -name '*.rpm' -printf '%f\n' -exec mv {} . \;
	rm -r "`pwd`/rpmbuild"

# checkout Cockpit's PF/React/build library; again this has no API stability guarantee, so check out a stable tag
$(LIB_TEST):
	git clone -b 253+chromium-sizzle --depth=1 https://github.com/cockpit-project/cockpit.git tmp/cockpit
	mv tmp/cockpit/pkg/lib src/
	rm -rf tmp/cockpit
