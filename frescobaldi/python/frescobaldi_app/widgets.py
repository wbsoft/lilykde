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

"""
Some special widgets
"""

import os
from time import time

from PyQt4.QtCore import QProcess, QRegExp, Qt
from PyQt4.QtGui import (
    QComboBox, QLabel, QPushButton, QSlider, QSpinBox, QRegExpValidator)
from PyKDE4.kdecore import i18n, KProcess
from PyKDE4.kdeui import KDialog, KLineEdit, KVBox

from frescobaldi_app.mainapp import SymbolManager


class TapButton(QPushButton):
    """
    A button the user can tap a tempo on.

    The callback is a function that is called
    with the number of beats per minute.
    """
    def __init__(self, parent, callback):
        QPushButton.__init__(self, i18n("Tap"), parent)
        self.tapTime = 0.0
        def tap():
            self.tapTime, t = time(), self.tapTime
            callback(int(60.0 / (self.tapTime - t)))
        self.pressed.connect(tap)
        self.setToolTip(i18n("Click this button a few times to set the tempo."))


class ProcessButtonBase(object):
    """
    to be subclassed together with a QPushButton or a QToolButton
    A button that starts a process when clicked, and stops it when
    clicked again.
    """
    def __init__(self, *args):
        super(ProcessButtonBase, self).__init__(*args)
        self.setCheckable(True)
        self._p = KProcess()
        self.clicked.connect(self.slotClicked)
    
    def slotClicked(self):
        if self.isRunning():
            self.setChecked(True) # keep pressed down
            self.stop()
        else:
            self.start()

    def isRunning(self):
        return self._p.state() != QProcess.NotRunning
        
    def start(self):
        """ Starts the process, calling the initializeProcess method first."""
        p = KProcess()    # create a new one (FIXME: really needed?)
        self._p = p
        self.destroyed.connect(p.terminate)
        p.finished.connect(self.slotFinished)
        p.error.connect(self.slotError)
        p.started.connect(self.slotStarted)
        p.readyRead.connect(self.slotReadyRead)
        p.readyReadStandardError.connect(self.slotReadyReadStandardError)
        p.readyReadStandardOutput.connect(self.slotReadyReadStandardOutput)
        self.initializeProcess(p)
        p.start()
        
    def slotFinished(self, exitCode, exitStatus):
        self.setChecked(False)
        self.finished(exitCode, exitStatus)
    
    def slotError(self, errorCode):
        self.setChecked(False)
        self.error(errorCode)
    
    def slotStarted(self):
        self.setChecked(True)
        self.started()
    
    def slotReadyRead(self):
        self.readOutput(self._p.readAll())
    
    def slotReadyReadStandardError(self):
        self.readStderr(self._p.readAllStandardError())
    
    def slotReadyReadStandardOutput(self):
        self.readStdout(self._p.readAllStandardOutput())
    
    def stop(self):
        """ Abort the running process """
        self._p.terminate()
    
    def quit(self):
        """
        Really stop. After return of this function, the process
        has been stopped neatly.
        """
        if self.isRunning():
            self.stop()
            if not self._p.waitForFinished(3000):
                self._p.kill()
        
    def process(self):
        """ Return the current KProcess instance. """
        return self._p
    
    def started(self):
        """ Called when the process really has been started. """
        pass
    
    def finished(self, exitCode, exitStatus):
        """ Called when the process has finished. """
        pass
    
    def error(self, errorCode):
        """ Called when there was an error. """
        pass
    
    def writeInput(self, text):
        """ Call to write input to the running process """
        self._p.write(text)
        
    def readOutput(self, qbytearray):
        """ Called with the read output if available. """
        pass
    
    def readStderr(self, qbytearray):
        """ Called with the read standard error if available. """
        pass
    
    def readStdout(self, qbytearray):
        """ Called with the read standard output if available. """
        pass
    
    def initializeProcess(self, p):
        """
        This method should be reimplemented to initialize the
        process the way you want it (e.g. set command and args, working
        directory, channels to open, etc.
        """
        p.setProgram(("kdialog", "--sorry", "Not Implemented"))
        

class TempoControl(object):
    """
    A combination of a spinbox, slider, and tap button to set the tempo.
    You must add them to a layout
    """
    minBPM = 30
    maxBPM = 400

    def __init__(self):
        self.spinbox = QSpinBox()
        self.spinbox.setRange(self.minBPM, self.maxBPM)
        self.spinbox.setToolTip(i18n("The tempo in beats per minute."))
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(self.minBPM, self.maxBPM)

        def tap(bpm):
            """ Tap the tempo """
            if self.minBPM <= bpm <= self.maxBPM:
                self.setTempo(bpm)
        self.tapButton = TapButton(None, tap)
        
        # setup signals
        self.slider.valueChanged.connect(self.spinbox.setValue)
        self.spinbox.valueChanged.connect(self.slider.setValue)
        
        self.slider.setMinimumWidth(200)
        self.setTempo(100) # default

    def tempo(self):
        return self.spinbox.value()

    def setTempo(self, value):
        self.spinbox.setValue(value)


class ClefSelector(SymbolManager, QComboBox):
    """
    A ComboBox to select a clef.
    
    Set resp. noclef and/or tab to True for those allowing the user
    to choose those clef/staff types.
    """
    def __init__(self, parent=None, noclef=False, tab=False):
        SymbolManager.__init__(self)
        QComboBox.__init__(self, parent)
        self.setDefaultSymbolSize(48)
        self.setSymbolSize(self, 48)
        self.clefs = [
            ('treble', i18n("Treble")),
            ('alto', i18n("Alto")),
            ('tenor', i18n("Tenor")),
            ('treble_8', i18n("Treble 8")),
            ('bass', i18n("Bass")),
            ('percussion', i18n("Percussion")),
            ]
        if tab:
            self.clefs.append(('tab', i18n("Tab clef")))
        if noclef:
            self.clefs.insert(0, ('', i18n("No Clef")))
        self.addItems([title for name, title in self.clefs])
        for index, (name, title) in enumerate(self.clefs):
            self.addItemSymbol(self, index, 'clef_' + (name or 'none'))
    
    def clef(self):
        """
        Returns the LilyPond name of the selected clef, or the empty string
        for no clef.
        """
        return self.clefs[self.currentIndex()][0]
    

