SRC_DIR = src/rhsm

check:
	nosetests

coverage:
	nosetests --with-cover --cover-package rhsm --cover-erase

coverage-html: coverage
	coverage html --include "${SRC_DIR}/*"

coverage-html-old:
	nosetests --with-cover --cover-package rhsm --cover-html --cover-html-dir test/html --cover-erase

coverage-xml: coverage
	coverage xml --include "${SRC_DIR}/*"

pyflakes:
	-@TMPFILE=`mktemp` || exit 1; \
	find -name \*.py | xargs pyflakes | tee $$TMPFILE; \
		! test -s $$TMPFILE

tablint:
	-@! find -name \*py | GREP_COLOR='7;31' xargs grep --color -nP "^\W*\t"

trailinglint:
	-@! find -name \*py | GREP_COLOR='7;31' xargs grep --color -nP "[ \t]$$"

whitespacelint: tablint trailinglint

pep8:
	-@TMPFILE=`mktemp` || exit 1; \
	pep8 --ignore E501 --exclude ".#*" --repeat src | tee $$TMPFILE; \
		! test -s $$TMPFILE

stylish: pyflakes whitespacelint pep8
