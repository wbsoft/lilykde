# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.


from contextlib import contextmanager
import unicodedata

from PyQt4.QtGui import QDialogButtonBox, QFont, QKeySequence
from PyKDE4.kdecore import KGlobal, i18n
from PyKDE4.kdeui import KDialog, KCharSelect, KKeySequenceWidget, KShortcut



class Dialog(KDialog):
    """
    A dialog to select special characters.
    """
    def __init__(self, mainwin):
        KDialog.__init__(self, mainwin)
        self.mainwin = mainwin
        self.shortcuts = mainwin.charSelectShortcuts
        self.setButtons(KDialog.ButtonCode(
            KDialog.Help | KDialog.Apply | KDialog.Ok | KDialog.Close))
        self.setCaption(i18n("Special Characters"))
        
        # trick key button in the DialogButtonBox
        self.keySelector = key = KKeySequenceWidget()
        key.layout().setContentsMargins(20, 0, 0, 0)
        self.findChild(QDialogButtonBox).layout().insertWidget(1, key)
        
        self.charSelect = KCharSelect(None)
        self.setMainWidget(self.charSelect)
        self.charSelect.charSelected.connect(self.insertText)
        self.charSelect.currentCharChanged.connect(self.slotCurrentCharChanged)
        self.keySelector.keySequenceChanged.connect(self.slotKeySequenceChanged)
        self.okClicked.connect(self.insertCurrentChar)
        self.applyClicked.connect(self.insertCurrentChar)
        self.finished.connect(self.saveSettings)
        self.loadSettings()
        
    def insertText(self, text):
        d = self.mainwin.currentDocument()
        d.view.insertText(text)
        
    def insertCurrentChar(self):
        c = self.charSelect.currentChar()
        if c:
            self.insertText(c)

    def loadSettings(self):
        c = config()
        self.restoreDialogSize(c)
        self.charSelect.setCurrentFont(
            c.readEntry("font", QFont("Century Schoolbook L"))) # lily default
        self.charSelect.setCurrentChar(unichr(
            c.readEntry("char", 0)))
        
    def saveSettings(self):
        c = config()
        self.saveDialogSize(c)
        c.writeEntry("font", self.charSelect.currentFont())
        c.writeEntry("char", ord(self.charSelect.currentChar()))

    def populateAction(self, action):
        action.setText(unicodedata.name(int(action.objectName(), 16),
            i18n("unknown")).title())
        
    def actionTriggered(self, name):
        self.insertText(unichr(int(name, 16)))
        
    def slotCurrentCharChanged(self, text):
        key = self.shortcuts.shortcut(hex(ord(text)))
        with blockSignals(self.keySelector) as w:
            w.setKeySequence(key and key.toList()[0] or QKeySequence())
        
    def slotKeySequenceChanged(self, seq):
        self.keySelector.applyStealShortcut()
        self.shortcuts.setShortcut(hex(ord(self.charSelect.currentChar())),
            KShortcut(seq))
        
        
        
def config():
    return KGlobal.config().group("charselect")


@contextmanager
def blockSignals(widget):
    block = widget.blockSignals(True)
    yield widget
    widget.blockSignals(block)
