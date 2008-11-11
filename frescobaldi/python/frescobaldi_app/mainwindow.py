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

        editor = KTextEditor.EditorChooser.editor()
        doc = editor.createDocument(self)
        view = doc.createView(self)

        self.setXMLFile("/home/kde4dev/dev/frescobaldi/data/frescobaldiui.rc")
        self.createShellGUI(True)
        self.guiFactory().addClient(view)
        self.setCentralWidget(view)
        self.show()

