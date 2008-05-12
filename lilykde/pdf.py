""" The embedded PDF preview """

import kate
import kate.gui

from qt import QWidget, QTimer
from dcopext import DCOPApp
from kdecore import KApplication, KURL
from kparts import createReadOnlyPart

# Translate the messages
from lilykde.i18n import _


tool = kate.gui.Tool(_("PDF"), "pdf", kate.gui.Tool.right)
pdfpart = createReadOnlyPart("libkpdfpart", tool.widget)
pdfpart.widget().setFocusPolicy(QWidget.NoFocus)
tool.show()

show = tool.show
hide = tool.hide

_file = ""

def openFile(pdf):
    """ Open the specified PDF document """

    global _file

    c = KApplication.kApplication().dcopClient()
    kpdf = DCOPApp(c.appId(), c).kpdf

    # When LilyPond writes a PDF, it first deletes the old one.
    # So the new PDF gets a different inode number, which causes
    # KPDF to sometimes loose the 'watch' on the file.
    # So we call KPDF to open the file, and remember the page number
    # displayed ourselves, because KPDF also seems to forget the scroll
    # position due to LilyPond deleting the old PDF first.
    # It would be best that either KPDF is fixed to just look for a
    # named file, even if it has a different inode number, or that
    # LilyPond is fixed to not delete the old PDF first, but just
    # truncate it and write the new data into it.

    # keep the current page number
    page = kpdf.currentPage()[1]
    # KPDF does not always watch the file for updates if the inode
    # number changes, which LilyPond does...
    kpdf.openDocument(KURL(pdf))
    if _file == pdf:
        QTimer.singleShot(100, lambda: kpdf.goToPage(page))
    _file = pdf


# kate: indent-width 4;
