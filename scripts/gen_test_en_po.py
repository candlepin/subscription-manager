#!/usr/bin/python

import polib
import sys


class PotFile:
    def __init__(self):

        self.msgids = []
        self.po = polib.pofile("po/keys.pot")
        for entry in self.po:
            self.msgids.append(entry.msgid)

        self.msgids.sort()

po = polib.POFile()
po.metadata = {
    'Project-Id-Version': '1.0',
    'Report-Msgid-Bugs-To': 'alikins@redhat.com',
    'POT-Creation-Date': '2007-10-18 14:00+0100',
    'PO-Revision-Date': '2007-10-18 14:00+0100',
    'Last-Translator': 'gen_test_en_po.py <nothing@example.com>',
    'Language-Team': 'English <yourteam@example.com>',
    'MIME-Version': '1.0',
    'Content-Type': 'text/plain; charset=utf-8',
    'Content-Transfer-Encoding': '8bit',
}


def gen_msg(msgid, tall=False, longstring=False, wrap=False):
    msg = msgid
    if longstring:
        msg = "%s________________" % msg
    if tall:
        msg = msg + "\n"*40
    if wrap:
        msg = "xx{%s}" % msg
    return msg

def main():
    args = sys.argv[1:]

    tall = False
    longstring = False
    wrap = False
    if "--tall" in args:
        tall = True
    if "--long" in args:
        longstring = True
    if "--wrap" in args:
        wrap = True

    potfile = PotFile()
    for pot_entry in potfile.po:
        entry = polib.POEntry(
            msgid=pot_entry.msgid,
            msgstr=gen_msg(pot_entry.msgid, tall, longstring, wrap),
            occurrences=pot_entry.occurrences
            )
        po.append(entry)

    po.save("po/en_US.po")

if __name__ == "__main__":
    main()
