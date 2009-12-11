#!@PYTHON_EXECUTABLE@

# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
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
# along with this package; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
# See http://www.gnu.org/licenses/ for more information.

import sys

import sip
sip.setapi("QString", 2)
sip.setapi("QVariant", 2)

from PyKDE4.kdecore import (ki18n, ki18nc,
    KAboutData, KCmdLineArgs, KCmdLineOptions, KComponentData, KLocalizedString)

# Find our own Python modules and packages
sys.path.insert(0, "@MODULE_DIR@")
from frescobaldi_app import newApp, runningApp

appName = "frescobaldi"
catalog = appName
programName = ki18n("Frescobaldi")
version = "@VERSION@"
description = ki18n("LilyPond Music Editor")
license = KAboutData.License_GPL
copyright = ki18n("Copyright (c) 2008-2009, Wilbert Berendsen")
text = KLocalizedString()
homepage = "http://www.frescobaldi.org/"
bugs = "info@frescobaldi.org"

aboutData = KAboutData(appName, catalog, programName, version, description,
    license, copyright, text, homepage, bugs)

aboutData.setTranslator(
    ki18nc("NAME OF TRANSLATORS", "Your name"),
    ki18nc("EMAIL OF TRANSLATORS", "i18n@frescobaldi.org"))
 
KCmdLineArgs.init(sys.argv, aboutData)
KComponentData(aboutData).dirs().addPrefix("@CMAKE_INSTALL_PREFIX@")

options = KCmdLineOptions()
options.add("start <session>", ki18n("Session to start"))
options.add("n").add("new", ki18n("Start a new instance"))
options.add("e").add("encoding <enc>", ki18n("Encoding to use"))
options.add("l").add("line <num>", ki18n("Line number to go to, starting at 1"))
options.add("c").add("column <num>", ki18n("Column to go to, starting at 0"))
options.add("smart", ki18n("Try to use smart line and column numbers"))
options.add("+files", ki18n("LilyPond files to open, may also be textedit URLs"))
KCmdLineArgs.addCmdLineOptions(options)

args = KCmdLineArgs.parsedArgs()

app = not args.isSet("new") and runningApp() or newApp()
docs = [app.openUrl(args.url(c), args.getOption("encoding"))
        for c in range(args.count())]
if docs:
    docs[-1].setActive()
    if args.isSet("line") or args.isSet("column"):
        line = int(args.getOption("line") or 1)
        col = int(args.getOption("column") or 0)
        docs[-1].setCursorPosition(line, col, args.isSet("smart"))
    
app.run()
