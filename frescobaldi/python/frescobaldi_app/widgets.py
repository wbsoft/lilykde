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

import os
from time import time

from PyQt4.QtCore import QObject, QProcess, QString, Qt, SIGNAL
from PyQt4.QtGui import QLineEdit, QPushButton, QSlider, QSpinBox, QToolButton
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
        @onSignal(self, "clicked()")
        def clicked():
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
            self.started()
        @onSignal(p, "readyRead()")
        def readOutput():
            self.readOutput(self._p.readAll())
        @onSignal(p, "readyReadStandardError")
        def readStderr():
            self.readStderr(self._p.readAllStandardError())
        @onSignal(p, "readyReadStandardOutput")
        def readStdout():
            self.readStdout(self._p.readAllStandardOutput())
        self.initializeProcess(p)
        p.start()
        
    def stop(self):
        """ Abort the running process """
        self._p.terminate()
    
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


class ExecLineEdit(QLineEdit):
    """
    A QLineEdit to enter a filename or path.
    The background changes to red if the entered path is not an
    executable command.
    """
    def __init__(self, *args):
        QLineEdit.__init__(self, *args)
        QObject.connect(self, SIGNAL("textChanged(const QString&)"),
            self._checkexec)

    def _get(self, filename):
        return unicode(filename)

    def _checkexec(self, filename):
        if not findexe(self._get(filename)):
            self.setStyleSheet("QLineEdit { background-color: #FAA }")
        else:
            self.setStyleSheet("")


class ExecArgsLineEdit(ExecLineEdit):
    """
    An ExecLineEdit that allows arguments in the command string.
    """
    def _get(self, filename):
        return unicode(filename).split()[0]



# utility functions used by above classes:

def onSignal(obj, signalName):
    """ decorator to easily add connect a Qt signal to a Python slot."""
    def decorator(func):
        QObject.connect(obj, SIGNAL(signalName), func)
        return func
    return decorator

def isexe(path):
    """
    Return path if it is an executable file, otherwise False
    """
    return os.access(path, os.X_OK) and path

def findexe(filename):
    """
    Look up a filename in the system PATH, and return the full
    path if it can be found. If the path is absolute, return it
    unless it is not an executable file.
    """
    if os.path.isabs(os.path.expanduser(filename)):
        return isexe(os.path.expanduser(filename))
    for p in os.environ.get("PATH", os.defpath).split(os.pathsep):
        if isexe(os.path.join(p, filename)):
            return os.path.join(p, filename)
    return False
