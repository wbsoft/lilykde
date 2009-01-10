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

"""
Preview dialog for the Score Wizard (scorewiz/__init__.py).
In separate file to ease maintenance.
"""

import ly, ly.dom

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

class PreviewDialog(KDialog):
    def __init__(self, scorewiz):
        self.scorewiz = scorewiz
        KDialog.__init__(self, scorewiz)
        self.setModal(True)
        self.setCaption(i18n("PDF Preview"))
        self.setButtons(KDialog.ButtonCode(KDialog.Close))
        
        
    def showPreview(self):
        # TODO: implement
        self.show()

