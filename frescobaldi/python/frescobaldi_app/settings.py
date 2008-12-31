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
Config dialog
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.ktexteditor import KTextEditor

class SettingsDialog(KPageDialog):
    def __init__(self, mainwin):
        KPageDialog.__init__(self, mainwin)
        self.setFaceType(KPageDialog.Tree)
        self.setButtons(KPageDialog.ButtonCode(KPageDialog.Apply | KPageDialog.Ok | KPageDialog.Cancel))
        self.setCaption(i18n("Configure"))
        self.setDefaultButton(KPageDialog.Ok)
        def changed():
            self.enableButton(KPageDialog.Apply, True)
        self.enableButton(KPageDialog.Apply, False)
        QObject.connect(self, SIGNAL("applyClicked()"), self.applyClicked)
        
        # TODO: our own pages
        
        # Get the KTextEditor config pages.
        editorItem = self.addPage(QWidget(), i18n("Editor Component"))
        editorItem.setHeader(i18n("Editor Component Options"))
        editorItem.setIcon(KIcon("accessories-text-editor"))
        self.editorPages = []
        editor = mainwin.app.editor
        for i in range(editor.configPages()):
            cPage = editor.configPage(i, self)
            QObject.connect(cPage, SIGNAL("changed()"), changed)
            self.editorPages.append(cPage)
            item = self.addSubPage(editorItem, cPage, editor.configPageName(i))
            item.setHeader(editor.configPageFullName(i))
            item.setIcon(editor.configPageIcon(i))

    def done(self, result):
        if result:
            self.saveSettings()
        KPageDialog.done(self, result)
        
    def applyClicked(self):
        self.saveSettings()
        self.enableButton(KPageDialog.Apply, False)

    def loadSettings(self):
        pass # TODO: implement
        
    def saveSettings(self):
        # TODO: own settings:
        
        # KTextEditor settings
        for page in self.editorPages:
            page.apply()
            
