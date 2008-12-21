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
Some special widgets
"""

from time import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import i18n, KProcess


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
        QObject.connect(self, SIGNAL("pressed()"), tap)
        self.setToolTip(i18n("Click this button a few times to set the tempo."))


class ProcessButton(QPushButton):
    """
    A Pushbutton that starts a process when clicked, and stops it when
    clicked again.
    """
    def __init__(self, *args):
        QPushButton.__init__(self, *args)
        self.setCheckable(True)
        self._p = KProcess()
        @onSignal(self, "clicked()")
        def clicked():
            if self.isRunning():
                self.stop()
            else:
                self.start()

    def isRunning(self):
        return self._p.state() != QProcess.NotRunning
        
    def start(self):
        """ Starts the process, calling the initializeProcess method first."""
        p = KProcess()    # create a new one (FIXME: really needed?)
        self._p = p
        @onSignal(p, "finished(int, QProcess::ExitStatus)")
        def finished(exitCode, exitStatus):
            self.setChecked(False)
            self.finished(exitCode, exitStatus)
        @onSignal(p, "error(QProcess::ProcessError)")
        def error(errorCode):
            self.setChecked(False)
            self.error(errorCode)
        @onSignal(p, "started()")
        def started():
            self.setChecked(True)
        QObject.connect(p, SIGNAL("readyRead()"), self.readOutput)
        QObject.connect(p, SIGNAL("readyReadStandardError"), self.readStderr)
        QObject.connect(p, SIGNAL("readyReadStandardOutput"), self.readStdout)
        self.initializeProcess(p)
        p.start()
        
    def stop(self):
        if self.isRunning():
            self._p.terminate()
    
    def finished(self, exitCode, exitStatus):
        pass
    
    def error(self, errorCode):
        pass
    
    def readOutput(self):
        pass
    
    def readStderr(self):
        pass
    
    def readStdout(self):
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
        QObject.connect(self.slider, SIGNAL("valueChanged(int)"),
            self.spinbox.setValue)
        QObject.connect(self.spinbox, SIGNAL("valueChanged(int)"),
            self.slider.setValue)
        
        self.slider.setMinimumWidth(200)
        self.setTempo(100) # default

    def tempo(self):
        return self.spinbox.value()

    def setTempo(self, value):
        self.spinbox.setValue(value)



def onSignal(obj, signalName):
    """ decorator to easily add connect a Qt signal to a Python slot."""
    def decorator(func):
        QObject.connect(obj, SIGNAL(signalName), func)
        return func
    return decorator
