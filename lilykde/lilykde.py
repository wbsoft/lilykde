#!/usr/bin/python

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

import os, sys

from PyKDE4.kdecore import KStandardDirs
from PyKDE4.kdecore import KAboutData, KCmdLineArgs, KCmdLineOptions
from PyKDE4.kdecore import ki18n, KLocalizedString
from PyKDE4.kdeui import KApplication

appName = "lilykde"
catalog = ""
programName = ki18n("LilyKDE")
version = "1.0"
description = ki18n("LilyPond editing environment")
license = KAboutData.License_GPL
copyright = ki18n("Copyright (c) 2008, Wilbert Berendsen")
text = KLocalizedString()
homepage = "http://lilykde.googlecode.com/"
bugs = "lilykde@googlegroups.com"

aboutData = KAboutData(appName, catalog, programName, version, description,
    license, copyright, text, homepage, bugs)

KCmdLineArgs.init(sys.argv, aboutData)

options = KCmdLineOptions()
options.add("+files", ki18n("LilyPond files to open"))


KCmdLineArgs.addCmdLineOptions(options)

# Instantiate our KDE application
app = KApplication()

# Find python modules and packages in our appdir
sys.path[0:0] = map(os.path.normpath, map(str,
    KStandardDirs().findDirs("appdata", "py")))

# Parse the command line args

# Instantiate one main window
MainWindow() # MainWindow keeps a pointer to its instances

sys.exit(app.exec_())

