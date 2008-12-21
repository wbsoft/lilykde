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
Frescobaldi module to run Rumor
"""

import os, re, sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

from frescobaldi_app.widgets import ProcessButton, TempoControl

class RumorPanel(QWidget):
    def __init__(self, tool):
        QWidget.__init__(self)
        self.view = tool.mainwin.view
        layout = QGridLayout(self)
        
        # start-stop toggle button
        layout.addWidget(RumorButton(self), 0, 0, 3, 1)
        
        
        # status bar
        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        layout.addWidget(self.status, 3, 1, 1, 4)
        
        # Tempo adjustment (spinbox + long slider)
        t = TempoControl()
        layout.addWidget(t.spinbox, 0, 2)
        hb = QHBoxLayout()
        layout.addLayout(hb, 0, 3)
        hb.addWidget(t.tapButton)
        hb.addWidget(t.slider)
        self.tempo = t
        
        # Meter select (editable qcombobox defaulting to document)
        AUTO = unicode(i18n("Auto"))
        self.meter = QComboBox()
        self.meter.setEditable(True)
        self.meter.addItems((
            AUTO,
            '1/4', '2/4', '3/4', '4/4', '5/4', '6/4',
            '2/2', '3/2',
            '3/8', '6/8', '9/8', '12/8',
            '3/16',
            ))
        self.meter.setValidator(QRegExpValidator(QRegExp(
            re.escape(AUTO) + "|[1-9][0-9]*/(1|2|4|8|16|32|64|128)"),
            self.meter))
        self.meter.setToolTip(i18n(
            "The meter to use. Leave 'Auto' to let Frescobaldi determine "
            "the meter from the LilyPond document."))
        layout.addWidget(self.meter, 1, 2)

        # Quantize (1,2,4,8,16,32,64 or 128, default to 16)
        hb = QHBoxLayout()
        layout.addLayout(hb, 1, 3)
        l = QLabel(i18n("Quantize:"))
        hb.addWidget(l)
        self.quantize = QComboBox()
        self.quantize.addItems([str(2**i) for i in range(8)])
        self.quantize.setCurrentIndex(4)
        self.quantize.setToolTip(i18n(
            "The shortest note duration to use."))
        hb.addWidget(self.quantize)
        l.setBuddy(self.quantize)

        # Step recording: (checkbox, disables the three controls above)
        self.step = QCheckBox(i18n("Step"))
        self.step.setToolTip(i18n(
            "Record LilyPond input note by note, without durations."))
        hb.addWidget(self.step)

        # Monophonic input (no chords)
        self.mono = QCheckBox(i18n("Mono"))
        self.mono.setToolTip(i18n(
            "Record monophonic input, without chords."))
        hb.addWidget(self.mono)

        # Key signature select (any lilypond pitch, defaulting to document)
        self.keysig = QComboBox()
        self.keysig.addItem(AUTO)
        self.keysig.addItems(["%d" % i for i in range(-7, 1)])
        self.keysig.addItems(["%+d" % i for i in range(1, 8)])
        self.keysig.setToolTip(i18n(
            "The number of accidentals. A negative number designates flats. "
            "Leave 'Auto' to let Frescobaldi determine the key signature from "
            "the LilyPond document."))
        layout.addWidget(self.keysig, 2, 2)

        # labels for controls:
        l = QLabel(i18n("Tempo:"))
        l.setBuddy(self.tempo.spinbox)
        layout.addWidget(l, 0, 1)
        l = QLabel(i18n("Meter:"))
        l.setBuddy(self.meter)
        layout.addWidget(l, 1, 1)
        l = QLabel(i18n("Key:"))
        l.setBuddy(self.keysig)
        layout.addWidget(l, 2, 1)


class RumorButton(ProcessButton):
    def __init__(self, *args):
        super(RumorButton, self).__init__(*args)
        self.setIconSize(QSize(48, 48))
        self.setIcon(KIcon("media-record"))
        self.setToolTip(i18n("Start or stop Rumor MIDI-recording."))
        
        


