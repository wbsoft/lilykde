# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
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

from __future__ import unicode_literals

""" LilyPond Quick Insert Toolbox """

import re

from PyQt4.QtCore import QSize, Qt
from PyQt4.QtGui import (
    QCheckBox, QComboBox, QGridLayout, QLabel, QToolBox, QToolButton, QWidget)
from PyKDE4.kdecore import KGlobal, i18n
from PyKDE4.kdeui import KIcon, KHBox, KMenu

import ly.articulation
from kateshell.shortcut import UserShortcutDispatcher, ShortcutDispatcherClient
from frescobaldi_app.mainapp import SymbolManager


class QuickInsertPanel(SymbolManager, UserShortcutDispatcher, QToolBox):
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
        UserShortcutDispatcher.__init__(self, tool.mainwin.quickInsertShortcuts)
        self.tool = tool
        self.mainwin = tool.mainwin
        Articulations(self)
        Spanners(self)
        self.setMinimumWidth(self.sizeHint().width())
        self.mainwin.aboutToClose.connect(self.saveSettings)
        self.loadSettings()
    
    def loadSettings(self):
        current = self.tool.config().readEntry('current', '')
        for index in range(self.count()):
            w = self.widget(index)
            if w._name == current:
                self.setCurrentIndex(index)
            
    def saveSettings(self):
        self.tool.config().writeEntry('current', self.currentWidget()._name)
        
        
class Lqi(ShortcutDispatcherClient, QWidget):
    """ Abstract base class for LilyPond Quick Insert tools """

    def __init__(self, toolbox, name, title, icon="", symbol="", tooltip=""):
        QWidget.__init__(self, toolbox)
        ShortcutDispatcherClient.__init__(self, toolbox, name)
        self.toolbox = toolbox
        self.mainwin = toolbox.mainwin
        i = toolbox.addItem(self, title)
        if icon:
            toolbox.setItemIcon(i, KIcon(icon))
        elif symbol:
            toolbox.addItemSymbol(toolbox, i, symbol)
        if tooltip:
            toolbox.setItemToolTip(i, tooltip)


class Articulations(Lqi):
    """
    A toolbox item with articulations.
    Clicking an articulation will insert it in the text document.
    If text (music) is selected, the articulation will be added to all notes.
    """
    def __init__(self, toolbox):
        Lqi.__init__(self, toolbox, 'articulation',
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

        self.titles = dict(ly.articulation.articulations(i18n))
        for title, group in ly.articulation.groups(i18n):
            layout.addWidget(QLabel('<u>{0}</u>:'.format(title)), row, 0, 1, cols)
            row += 1
            col = 0
            for sign, title in group:
                b = QToolButton(clicked=(lambda sign: lambda: self.writeSign(sign))(sign))
                b.setContextMenuPolicy(Qt.CustomContextMenu)
                b.customContextMenuRequested.connect((lambda button, sign:
                    lambda pos: self.showContextMenu(sign, button.mapToGlobal(pos)))
                    (b, sign))
                b.setAutoRaise(True)
                # load and convert the icon to the default text color
                toolbox.addSymbol(b, 'articulation_' + sign, 22)
                b.setIconSize(QSize(22, 22))
                b.setToolTip('<b>{0}</b> (\\{1})'.format(title, sign))
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
    
    def showContextMenu(self, name, pos):
        menu = KMenu(self.mainwin)
        menu.aboutToHide.connect(menu.deleteLater)
        a = menu.addAction(KIcon("accessories-character-map"),
            i18n("Configure Keyboard Shortcut (%1)", self.shortcutText(name) or i18n("None")))
        a.triggered.connect(lambda: self.editShortcut(name))
        menu.popup(pos)
        
    def editShortcut(self, name):
        title = self.titles[name]
        icon = self.toolbox.symbolIcon('articulation_' + name, 22)
        super(Articulations, self).editShortcut(name, title, icon)
        self.mainwin.currentDocument().view.setFocus()
        
    def actionTriggered(self, name):
        self.writeSign(name)
        
    def populateAction(self, name, action):
        if name in self.titles:
            action.setText(self.titles[name])
            self.toolbox.addSymbol(action, 'articulation_' + name)


class Spanners(Lqi):
    """A toolbox item with slurs, spanners, etc."""
    def __init__(self, toolbox):
        super(Spanners, self).__init__(toolbox, 'spanner',
            i18n("Spanners"), symbol='slur_solid',
            tooltip=i18n("Slurs, spanners, hairpins, etcetera."))
        