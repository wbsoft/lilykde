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

from lilykde.util import py2qstringlist
from lilykde import config, editor
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


durations = ['\\maxima', '\\longa', '\\breve',
    '1', '2', '4', '8', '16', '32', '64', '128', '256', '512', '1024', '2048']


class Res(object):
    """ static class to store regexps """

    pitch = (
        r"(?P<pitch>\b([a-h]((iss){1,2}|(ess){1,2}|(is){1,2}|(es){1,2}|"
        r"(sharp){1,2}|(flat){1,2}|ss?|ff?)?"
        r"|(do|re|mi|fa|sol|la|si)(dd?|bb?|ss?|kk?)?)(?P<cautionary>[?!])?)"
    )

    octave = r"(?P<octave>'+|,+|(?![A-Za-z]))(\s*(?P<octcheck>=[',]*))?"

    duration = (
        r"(?P<duration>"
            r"(?P<dur>"
                r"\\(maxima|longa|breve)\b|"
                r"(1|2|4|8|16|32|64|128|256|512|1024|2048)(?!\d)"
            r")"
            r"(\s*(?P<dots>\.+))?"
            r"(?P<scale>(\s*\*\s*\d+(/\d+)?)*)"
        r")"
    )

    quotedstring = r"\"(?:\\\\|\\\"|[^\"])*\""

    chord = re.compile(
        # skip this:
        r"\\[A-Za-z]+|<<|>>|" + quotedstring +
        # but catch either a pitch plus an octave
        r"|((?P<chord>" + pitch + octave +
        # or a chord:
        r"|<(\\[A-Za-z]+|" + quotedstring + r"|[^>])*>)"
        # finally a duration?
        r"(\s*" + duration + r")?)"
    )

    finddurs = re.compile(duration)


class Lqi(QWidget):
    """ Abstract base class for LilyPond Quick Insert tools """
    label, icon, tooltip = '', '', ''

    def __init__(self):
        QWidget.__init__(self, toolbox)
        self.widgets()
        i = toolbox.addItem(self, self.label)
        if self.icon:
            toolbox.setItemIconSet(i,
                QIconSet(QPixmap.fromMimeSource(self.icon + '.png')))
        if self.tooltip:
            toolbox.setItemToolTip(i, self.tooltip)


class Articulations(Lqi):
    """
    A toolbox item with articulations.
    Clicking an articulation will insert it in the text document.
    If text (music) is selected, the articulation will be added to all notes.
    """
    label = _("Articulations")
    icon = 'articulation_prall'
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

        text = editor.selectedText()
        if text:
            def repl(m):
                if m.group(1):
                    return m.group(1) + art
                else:
                    return m.group(0)
            editor.replaceSelectionWith(Res.chord.sub(repl, text))
        else:
            editor.insertText(art)


class Rhythm(Lqi):
    """
    A widget containing different tools to edit durations.
    """
    label = _("Rhythm")
    icon = 'icon_rhythm'
    tooltip = _("Different tools to edit durations.")


    def widgets(self):
        l = QVBoxLayout(self)
        g = QVGroupBox(_("Durations"), self)
        l.addWidget(g)

        for func, title, tooltip in (
            (self.doubleDurations, _("Double durations"),
                _("Double all the durations in the selection.")),
            (self.halveDurations, _("Halve durations"),
                _("Halve all the durations in the selection.")),
            (self.dotDurations, _("Dot durations"),
                _("Add a dot to all the durations in the selection.")),
            (self.undotDurations, _("Undot durations"),
                _("Remove one dot from all the durations in the selection.")),
            (self.removeScaling, _("Remove scaling"),
                _("Remove all scaling (*n/m) from the durations in the "
                  "selection.")),
            (self.removeDurations, _("Remove durations"),
                _("Remove all durations from the selection.")),
            ):
            b = QPushButton(title, g)
            QToolTip.add(b, tooltip)
            QObject.connect(b, SIGNAL("clicked()"), func)

        l.addSpacing(10)

        g = QVGroupBox(_("Apply rhythm"), self)
        l.addWidget(g)
        self.rhythm = QLineEdit(g)
        QToolTip.add(self.rhythm, _(
            "Enter a rhythm using space separated duration values "
            "(e.g. 8. 16 8 4 8)"))
        b = QPushButton(_("Apply"), g)
        QToolTip.add(b, _(
            "Press to apply the entered rhythm to the selected music. "
            "This will delete previous entered durations."))
        QObject.connect(b, SIGNAL("clicked()"), self.applyRhythm)

        # at the end
        l.addStretch(10)



    def editRhythm(func):
        """
        Decorator to handles functions that use the Res.chord regexp
        substitute function to iterate over the selected music.
        """
        def deco(self):
            text = editor.selectedText()
            if text:
                editor.replaceSelectionWith(Res.chord.sub(func, text), True)
        return deco

    @editRhythm
    def doubleDurations(m):
        if m.group('duration'):
            chord, dur, dots, scale = m.group('chord', 'dur', 'dots', 'scale')
            if dur in durations:
                i = durations.index(dur)
                if i > 0:
                    dur = durations[i - 1]
            return ''.join(i or '' for i in (chord, dur, dots, scale))
        else:
            return m.group(0)

    @editRhythm
    def halveDurations(m):
        if m.group('duration'):
            chord, dur, dots, scale = m.group('chord', 'dur', 'dots', 'scale')
            if dur in durations:
                i = durations.index(dur)
                if i < len(durations) - 1:
                    dur = durations[i + 1]
            return ''.join(i or '' for i in (chord, dur, dots, scale))
        else:
            return m.group(0)

    @editRhythm
    def dotDurations(m):
        if m.group('duration'):
            chord, dur, dots, scale = m.group('chord', 'dur', 'dots', 'scale')
            dots = (dots or '') + '.'
            return ''.join(i or '' for i in (chord, dur, dots, scale))
        else:
            return m.group(0)

    @editRhythm
    def undotDurations(m):
        if m.group('duration'):
            chord, dur, dots, scale = m.group('chord', 'dur', 'dots', 'scale')
            if dots:
                dots = dots[1:]
            return ''.join(i or '' for i in (chord, dur, dots, scale))
        else:
            return m.group(0)

    @editRhythm
    def removeScaling(m):
        if m.group('duration'):
            return ''.join(i or '' for i in m.group('chord', 'dur', 'dots'))
        else:
            return m.group(0)

    @editRhythm
    def removeDurations(m):
        if m.group(1):
            return m.group('chord')
        else:
            return m.group(0)

    def applyRhythm(self):
        """ Adds the entered rhythm to the selected music."""
        text = editor.selectedText()
        if text:
            durs = [m.group() for m in Res.finddurs.finditer(
                unicode(self.rhythm.text()))]
            def durgen():
                old = ''
                while True:
                    for i in durs:
                        yield i != old and i or ''
                        old = i
            nextdur = durgen().next
            def repl(m):
                if m.group('chord'):
                    return m.group('chord') + nextdur()
                else:
                    return m.group(0)
            editor.replaceSelectionWith(Res.chord.sub(repl, text), True)





Articulations()
Rhythm()


# Remember the currently selected tab.
def _saveTab(index):
    config('lqi')['current tab'] = index
toolbox.setCurrentIndex(int(config('lqi')['current tab'] or '0'))
QObject.connect(toolbox, SIGNAL("currentChanged(int)"), _saveTab)

