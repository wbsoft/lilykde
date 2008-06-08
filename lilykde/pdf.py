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

""" The embedded PDF preview """

import kate
import kate.gui

from qt import QWidget, QTimer
from dcopext import DCOPApp
from kdecore import KApplication, KURL
from kparts import createReadOnlyPart

from lilykde.kateutil import Dockable

# Translate the messages
from lilykde.i18n import _


pdfpart = createReadOnlyPart("libkpdfpart")
tool = Dockable(pdfpart.widget(), _("PDF"), "pdf", kate.gui.Tool.right, False)

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
