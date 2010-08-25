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
A MIDI Player based on the kmid_part widget of KMid.
"""

import os

from PyQt4.QtCore import Q_ARG, QMetaObject, Qt, SIGNAL
from PyQt4.QtGui import (
    QComboBox, QGridLayout, QKeySequence, QLabel, QLCDNumber, QSlider,
    QToolButton, QWidget)
from PyKDE4.kdecore import KPluginLoader, KUrl, i18n
from PyKDE4.kdeui import KAction, KIcon, KShortcut
from PyKDE4.kparts import KParts

EMPTY, STOPPED, PAUSED, PLAYING = 0, 1, 2, 3

def player(tool):
    """ Return a player widget if KMid part can be found.
    
    Otherwise returns a label with explanation.
    
    """
    # load the KMid Part
    factory = KPluginLoader("kmid_part").factory()
    if factory:
        part = factory.create(tool.mainwin)
        if part:
            return Player(tool, part)
    

class Player(QWidget):
    
    def __init__(self, tool, part):
        super(Player, self).__init__(tool.mainwin)
        self.player = part
        self._currentFile = None
        self._currentFileList = None
        
        layout = QGridLayout()
        self.setLayout(layout)
        layout.setSpacing(0)
        
        fl = self.fileList = QComboBox()
        fl.activated.connect(self.slotItemActivated)
        fl.setEnabled(False)
        layout.addWidget(fl, 0, 0, 1, 2)
        
        pb = self.pauseButton = QToolButton()
        pb.setIcon(KIcon('media-playback-pause'))
        pb.clicked.connect(self.pause)
        pb.setToolTip(i18n("Pause"))
        layout.addWidget(pb, 1, 0)
        
        lcd = self.lcd = QLCDNumber()
        lcd.setMaximumHeight(60)
        lcd.setSegmentStyle(QLCDNumber.Filled)
        layout.addWidget(lcd, 2, 0, 1, 2)
        
        vs = self.volumeSlider = QSlider(Qt.Vertical)
        vs.setRange(0, 20)
        vs.setValue(int(self.readProperty('volumeFactor') * 10))
        vs.setToolTip(i18n("Volume"))
        layout.addWidget(vs, 0, 2, 3, 1)
        
        # KMid Part widget
        widget = self.widget = part.widget()
        layout.addWidget(widget, 1, 1)
        
        # make smaller
        widget.layout().setSpacing(0)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        
        # set auto start off
        self.writeProperty('autoStart', False)
        
        # connect stuff
        part.connect(part, SIGNAL("stateChanged(int)"),
            self.slotStateChanged, Qt.QueuedConnection)
        part.connect(part, SIGNAL("beat(int,int,int)"), self.slotBeat)
        vs.valueChanged.connect(self.setVolumeFactor)
    
        tool.mainwin.aboutToClose.connect(self.quit)
        tool.mainwin.currentDocumentChanged.connect(self.setCurrentDocument)
        tool.mainwin.jobManager().jobFinished.connect(self.jobFinished)
        self.slotBeat(0, 0, 0)
        self.setCurrentDocument(tool.mainwin.currentDocument())
        
        # keyboard action to pause playback, works when the MIDI tool is visible
        # (hardcoded to Pause and MediaPlay)
        a = KAction(self)
        a.setShortcut(KShortcut(
            QKeySequence(Qt.Key_Pause), QKeySequence(Qt.Key_MediaPlay)))
        a.triggered.connect(self.slotPlayPause)
        self.addAction(a)
        
        # keyboard action to stop playback, ESC and MediaStop
        a = KAction(self)
        a.setShortcut(KShortcut(
            QKeySequence(Qt.Key_Escape), QKeySequence(Qt.Key_MediaStop)))
        a.triggered.connect(self.stop)
        self.addAction(a)
        
    def slotPlayPause(self):
        """ Called when the user presses the MediaPlay or Pause key.
        
        when stopped, starts playing
        when playing, pauses
        when paused, winds back a few seconds and starts playing
        
        """
        state = self.state()
        if state == STOPPED:
            if self._currentFile:
                self.play()
        elif state == PAUSED:
            self.pause()
        elif state == PLAYING:
            self.rewind(2200)
            self.pause()
        
    def setCurrentDocument(self, doc):
        """ Called when the current document changes. """
        self.setMidiFiles(doc.updatedFiles()("mid*"))
        
    def jobFinished(self, job):
        """ Called when a LilyPond job finishes. """
        self.setMidiFiles(job.updatedFiles()("mid*"), True)
    
    def play(self):
        QMetaObject.invokeMethod(self.player, 'play')
        
    def pause(self):
        QMetaObject.invokeMethod(self.player, 'pause')
        
    def stop(self):
        QMetaObject.invokeMethod(self.player, 'stop')
    
    def seek(self, pos):
        QMetaObject.invokeMethod(self.player, 'seek', Q_ARG("qlonglong", pos))
        
    def rewind(self, msec):
        offset = msec * 768 / 1000
        pos = self.readProperty('position') - offset
        if pos < 0:
            pos = 0
        self.seek(pos)
        
    def quit(self):
        """Called when the application exits."""
        self.stop()
        self.player.closeUrl()
        
    def setMidiFiles(self, files, forceReload=False):
        """ Sets the list of MIDI files that can be played. """
        self._currentFileList = files
        self.fileList.clear()
        self.fileList.addItems([os.path.basename(f) for f in files])
        icon = KIcon("audio-midi")
        for i in range(self.fileList.count()):
            self.fileList.setItemIcon(i, icon)
        self.fileList.setCurrentIndex(0)
        self.fileList.setEnabled(bool(files))
        if files and (forceReload or not self.isPlaying()):
            self.loadFile(files[0], forceReload)
        
    def loadFile(self, fileName, forceReload=False):
        if forceReload or self._currentFile != fileName:
            self._currentFile = fileName
            playing = self.isPlaying()
            if playing:
                self.stop()
            self.player.openUrl(KUrl(fileName))
            self.slotBeat(0, 0, 0)
            if playing:
                self.play()
        
    def slotItemActivated(self, index):
        self.loadFile(self._currentFileList[index])
    
    def slotStateChanged(self, state):
        if state == STOPPED and self._currentFile:
            if self._currentFileList:
                # if there are other files, load one
                if self._currentFile not in self._currentFileList:
                    self.loadFile(
                        self._currentFileList[self.fileList.currentIndex()])
            else:
                # no updated files to load, just close
                self.player.closeUrl()
        self.pauseButton.setDown(state == PAUSED)
    
    def slotBeat(self, measnum, beat, measlen):
        self.lcd.display("{0}:{1}".format(measnum, beat))
        
    def readProperty(self, name):
        mobj = self.player.metaObject()
        prop = mobj.property(mobj.indexOfProperty(name))
        return prop.read(self.player)
    
    def writeProperty(self, name, value):
        mobj = self.player.metaObject()
        prop = mobj.property(mobj.indexOfProperty(name))
        return prop.write(self.player, value)
        
    def state(self):
        """Returns the state of the player."""
        return self.readProperty('state')
    
    def isPlaying(self):
        """Returns True if state is playing or paused."""
        return self.state() in (PAUSED, PLAYING)
        
    def setVolumeFactor(self, volume):
        """ Change the volume factor (0 - 20) """
        QMetaObject.invokeMethod(self.player,
            'setVolumeFactor', Q_ARG("double", volume / 10.0))


