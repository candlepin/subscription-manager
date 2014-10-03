SRC_DIR = src/rhsm

STYLETESTS ?=
PYFILES=`find  ${SRC_DIR} -name "*.py"`
TESTFILES=`find test/ -name "*.py"`
STYLEFILES=$(PYFILES)
# note, set STYLETEST to something if you want
# make stylish to check the tests code
# as well

ifdef STYLETESTS
STYLEFILES+=$(TESTFILES)
endif

docs:
	python setup.py build_sphinx

check:
	python setup.py -q nosetests -c playpen/noserc.dev

coverage: coverage-jenkins

coverage-html: coverage-jenkins

coverage-jenkins:
	python setup.py -q nosetests -c playpen/noserc.ci

clean:
	rm -f *~ *.bak *.tar.gz
	find . -name "*.py[com]" | xargs rm -f
	python setup.py clean --all
	rm -rf cover/ htmlcov/ docs/sphinx/_build/ build/ dist/

version_check:
# needs https://github.com/alikins/pyqver
	-@TMPFILE=`mktemp` || exit 1; \
	pyqver2.py -v -m 2.5  $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

flake8:
	@TMPFILE=`mktemp` || exit 1; \
	python setup.py -q flake8 -q | tee $$TMPFILE; \
	! test -s $$TMPFILE

pylint:
	-@PYTHONPATH="src/:/usr/share/rhn:/usr/share/rhsm" pylint --rcfile=pylintrc $(STYLEFILES)

tablint:
	@! GREP_COLOR='7;31' grep --color -nP "^\W*\t" $(STYLEFILES)

trailinglint:
	@! GREP_COLOR='7;31'  grep --color -nP "[ \t]$$" $(STYLEFILES)

whitespacelint: tablint trailinglint

# look for things that are likely debugging code left in by accident
debuglint:
	@! GREP_COLOR='7;31' grep --color -nP "pdb.set_trace|pydevd.settrace|import ipdb|import pdb|import pydevd" $(STYLEFILES)

gettext_lint:
	@TMPFILE=`mktemp` || exit 1; \
	pcregrep -n --color=auto -M  "_\(.*[\'|\"].*[\'|\"]\s*\+\s*[\"|\'].*[\"|\'].*\)" $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

rpmlint:
	@TMPFILE=`mktemp` || exit 1; \
	rpmlint -f rpmlint.config python-rhsm.spec | grep -v "^.*packages and .* specfiles checked\;" | tee $$TMPFILE; \
	! test -s $$TMPFILE

versionlint:
	@TMPFILE=`mktemp` || exit 1; \
	pyqver2.py -m 2.7 -l $(STYLEFILES) | tee $$TMPFILE; \
	! test -s $$TMPFILE

.PHONY: stylish
stylish: flake8 versionlint whitespacelint gettext_lint rpmlint debuglint

jenkins: stylish coverage-jenkins
