"""
A LilyPond Kate/Pate plugin.

Makes it easy to run LilyPond from within Kate.
"""

__title__ = "LilyPond"
__author__ = "Wilbert Berendsen <info@wilbertberendsen.nl>"
__license__ = "LGPL"


import sys
import os
import kate

# The rest of the plugin is located in KDE/share/apps/lilykde/, with the
# python modules in ./py/.
from kdecore import KStandardDirs
sys.path[0:0]=map(str, KStandardDirs().findDirs("data", "lilykde/py"))

# Setup the LilyPond main menu
import lymenu

@kate.onWindowShown
def initLilyPond():
    # init stuff
    documentChanged(kate.document())

@kate.documentManager.onChanged
def documentChanged(doc):
    # only if kate already started and the document has a name
    if kate.application.mainWindow() and doc.url:
        # load lilykde if this is probably a lilypond file
        if doc.information.mimeType == 'text/x-lilypond' or \
                os.path.splitext(doc.url)[1] in ('.ly', '.ily', 'lyi'):
            import lilykde
            f = lilykde.LyFile(doc)
            # Show corresponding PDF if it's not older than the LilyPond file.
            # TODO: make it a config option whether to directly show the PDF.
            if f.hasUpdatedPDF():
                f.previewPDF()
        elif 'lilykde' in sys.modules:
            import lilykde
            # Hide the PDF toolview (if it exists) when a probably non-lilypond
            # document is selected. Only if lilykde really loaded.
            lilykde.PDFToolView().hide()
            lilykde.LogWindow().hide()


# kate: indent-width 4;
