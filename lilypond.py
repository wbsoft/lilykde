__title__ = "LilyPond"
__author__ = "Wilbert Berendsen <info@wilbertberendsen.nl>"
__license__ = "LGPL"

__version__ = "0.3.2"

import sys
import os
import kate

# The rest of the plugin is located in KDE/share/apps/lilykde/, with the
# python modules in ./py/.
from kdecore import KStandardDirs
sys.path[0:0]=map(str, KStandardDirs().findDirs("data", "lilykde/py"))

from lilykde_i18n import _
__doc__ = _("""
A LilyPond Kate/Pate plugin.

This is LilyKDE, a plugin to make it easy to run the LilyPond music typesetter from within Kate.

If you also enable the Expand plugin, you get nice shorthands for often used LilyPond constructs. To view those, look at the x-lilypond MIME-Type in the Expand configuration dialog.

Version: %s
Homepage: %s
""") % (__version__, "http://lilykde.googlecode.com/")


@kate.onWindowShown
def initLilyPond():
    # Setup the LilyPond main menu
    from lymenu import menu
    menu.plug(kate.mainWidget().topLevelWidget().menuBar(), 5)
    # init toolviews if LilyPond document
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
