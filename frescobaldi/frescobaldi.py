#!/usr/bin/python

# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
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

import os, sys

from PyKDE4.kdecore import (KAboutData, KCmdLineArgs, KCmdLineOptions,
    KLocalizedString, KStandardDirs, ki18n)

appName = "frescobaldi"
catalog = appName
programName = ki18n("Frescobaldi")
version = "0.1"
description = ki18n("LilyPond editing environment for KDE")
license = KAboutData.License_GPL
copyright = ki18n("Copyright (c) 2008, Wilbert Berendsen")
text = KLocalizedString()
homepage = "http://www.frescobaldi.org/"
bugs = "info@frescobaldi.org"

# Find our own Python modules and packages
sys.path[0:0] = map(os.path.normpath, map(str,
    KStandardDirs().findDirs("data", appName+"/python")))
from frescobaldi_app import newApp, runningApp

aboutData = KAboutData(appName, catalog, programName, version, description,
    license, copyright, text, homepage, bugs)

KCmdLineArgs.init(sys.argv, aboutData)

options = KCmdLineOptions()
options.add("start <session>", ki18n("Session to start"))
options.add("n").add("new", ki18n("Start a new instance"))
options.add("l").add("line <line>", ki18n("Line number to go to, starting at 1"))
options.add("c").add("column <col>", ki18n("Column to go to, starting at 0"))
options.add("+files", ki18n("LilyPond files to open, may also be textedit URLs"))
KCmdLineArgs.addCmdLineOptions(options)

args = KCmdLineArgs.parsedArgs()

app = (not args.isSet("new") and runningApp()) or newApp()
nav = args.isSet("line") or args.isSet("column")
line = int(args.getOption("line") or 1)
col = int(args.getOption("column") or 0)
for c in range(args.count()):
    doc = app.openUrl(unicode(args.url(c).url()))
    if doc and nav:
        doc.setCursorPosition(line, col)
        nav = False # only first doc
    
app.run()
