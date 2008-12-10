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

""" LilyPond Quick Insert Toolbox """

import re

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

import ly.articulation, ly.rx

class ToolBox(QToolBox):
    def __init__(self, tool):
        QToolBox.__init__(self)
        self.mainwin = tool.mainwin
        Articulations(self)


class Lqi(QWidget):
    """ Abstract base class for LilyPond Quick Insert tools """

    def __init__(self, toolbox, label, icon="", tooltip=""):
        QWidget.__init__(self, toolbox)
        i = toolbox.addItem(self, label)
        if icon:
            toolbox.setItemIcon(i, KIcon(icon))
        if tooltip:
            toolbox.setItemToolTip(i, tooltip)
        self.view = toolbox.mainwin.view


class Articulations(Lqi):
    """
    A toolbox item with articulations.
    Clicking an articulation will insert it in the text document.
    If text (music) is selected, the articulation will be added to all notes.
    """
    def __init__(self, toolbox):
        Lqi.__init__(self, toolbox, i18n("Articulations"), 'articulation_prall',
            i18n("Different kinds of articulations and other signs."))
            
        layout = QGridLayout(self)
        layout.setSpacing(0)
        row = 0
        cols = 5

        self.shorthands = QCheckBox(i18n("Allow shorthands"), self)
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

        for title, group in ly.articulation.groups(i18n):
            layout.addWidget(
                QLabel('<u>%s</u>:' % title, self), row, 0, 1, cols)
            row += 1
            col = 0
            for sign, title in group:
                b = QToolButton(self)
                b.setAutoRaise(True)
                b.setIcon(KIcon('articulation_%s' % sign))
                b.setIconSize(QSize(22, 22))
                b.setToolTip('%s (\\%s)' % (title, sign))
                QObject.connect(b, SIGNAL("clicked()"),
                    lambda sign = sign: self.writeSign(sign))
                layout.addWidget(b, row, col)
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            if col != 0:
                row += 1

        # help text
        l = QLabel("<p><i>%s</i></p><p><i>%s</i></p>" % (
            i18n("Click an articulation sign to add it to your document."),
            i18n("If you select some music first, the articulation will "
              "be added to all notes in the selection.")), self)
        l.setWordWrap(True)
        layout.addWidget(l, row, 0, 4, cols)

    def writeSign(self, sign):
        if self.shorthands.isChecked() and sign in ly.articulation.shorthands:
            art = '^-_'[self.direction.currentIndex()] + ly.articulation.shorthands[sign]
        else:
            art = ('^', '', '_')[self.direction.currentIndex()] + '\\' + sign

        v, d = self.view(), self.view().document()
        if v.selection():
            def repl(m):
                if m.group('chord'):
                    return m.group('full') + art
                else:
                    return m.group()
            text = unicode(v.selectionText())
            d.startEditing()
            v.removeSelectionText()
            v.insertText(ly.rx.chord.sub(repl, text))
            d.endEditing()
        else:
            v.insertText(art)
        v.setFocus()
        
