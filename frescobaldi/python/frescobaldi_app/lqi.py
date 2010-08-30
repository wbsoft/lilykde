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
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QLabel, QSizePolicy, QToolBox,
    QToolButton, QVBoxLayout, QWidget)
from PyKDE4.kdecore import KGlobal, i18n
from PyKDE4.kdeui import KIcon, KHBox, KMenu

import ly.articulation, ly.dynamic
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
        self.widgets = [
            Articulations(self),
            Dynamics(self),
            Spanners(self),
        ]
        # don't allow us to shrink below the minimum size of our children
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        width = max(w.minimumSizeHint().width() for w in self.widgets) + 12
        self.setMinimumWidth(width)
        self.mainwin.aboutToClose.connect(self.saveSettings)
        self.loadSettings()
    
    def loadSettings(self):
        current = self.tool.config().readEntry('current', '')
        for i, w in enumerate(self.widgets):
            if w._name == current:
                self.setCurrentIndex(i)
            
    def saveSettings(self):
        self.tool.config().writeEntry('current', self.currentWidget()._name)
    
    def wheelEvent(self, ev):
        i = self.currentIndex() + self.count()
        i += 1 if ev.delta() < 0 else -1
        self.setCurrentIndex(i % self.count())
        ev.accept()


class ActionButton(QToolButton):
    """ A toolbutton that manages its shortcut and title automatically. """
    def __init__(self, panel, name, title,
            symbol=None, icon=None, tooltip=None, size=22):
        QToolButton.__init__(self)
        self.panel = panel
        self.name = name
        self.title = title
        self.symbol = symbol
        self.icon = icon
        if symbol:
            panel.toolbox.addSymbol(self, symbol, size)
        elif icon:
            self.setIcon(KIcon(icon))
        self.clicked.connect(self.fire)
        self.setAutoRaise(True)
        self.setIconSize(QSize(size, size))
        self.setToolTip(tooltip if tooltip else title)
        
    def fire(self):
        self.panel.actionTriggered(self.name)
        
    def contextMenuEvent(self, ev):
        menu = KMenu(self.panel.mainwin)
        menu.aboutToHide.connect(menu.deleteLater)
        a = menu.addAction(KIcon("accessories-character-map"),
            i18n("Configure Keyboard Shortcut (%1)",
                 self.panel.shortcutText(self.name) or i18n("None")))
        a.triggered.connect(self.editShortcut)
        menu.popup(ev.globalPos())
        
    def editShortcut(self):
        if self.symbol:
            icon = self.panel.toolbox.symbolIcon(self.symbol, 22)
        else:
            icon = self.icon
        self.panel.editShortcut(self.name, self.title, icon)
        self.panel.mainwin.currentDocument().view.setFocus()
        
    
class LqiPanel(ShortcutDispatcherClient, QWidget):
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


class Articulations(LqiPanel):
    """
    A toolbox item with articulations.
    Clicking an articulation will insert it in the text document.
    If text (music) is selected, the articulation will be added to all notes.
    """
    def __init__(self, toolbox):
        super(Articulations, self).__init__(toolbox, 'articulation',
            i18n("Articulations"), symbol='articulation_prall',
            tooltip=i18n("Different kinds of articulations and other signs."))
            
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # help text
        self.setWhatsThis("<p>{0}</p><p>{1}</p>".format(
            i18n("Click an articulation sign to add it to your document."),
            i18n("If you select some music first, the articulation will "
              "be added to all notes in the selection.")))
        
        cols = 5

        self.shorthands = QCheckBox(i18n("Allow shorthands"))
        self.shorthands.setChecked(True)
        self.shorthands.setToolTip(i18n(
            "Use short notation for some articulations like staccato."))
        layout.addWidget(self.shorthands)

        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Direction:"), h)
        self.direction = QComboBox(h)
        self.direction.addItems([i18n("Up"), i18n("Neutral"), i18n("Down")])
        self.direction.setCurrentIndex(1)
        l.setBuddy(self.direction)
        h.setToolTip(i18n("The direction to use for the articulations."))

        self.titles = dict(ly.articulation.articulations(i18n))
        for title, group in ly.articulation.groups(i18n):
            box = QGroupBox(title)
            layout.addStretch(1)
            layout.addWidget(box)
            grid = QGridLayout()
            grid.setSpacing(0)
            box.setLayout(grid)
            for num, (sign, title) in enumerate(group):
                row, col = divmod(num, cols)
                b = ActionButton(self, sign, title, 'articulation_' + sign,
                    tooltip='<b>{0}</b> (\\{1})'.format(title, sign))
                grid.addWidget(b, row, col)
        layout.addStretch(2)

    def actionTriggered(self, sign):
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
    
    def populateAction(self, name, action):
        if name in self.titles:
            action.setText(self.titles[name])
            self.toolbox.addSymbol(action, 'articulation_' + name)


class Dynamics(LqiPanel):
    """A toolbox item with slurs, spanners, etc."""
    def __init__(self, toolbox):
        super(Dynamics, self).__init__(toolbox, 'dynamic',
            i18n("Dynamics"), symbol='dynamic_f',
            tooltip=i18n("Dynamic symbols."))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # help text
        self.setWhatsThis("<p>{0}</p><p>{1}</p><p>{2}</p>".format(
            i18n("Click a dynamic sign to add it to your document."),
            i18n("If you select some music first, dynamic spanners will "
                 "be added the selected fragment."),
            i18n("If you have selected some music and you click a sign "
                 "after a spanner, the sign will terminate the spanner.")))
        
        cols = 5

        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Direction:"), h)
        self.direction = QComboBox(h)
        self.direction.addItems([i18n("Up"), i18n("Neutral"), i18n("Down")])
        self.direction.setCurrentIndex(1)
        l.setBuddy(self.direction)
        h.setToolTip(i18n("The direction to use for the dynamics."))

        signs = QGroupBox(i18n("Signs"))
        grid = QGridLayout()
        grid.setSpacing(0)
        signs.setLayout(grid)
        
        for num, sign in enumerate(ly.dynamic.marks):
            row, col = divmod(num, cols)
            b = ActionButton(self, sign,
                i18n("Dynamic sign %1", "<b><i>{0}</i><b>".format(sign)),
                'dynamic_' + sign)
            grid.addWidget(b, row, col)
      
        spanners = QGroupBox(i18n("Spanners"))
        grid = QGridLayout()
        grid.setSpacing(0)
        spanners.setLayout(grid)
        
        self.dynamicSpanners = {}
        for num, (sign, title) in enumerate((
            ('hairpin_cresc', i18n("Hairpin crescendo")),
            ('cresc', i18n("Crescendo")),
            ('hairpin_dim', i18n("Hairpin diminuendo")),
            ('dim', i18n("Diminuendo")),
            ('decresc', i18n("Decrescendo")),
            )):
            self.dynamicSpanners[sign] = title
            row, col = divmod(num, cols)
            b = ActionButton(self, sign, title, 'dynamic_' + sign)
            grid.addWidget(b, row, col)
      
        layout.addStretch(1)
        layout.addWidget(signs)
        layout.addStretch(1)
        layout.addWidget(spanners)
        layout.addStretch(3)

    def actionTriggered(self, name):
        direction = 1 - self.direction.currentIndex()
        # the actual writing is performed by the manipulator (see document.py)
        doc = self.mainwin.currentDocument()
        doc.manipulator().addDynamic(name, direction)
        doc.view.setFocus()
        
    def populateAction(self, name, action):
        if name in self.dynamicSpanners:
            action.setText(self.dynamicSpanners[name])
        elif name in ly.dynamic.marks:
            action.setText(i18n("Dynamic sign %1", "\"{0}\"".format(name)))
        self.toolbox.addSymbol(action, 'dynamic_' + name)


class Spanners(LqiPanel):
    """A toolbox item with slurs, spanners, etc."""
    def __init__(self, toolbox):
        super(Spanners, self).__init__(toolbox, 'spanner',
            i18n("Spanners"), symbol='slur_solid',
            tooltip=i18n("Slurs, spanners, hairpins, etcetera."))


