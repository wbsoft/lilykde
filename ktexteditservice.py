#!/usr/bin/env python

# This file is part of LilyKDE, http://lilykde.googlecode.com/
#
# Copyright (c) 2008  Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# See http://www.gnu.org/licenses/ for more information.

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


# kate: indent-width 4;
