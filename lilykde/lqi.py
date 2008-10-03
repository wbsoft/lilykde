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

from qt import *

import kate

from kateutil import Dockable

# Translate the messages
from lilykde.i18n import _

toolbox = QToolBox()

tool = Dockable(toolbox, _("Quick Insert"), "edit", Dockable.left,
        (150, 500), False)


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
    (_("Performing"), (
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
    (_("Other"), (
        ('fermata', _("Fermata")),
        ('shortfermata', _("Short fermata")),
        ('longfermata', _("Long fermata")),
        ('verylongfermata', _("Very long fermata")),
        ('segno', _("Segno")),
        ('coda', _("Coda")),
        ('varcoda', _("Varcoda")),
        ('signumcongruentiae', _("Signumcongruentiae")),
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

class Lqi(QFrame):
    """ Abstract base class for LilyPond Quick Insert tools """
    label, icon, tooltip = '', '', ''

    def __init__(self):
        super(Lqi, self).__init__(toolbox)
        i = toolbox.addItem(self, self.label)
        if self.icon:
            toolbox.setItemIconSet(i,
                QIconSet(QPixmap.fromMimeSource(self.icon)))
        if self.tooltip:
            toolbox.setItemToolTip(i, self.tooltip)


class Articulations(Lqi):
    """
    A toolbox item with articulations. Clicking an articulation will insert
    in the text document.
    """
    label = _("Articulations")
    icon = 'articulation_prall.png'
    tooltip = _("Different kinds of articulations and other signs.")

    def __init__(self):
        super(Articulations, self).__init__()
        layout = QGridLayout(self)
        row = 0
        cols = 5
        self.shorthands = QCheckBox(_("Allow shorthands"), self)
        self.shorthands.setChecked(True)
        layout.addMultiCellWidget(self.shorthands, row, row, 0, cols - 1)
        QToolTip.add(self.shorthands, _(
            "Use short notation for some articulations like staccato"))
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

    def writeSign(self, sign):
        #TODO: direction (up, down, neutral)
        #TODO: add articulation to many selected notes
        if self.shorthands.isChecked() and sign in shorthands:
            kate.view().insertText('-' + shorthands[sign])
        else:
            kate.view().insertText('\\' + sign)


Articulations()
Articulations()


