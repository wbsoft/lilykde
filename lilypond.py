#! python

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
import kate
from kdecore import KGlobal, KStandardDirs

# Add our domain so that the translations can be found
KGlobal.locale().insertCatalogue('lilykde')

# The rest of the plugin is located in KDE/share/apps/lilykde/,
# as a python package named lilykde.
# TODO: install lilykde as site package if system-wide install
sys.path[0:0] = map(os.path.normpath, map(str,
    KStandardDirs().findDirs("data", "lilykde")))

# Get the LilyKDE version, homepage etc.
from lilykde.about import *

__title__ = "LilyPond"
__author__ = "%s <%s>" % (AUTHOR, EMAIL)
__license__ = LICENSE

# Load the KConfig backend for 'lilykderc'
from lilykde import config

# Translate the messages
from lilykde.i18n import _


__doc__ = _(
    "A LilyPond Kate/Pate plugin.\n"
    "\n"
    "This is LilyKDE, a plugin to make it easy to run the LilyPond music "
    "typesetter from within Kate.\n"
    "\n"
    "Version: $version\n"
    "Homepage: $homepage\n"
).args(
    version = VERSION,
    homepage = HOMEPAGE
)

@kate.onWindowShown
def initLilyPond():
    # run the install script if this is the first run or an upgrade
    conf = config()
    if "version" not in conf or conf["version"] != VERSION:
        import lilykde.install
        conf["version"] = VERSION
    # Setup the LilyPond main menu
    from lilykde.menu import menu
    menu.plug(kate.mainWidget().topLevelWidget().menuBar(), 5)
    # Run LilyPond once to determine the version
    import lilykde.version
    # init toolviews if LilyPond document
    documentChanged(kate.document())

@kate.documentManager.onChanged
def documentChanged(doc):
    # only if kate already started and the document has a name
    if kate.application.mainWindow() and doc.url:
        # load lilykde if this is probably a lilypond file
        if doc.information.mimeType == 'text/x-lilypond' or \
                os.path.splitext(doc.url)[1] in ('.ly', '.ily', '.lyi'):
            from lilykde import runlily
            f = runlily.LyFile(doc)
            # Show corresponding PDF if it's not older than the LilyPond file.
            # TODO: make it a config option whether to directly show the PDF.
            if f.hasUpdatedPDF():
                f.previewPDF()
        else:
            # Hide the toolviews (if they exist) when a probably non-lilypond
            # document is selected.
            for m in 'log', 'pdf', 'rumor', 'lqi':
                if hasattr(sys.modules['lilykde'], m):
                    getattr(sys.modules['lilykde'], m).hide()

@kate.onConfigure
def configure(parent):
    # show the configuration dialog
    from lilykde.settings import settings
    settings(parent)


# kate: indent-width 4;
