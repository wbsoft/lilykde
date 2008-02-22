#!/usr/bin/env python
import sys, os, re

if len(sys.argv) != 2:
    sys.stderr.write(
        "Usage:\n"
        "ktexteditservice.py textedit:///path/to/file:line:char:col\n")
    sys.exit(2)

url = unicode(sys.argv[1])
m = re.match("textedit:/{,2}(/[^/].*):(\d+):(\d+):(\d+)$", url)
if m:
    file, (line, char, col) = "file://%s" % m.group(1), map(int, m.group(2,3,4))
    line -= 1 # for KDE 3.x
    #col += 1 # for KDE 4.x
    os.execlp("kate", "kate", "--use", "--line", str(line), "--column", str(col), file)
else:
    sys.stderr.write("Not a valid textedit URL: %s\n" % url)
    sys.exit(1)
