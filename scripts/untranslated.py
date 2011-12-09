#!/usr/bin/python

# sort of kind of a translation lint
#
# require's polib from https://bitbucket.org/izi/polib/wiki/Home
#
# from top level of tree:
#    check_translations.py /path/to/source/file
#
#  Should output any untranslated or fuzzy lines from the file in a "lint" style
#!/usr/bin/python

# NEEDS polib from http://pypi.python.org/pypi/polib
# or easy_install polib

import glob
import polib

#FIXME
PO_PATH = "po/"

po_files = glob.glob("%s/*.po" % PO_PATH)

for po_file in po_files:
    print
    print po_file
    p = polib.pofile(po_file)
    for entry in p.untranslated_entries():
        for line in entry.occurrences:
            print "%s:%s" % (line[0], line[1])
        print "\t%s" % entry.msgid

    for entry in p.fuzzy_entries():
        for line in entry.occurrences:
            print "%s:%s" % (line[0], line[1])
        print "\t%s" % entry.msgid
