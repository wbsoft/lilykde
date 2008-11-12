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

from PyKDE4.kparts import KParts
from PyKDE4.ktexteditor import KTextEditor


class MainWindow(KParts.MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setXMLFile("frescobaldiui.rc")
        self.createShellGUI(True)
        self.show()
        self._currentView = None

    def showView(self, view):
        if view is self._currentView:
            return
        if self._currentView:
            self.guiFactory().removeClient(self._currentView)
        self.guiFactory().addClient(view)
        #self.setCentralWidget(view)
        self._currentView = view

