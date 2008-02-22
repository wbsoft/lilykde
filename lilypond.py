__title__ = "LilyPond"
__author__ = "Wilbert Berendsen <info@wilbertberendsen.nl>"
__license__ = "LGPL"

__version__ = "0.4.3"

import sys
import os
import kate

# The rest of the plugin is located in KDE/share/apps/lilykde/, as a python
# python package named lilykde.
# TODO: install lilykde as site package if system-wide install
from kdecore import KStandardDirs
sys.path[0:0]=map(str, KStandardDirs().findDirs("data", "lilykde"))

from lilykde.i18n import _

__doc__ = _("A LilyPond Kate/Pate plugin.\n"
"\n"
"This is LilyKDE, a plugin to make it easy to run the LilyPond music "
"typesetter from within Kate.\n"
"\n"
"If you also enable the Expand plugin, you get some nice shorthands for often "
"used LilyPond constructs. To view those, look at the x-lilypond MIME-Type "
"in the Expand configuration dialog.\n"
"\n"
"Version: %s\n"
"Homepage: %s\n"
) % (__version__, "http://lilykde.googlecode.com/")

@kate.onWindowShown
def initLilyPond():
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
                os.path.splitext(doc.url)[1] in ('.ly', '.ily', 'lyi'):
            from lilykde import runlily
            f = runlily.LyFile(doc)
            # Show corresponding PDF if it's not older than the LilyPond file.
            # TODO: make it a config option whether to directly show the PDF.
            if f.hasUpdatedPDF():
                f.previewPDF()
        else:
            # Hide the toolviews (if they exist) when a probably non-lilypond
            # document is selected.
            if 'lilykde.pdf' in sys.modules:
                from lilykde import pdf
                pdf.hide()
            if 'lilykde.log' in sys.modules:
                from lilykde import log
                log.hide()


# kate: indent-width 4;
