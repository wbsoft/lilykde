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

""" LilyPond Quick Insert Toolbox """

import re

from PyQt4.QtCore import QSize
from PyQt4.QtGui import (
    QCheckBox, QComboBox, QGridLayout, QLabel, QToolBox, QToolButton, QWidget)
from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KIcon, KHBox

import ly.articulation
from frescobaldi_app.mainapp import SymbolManager


class QuickInsertPanel(SymbolManager, QToolBox):
    """
    The Quick Insert Panel manages its own actionCollection of shortcuts in
    the QuickInsertShortcuts instance of the mainwindow.
    
    If the user presses a keyboard shortcut, the Quick Insert Panel is loaded,
    and the action is dispatched to the tool it originated from.
    
    The actions are named with this format: 'tool:name'. So the correct
    tool can always be found.
    """
    def __init__(self, tool):
        QToolBox.__init__(self)
        SymbolManager.__init__(self)
        self.mainwin = tool.mainwin
        self.shortcuts = tool.mainwin.quickInsertShortcuts
        self.tools = {}
        Articulations(self)
        self.setMinimumWidth(self.sizeHint().width())

    def populateAction(self, action):
        """ Dispatch to the correct tool. """
        if ':' in action.objectName():
            tool, name = action.objectName().split(':')
            if tool in self.tools:
                self.tools[tool].populateAction(name, action)
                
    def actionTriggered(self, name):
        """ Dispatch to the correct tool. """
        if ':' in name:
            tool, name = name.split(':')
            if tool in self.tools:
                self.tools[tool].actionTriggered(name)
        
        
class Lqi(QWidget):
    """ Abstract base class for LilyPond Quick Insert tools """

    def __init__(self, toolbox, name, label, icon="", symbol="", tooltip=""):
        QWidget.__init__(self, toolbox)
        self.name = name
        self.toolbox = toolbox
        toolbox.tools[name] = self
        self.mainwin = toolbox.mainwin
        i = toolbox.addItem(self, label)
        if icon:
            toolbox.setItemIcon(i, KIcon(icon))
        elif symbol:
            toolbox.addItemSymbol(toolbox, i, symbol)
        if tooltip:
            toolbox.setItemToolTip(i, tooltip)

    def setShortcut(self, name, shortcut):
        self.toolbox.shortcuts.setShortcut(self.name + ":" + name, seq)
        
    def shortcut(self, name):
        return self.toolbox.shortcuts.shortcut(self.name + ":" + name)
        
    def populateAction(self, name, action):
        """
        Must implement this to populate the action based on the given name.
        """
        pass
    
    def actionTriggered(self, name):
        """
        Must implement this to perform the action that belongs to name.
        """
        pass
    
    
class Articulations(Lqi):
    """
    A toolbox item with articulations.
    Clicking an articulation will insert it in the text document.
    If text (music) is selected, the articulation will be added to all notes.
    """
    def __init__(self, toolbox):
        Lqi.__init__(self, toolbox, 'articulations',
            i18n("Articulations"), symbol='articulation_prall',
            tooltip=i18n("Different kinds of articulations and other signs."))
            
        layout = QGridLayout(self)
        layout.setSpacing(0)
        row = 0
        cols = 5

        self.shorthands = QCheckBox(i18n("Allow shorthands"))
        self.shorthands.setChecked(True)
        self.shorthands.setToolTip(i18n(
            "Use short notation for some articulations like staccato."))
        layout.addWidget(self.shorthands, row, 0, 1, cols)
        row += 1

        h = KHBox(self)
        layout.addWidget(h, row, 0, 1, cols)
        l = QLabel(i18n("Direction:"), h)
        self.direction = QComboBox(h)
        for s in (i18n("Up"), i18n("Neutral"), i18n("Down")):
            self.direction.addItem(s)
        self.direction.setCurrentIndex(1)
        l.setBuddy(self.direction)
        h.setToolTip(i18n("The direction to use for the articulations."))
        row += 1

        self.titles = {}
        for title, group in ly.articulation.groups(i18n):
            layout.addWidget(QLabel('<u>{0}</u>:'.format(title)), row, 0, 1, cols)
            row += 1
            col = 0
            for sign, title in group:
                self.titles[sign] = title
                b = QToolButton(clicked=(lambda sign: lambda: self.writeSign(sign))(sign))
                b.setAutoRaise(True)
                # load and convert the icon to the default text color
                toolbox.addSymbol(b, 'articulation_' + sign, 22)
                b.setIconSize(QSize(22, 22))
                b.setToolTip('{0} (\\{1})'.format(title, sign))
                layout.addWidget(b, row, col)
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            if col != 0:
                row += 1

        # help text
        l = QLabel("<p><i>{0}</i></p><p><i>{1}</i></p>".format(
            i18n("Click an articulation sign to add it to your document."),
            i18n("If you select some music first, the articulation will "
              "be added to all notes in the selection.")))
        l.setWordWrap(True)
        layout.addWidget(l, row, 0, 4, cols)

    def writeSign(self, sign):
        """
        Write the clicked articulation to the document
        (or add it to all selected pitches).
        """
        if self.shorthands.isChecked() and sign in ly.articulation.shorthands:
            art = '^-_'[self.direction.currentIndex()] + ly.articulation.shorthands[sign]
        else:
            art = ('^', '', '_')[self.direction.currentIndex()] + '\\' + sign
        
        # the actual writing is performed by the manipulator (see document.py)
        doc = self.mainwin.currentDocument()
        doc.manipulator().addArticulation(art)
        doc.view.setFocus()
        
    def actionTriggered(self, name):
        self.writeSign(name)
        
    def populateAction(self, name, action):
        if name in self.titles:
            action.setText(self.titles[name])
