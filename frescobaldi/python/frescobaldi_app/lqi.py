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
from PyKDE4.kdeui import KIcon, KHBox, KMenu, KVBox

import ly.articulation, ly.dynamic
from kateshell.shortcut import UserShortcutDispatcher, ShortcutDispatcherClient
from frescobaldi_app.mainapp import SymbolManager

# how many column of toolbuttons to use
COLUMNS = 5

class QuickInsertPanel(KVBox):
    """
    The Quick Insert Panel manages its own actionCollection of shortcuts in
    the QuickInsertShortcuts instance of the mainwindow.
    
    If the user presses a keyboard shortcut, the Quick Insert Panel is loaded,
    and the action is dispatched to the tool it originated from.
    
    The actions are named with this format: 'tool:name'. So the correct
    tool can always be found.
    """
    def __init__(self, tool):
        KVBox.__init__(self)
        self.tool = tool
        
        h = KHBox(self)
        h.layout().setContentsMargins(8, 2, 4, 0)
        l = QLabel(i18n("Direction:"), h)
        d = self.directionWidget = QComboBox(h)
        d.addItems([i18n("Up"), i18n("Neutral"), i18n("Down")])
        d.setItemIcon(0, KIcon("arrow-up"))
        d.setItemIcon(2, KIcon("arrow-down"))
        d.setCurrentIndex(1)
        l.setBuddy(d)
        h.setToolTip(i18n(
            "Where to add articulations et cetera: "
            "above or below the staff or in the default position."))
        
        t = self.toolboxWidget = ToolBox(self)
        # don't allow us to shrink below the minimum size of our children
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        width = max(w.minimumSizeHint().width() for w in t.widgets) + 12
        self.setMinimumWidth(width)


class ToolBox(SymbolManager, UserShortcutDispatcher, QToolBox):
    """A QToolBox containing different panels.
    
    The mouse wheel pages through the panels.
    
    This object also manages the keyboard shortcuts and the loading of
    LilyPond-generated icons in the right text color.
    
    The current page is saved in the config on exit.
    
    """
    def __init__(self, toolWidget):
        self.toolWidget = toolWidget
        self.tool = toolWidget.tool
        self.mainwin = toolWidget.tool.mainwin
        QToolBox.__init__(self, toolWidget)
        SymbolManager.__init__(self)
        UserShortcutDispatcher.__init__(self, self.mainwin.quickInsertShortcuts)
        self.widgets = [
            Articulations(self),
            Dynamics(self),
            Spanners(self),
            BarLines(self),
        ]
        self.mainwin.aboutToClose.connect(self.saveSettings)
        self.loadSettings()
        self._wheeldelta = 0
    
    def loadSettings(self):
        current = self.tool.config().readEntry('current', '')
        for i, w in enumerate(self.widgets):
            if w._name == current:
                self.setCurrentIndex(i)
            
    def saveSettings(self):
        self.tool.config().writeEntry('current', self.currentWidget()._name)
    
    def wheelEvent(self, ev):
        self._wheeldelta -= ev.delta()
        steps, self._wheeldelta = divmod(self._wheeldelta, 120)
        i = self.currentIndex() + steps
        if 0 <= i < self.count():
            self.setCurrentIndex(i)
            ev.accept()
        else:
            ev.ignore()


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

    def direction(self):
        """ The value of the generic direction widget.
        
        -1 == Down
         0 == Neutral
         1 == Up
         
        """
        return 1 - self.toolbox.toolWidget.directionWidget.currentIndex()


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
        
        self.shorthands = QCheckBox(i18n("Allow shorthands"))
        self.shorthands.setChecked(True)
        self.shorthands.setToolTip(i18n(
            "Use short notation for some articulations like staccato."))
        layout.addWidget(self.shorthands)

        self.titles = dict(ly.articulation.articulations(i18n))
        for title, group in ly.articulation.groups(i18n):
            box = QGroupBox(title)
            layout.addWidget(box)
            grid = QGridLayout()
            grid.setSpacing(0)
            box.setLayout(grid)
            for num, (sign, title) in enumerate(group):
                row, col = divmod(num, COLUMNS)
                b = ActionButton(self, sign, title, 'articulation_' + sign,
                    tooltip='<b>{0}</b> (\\{1})'.format(title, sign))
                grid.addWidget(b, row, col)
        layout.addStretch()

    def actionTriggered(self, sign):
        """
        Write the clicked articulation to the document
        (or add it to all selected pitches).
        """
        if self.shorthands.isChecked() and sign in ly.articulation.shorthands:
            art = '_-^'[self.direction()+1] + ly.articulation.shorthands[sign]
        else:
            art = ('_', '', '^')[self.direction()+1] + '\\' + sign
        
        # the actual writing is performed by the manipulator (see document.py)
        doc = self.mainwin.currentDocument()
        doc.manipulator().addArticulation(art)
        doc.view.setFocus()
    
    def populateAction(self, name, action):
        if name in self.titles:
            action.setText(self.titles[name])
            action.setIcon(self.toolbox.symbolIcon('articulation_' + name))


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
        
        signs = QGroupBox(i18n("Signs"))
        grid = QGridLayout()
        grid.setSpacing(0)
        signs.setLayout(grid)
        
        for num, sign in enumerate(ly.dynamic.marks):
            row, col = divmod(num, COLUMNS)
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
            b = ActionButton(self, sign, title, 'dynamic_' + sign)
            row, col = divmod(num, COLUMNS)
            grid.addWidget(b, row, col)
      
        layout.addWidget(signs)
        layout.addWidget(spanners)
        layout.addStretch()

    def actionTriggered(self, name):
        # the actual writing is performed by the manipulator (see document.py)
        doc = self.mainwin.currentDocument()
        doc.manipulator().addDynamic(name, self.direction())
        doc.view.setFocus()
        
    def populateAction(self, name, action):
        if name in self.dynamicSpanners:
            action.setText(self.dynamicSpanners[name])
        elif name in ly.dynamic.marks:
            action.setText(i18n("Dynamic sign %1", "\"{0}\"".format(name)))
        action.setIcon(self.toolbox.symbolIcon('dynamic_' + name))


class BarLines(LqiPanel):
    """A toolbox item with barlines, etc."""
    def __init__(self, toolbox):
        super(BarLines, self).__init__(toolbox, 'bar',
            i18n("Bar Lines"), symbol='bar_single',
            tooltip=i18n("Bar lines, breathing signs, etcetera."))
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        bars = QGroupBox(i18n("Bar Lines"))
        grid = QGridLayout()
        grid.setSpacing(0)
        bars.setLayout(grid)

        self.bars = {}
        for num, (name, bar, title) in enumerate((
            ("double", "||", i18n("Double bar line")),
            ("end", "|.", i18n("Ending bar line")),
            ("dotted", ":", i18n("Dotted bar line")),
            ("dashed", "dashed", i18n("Dashed bar line")),
            ("invisible", "", i18n("Invisible bar line")),
            ("repeat_start", "|:", i18n("Repeat start")),
            ("repeat_double", ":|:", i18n("Repeat both")),
            ("repeat_end", ":|", i18n("Repeat end")),
            ("cswc", ":|.:", i18n("Repeat both (old)")),
            ("cswsc", ":|.|:", i18n("Repeat both (classic)")),
            ("tick", "'", i18n("Tick bar line")),
            ("single", "|", i18n("Single bar line")),
            ("sws", "|.|", i18n("Small-Wide-Small bar line")),
            ("ws", ".|", i18n("Wide-Small bar line")),
            ("ww", ".|.", i18n("Double wide bar line")),
            ("segno", "S", i18n("Segno bar line")),
        )):
            self.bars[name] = (bar, title)
            b = ActionButton(self, name, title, 'bar_' + name)
            row, col = divmod(num, COLUMNS)
            grid.addWidget(b, row, col)
        layout.addWidget(bars)
        
        breathes = QGroupBox(i18n("Breathing Signs"))
        grid = QGridLayout()
        grid.setSpacing(0)
        breathes.setLayout(grid)
        
        self.breathes = {}
        for num, (name, title) in enumerate((
            ('rcomma', i18n("Default Breathing Sign")),
            ('rvarcomma', i18n("Straight Breathing Sign")),
            ('caesura_curved', i18n("Curved Caesura")),
            ('caesura_straight', i18n("Straight Caesura")),
        )):
            self.breathes[name] = title
            b = ActionButton(self, name, title, 'breathe_' + name)
            row, col = divmod(num, COLUMNS)
            grid.addWidget(b, row, col)
        layout.addWidget(breathes)
        layout.addStretch()

    def actionTriggered(self, name):
        doc = self.mainwin.currentDocument()
        if name in self.bars:
            doc.manipulator().insertBarLine(self.bars[name][0])
            doc.view.setFocus()
        elif name in self.breathes:
            doc.manipulator().insertBreathingSign(name)
            doc.view.setFocus()
        
    def populateAction(self, name, action):
        if name in self.bars:
            action.setText(self.bars[name][1])
            action.setIcon(self.toolbox.symbolIcon('bar_' + name))
        elif name in self.breathes:
            action.setText(self.breathes[name])
            action.setIcon(self.toolbox.symbolIcon('breathe_' + name))
            

class Spanners(LqiPanel):
    """A toolbox item with slurs, spanners, etc."""
    def __init__(self, toolbox):
        super(Spanners, self).__init__(toolbox, 'spanner',
            i18n("Spanners"), symbol='slur_solid',
            tooltip=i18n("Slurs, spanners, etcetera."))

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        box = QGroupBox(i18n("Spanners"))
        box.setToolTip(i18n(
            "These spanners need a music fragment to be selected."))
        grid = QGridLayout()
        grid.setSpacing(0)
        box.setLayout(grid)

        self.spanners = {}

        for num, (name, title, symbol) in enumerate((
            ('slur', i18n("Slur"), 'slur_solid'),
            ('phrasing_slur', i18n("Phrasing Slur"), 'slur_solid'),
            ('beam', i18n("Beam"), 'spanner_beam16'),
            ('trill', i18n("Trill"), 'spanner_trill'),
        )):
            self.spanners[name] = (symbol, title)
            b = ActionButton(self, name, title, symbol)
            row, col = divmod(num, COLUMNS)
            grid.addWidget(b, row, col)
        layout.addWidget(box)
        
        box = QGroupBox(i18n("Arpeggios"))
        box.setToolTip(i18n(
            "Arpeggios are used with chords with multiple notes."))
        grid = QGridLayout()
        grid.setSpacing(0)
        box.setLayout(grid)

        self.arpeggios = {}

        for num, (name, title) in enumerate((
            ('arpeggio_normal', i18n("Arpeggio")),
            ('arpeggio_arrow_up', i18n("Arpeggio with Up Arrow")),
            ('arpeggio_arrow_down', i18n("Arpeggio with Down Arrow")),
            ('arpeggio_bracket', i18n("Bracket Arpeggio")),
            ('arpeggio_parenthesis', i18n("Parenthesis Arpeggio")),
        )):
            self.arpeggios[name] = title
            b = ActionButton(self, name, title, name)
            row, col = divmod(num, COLUMNS)
            grid.addWidget(b, row, col)
        layout.addWidget(box)

        box = QGroupBox(i18n("Glissandos"))
        box.setToolTip(i18n(
            "Glissandos are attached to a note and automatically "
            "extend to the next note."))
        grid = QGridLayout()
        grid.setSpacing(0)
        box.setLayout(grid)

        self.glissandos = {}

        for num, (name, title) in enumerate((
            ('glissando_normal', i18n("Glissando")),
            ('glissando_dashed', i18n("Dashed Glissando")),
            ('glissando_dotted', i18n("Dotted Glissando")),
            ('glissando_zigzag', i18n("Zigzag Glissando")),
            ('glissando_trill', i18n("Trill Glissando")),
        )):
            self.glissandos[name] = title
            b = ActionButton(self, name, title, name)
            row, col = divmod(num, COLUMNS)
            grid.addWidget(b, row, col)
        layout.addWidget(box)
        layout.addStretch()

    def actionTriggered(self, name):
        doc = self.mainwin.currentDocument()
        if name in self.spanners:
            doc.manipulator().addSpanner(name, self.direction())
        elif name in self.arpeggios:
            doc.manipulator().addArpeggio(name)
        elif name in self.glissandos:
            doc.manipulator().addGlissando(name)
        doc.view.setFocus()

    def populateAction(self, name, action):
        if name in self.spanners:
            symbol, title = self.spanners[name]
            action.setText(title)
            action.setIcon(self.toolbox.symbolIcon(symbol))
        elif name in self.arpeggios:
            action.setText(self.arpeggios[name])
            action.setIcon(self.toolbox.symbolIcon(name))
        elif name in self.glissandos:
            action.setText(self.glissandos[name])
            action.setIcon(self.toolbox.symbolIcon(name))


