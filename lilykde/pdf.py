""" The embedded PDF preview """

import kate
import kate.gui

from qt import QWidget
from kdecore import KURL
from kparts import createReadOnlyPart

# Translate the messages
from lilykde.i18n import _


tool = kate.gui.Tool(_("PDF"), "pdf", kate.gui.Tool.right)
pdfpart = createReadOnlyPart("libkpdfpart", tool.widget)
pdfpart.widget().setFocusPolicy(QWidget.NoFocus)
tool.show()

show = tool.show
hide = tool.hide

#_file = ""

def openFile(pdf):
    #if _file != pdf:
        # KPDF does not always watch the file for updates if the inode
        # number changes, which LilyPond does...
        pdfpart.openURL(KURL(pdf))
        #_file = pdf


# kate: indent-width 4;
