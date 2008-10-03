# This file is part of LilyKDE, http://lilykde.googlecode.com/
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
A LilyPond Quick Insert toolbox.
"""

import re
from qt import *

import kate

from lilykde.util import py2qstringlist
from lilykde.kateutil import Dockable

# Translate the messages
from lilykde.i18n import _

toolbox = QToolBox()

tool = Dockable(toolbox, _("Quick Insert"), "edit", Dockable.left,
        (170, 540), False)
show = tool.show
hide = tool.hide

articulation_groups = (
    (_("Articulation"), (
        ('accent', _("Accent")),
        ('marcato', _("Marcato")),
        ('staccatissimo', _("Staccatissimo")),
        ('staccato', _("Staccato")),
        ('portato', _("Portato")),
        ('tenuto', _("Tenuto")),
        ('espressivo', _("Espressivo")),
        )),
    (_("Ornaments"), (
        ('trill', _("Trill")),
        ('prall', _("Prall")),
        ('mordent', _("Mordent")),
        ('turn', _("Turn")),
        ('prallprall', _("Prall prall")),
        ('prallmordent', _("Prall mordent")),
        ('upprall', _("Up prall")),
        ('downprall', _("Down prall")),
        ('upmordent', _("Up mordent")),
        ('downmordent', _("Down mordent")),
        ('prallup', _("Prall up")),
        ('pralldown', _("Prall down")),
        ('lineprall', _("Line prall")),
        ('reverseturn', _("Reverse turn")),
        )),
    (_("Signs"), (
        ('fermata', _("Fermata")),
        ('shortfermata', _("Short fermata")),
        ('longfermata', _("Long fermata")),
        ('verylongfermata', _("Very long fermata")),
        ('segno', _("Segno")),
        ('coda', _("Coda")),
        ('varcoda', _("Varcoda")),
        ('signumcongruentiae', _("Signumcongruentiae")),
        )),
    (_("Other"), (
        ('upbow', _("Upbow")),
        ('downbow', _("Downbow")),
        ('open', _("Open (e.g. brass)")),
        ('stopped', _("Stopped (e.g. brass)")),
        ('flageolet', _("Flageolet")),
        ('thumb', _("Thumb")),
        ('lheel', _("Left heel")),
        ('rheel', _("Right heel")),
        ('ltoe', _("Left toe")),
        ('rtoe', _("Right toe")),
        )),
    )

shorthands = {
    'marcato': '^',
    'stopped': '+',
    'tenuto': '-',
    'staccatissimo': '|',
    'accent': '>',
    'staccato': '.',
    'portato': '_',
    }

note_re = re.compile(
    # skip this:
    r"\\[A-Za-z]+|<<|>>|\"(?:\\\\|\\\"|[^\"])*\""
    r"|("
    # but catch a pitch...
    r"(\b([a-h]((iss){1,2}|(ess){1,2}|(is){1,2}|(es){1,2}|"
    r"(sharp){1,2}|(flat){1,2}|ss?|ff?)?"
    r"|(do|re|mi|fa|sol|la|si)(dd?|bb?|ss?|kk?)?)[?!]?"
    # ...plus an octave:
    r"('+|,+|(?![A-Za-z]))|"
    # or a chord:
    r"<(\\[A-Za-z]+|\"(\\\\|\\\"|[^\"])*\"|[^>])+>)"
    # finally a duration?
    r"\s*((\\(longa|breve)\b|(1|2|4|8|16|32|64|128|256|512|1024|2048)"
    r"(?!\d))(\s*\.+)?(\s*\*\s*\d+(/\d+)?)*)?)"
    )


class Lqi(QWidget):
    """ Abstract base class for LilyPond Quick Insert tools """
    label, icon, tooltip = '', '', ''

    def __init__(self):
        QWidget.__init__(self, toolbox)
        self.widgets()
        i = toolbox.addItem(self, self.label)
        if self.icon:
            toolbox.setItemIconSet(i,
                QIconSet(QPixmap.fromMimeSource(self.icon)))
        if self.tooltip:
            toolbox.setItemToolTip(i, self.tooltip)


class Articulations(Lqi):
    """
    A toolbox item with articulations.
    Clicking an articulation will insert it in the text document.
    If text (music) is selected, the articulation will be added to all notes.
    """
    label = _("Articulations")
    icon = 'articulation_prall.png'
    tooltip = _("Different kinds of articulations and other signs.")

    def widgets(self):
        layout = QGridLayout(self, 18, 5, 2, 0)
        row = 0
        cols = 5

        self.shorthands = QCheckBox(_("Allow shorthands"), self)
        self.shorthands.setChecked(True)
        layout.addMultiCellWidget(self.shorthands, row, row, 0, cols - 1)
        QToolTip.add(self.shorthands, _(
            "Use short notation for some articulations like staccato."))
        row += 1

        h = QHBox(self)
        layout.addMultiCellWidget(h, row, row, 0, cols - 1)
        l = QLabel(_("Direction:"), h)
        self.direction = QComboBox(h)
        for s in (_("Up"), _("Neutral"), _("Down")):
            self.direction.insertItem(s)
        self.direction.setCurrentItem(1)
        l.setBuddy(self.direction)
        QToolTip.add(h, _("The direction to use for the articulations."))
        row += 1

        for title, group in articulation_groups:
            layout.addMultiCellWidget(
                QLabel('<u>%s</u>:' % title, self), row, row, 0, cols - 1)
            row += 1
            col = 0
            for sign, title in group:
                b = QToolButton(self)
                b.setAutoRaise(True)
                b.setIconSet(QIconSet(
                    QPixmap.fromMimeSource('articulation_%s.png' % sign)))
                QToolTip.add(b, '%s (\\%s)' % (title, sign))
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
            _("Click an articulation sign to add it to your document."),
            _("If you select some music first, the articulation will "
              "be added to all notes in the selection.")), self)
        l.setMaximumWidth(160)
        layout.addMultiCellWidget(l, row, row + 4, 0, cols - 1)

    def writeSign(self, sign):
        if self.shorthands.isChecked() and sign in shorthands:
            art = '^-_'[self.direction.currentItem()] + shorthands[sign]
        else:
            art = ('^', '', '_')[self.direction.currentItem()] + '\\' + sign

        sel = kate.view().selection
        if sel.exists:
            d, v, text = kate.document(), kate.view(), sel.text
            def repl(m):
                if m.group(1):
                    return m.group(1) + art
                else:
                    return m.group(0)
            text = note_re.sub(repl, text)
            d.editingSequence.begin()
            sel.removeSelectedText()
            v.insertText(text)
            d.editingSequence.end()
        else:
            kate.view().insertText(art)



Articulations()


