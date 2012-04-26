#!/usr/bin/python

# dump out the msg keys by themselves, newline seperated
#
# require's polib from https://bitbucket.org/izi/polib/wiki/Home
#
#   python-polib rpm or "easy_install polib"
#
#  usage: just_strings.py po/keys.pot

import polib
import sys

pot_file1 = sys.argv[1]
msgs = polib.pofile(pot_file1)

for msg in msgs:
    print msg.msgid
    print
