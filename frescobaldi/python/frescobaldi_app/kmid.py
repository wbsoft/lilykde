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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kparts import KParts

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

    label = QLabel(i18n(
        "Could not load the KMid part.\n"
        "Please install KMid 2.4.0 or higher."))
    label.setAlignment(Qt.AlignCenter)
    return label
    

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
        pb.clicked.connect(self.slotPauseButtonClicked)
        pb.setToolTip(i18n("Pause"))
        layout.addWidget(pb, 1, 0)
        
        lcd = self.lcd = QLCDNumber()
        lcd.setMaximumHeight(70)
        layout.addWidget(lcd, 2, 0, 1, 2)
        
        # KMid Part widget
        widget = self.widget = part.widget()
        layout.addWidget(widget, 1, 1)
        
        # make smaller
        widget.layout().setSpacing(0)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        
        # set auto start off
        mobj = part.metaObject()
        prop = mobj.property(mobj.indexOfProperty('autoStart'))
        prop.write(part, False)
        
        # connect stateChanged
        part.connect(part, SIGNAL("stateChanged(int)"),
            self.slotStateChanged, Qt.QueuedConnection)
        part.connect(part, SIGNAL("beat(int,int,int)"), self.slotBeat)
    
        tool.mainwin.aboutToClose.connect(self.quit)
        tool.mainwin.currentDocumentChanged.connect(self.setCurrentDocument)
        tool.mainwin.jobManager().jobFinished.connect(self.jobFinished)
        self.setCurrentDocument(tool.mainwin.currentDocument())
        self.slotBeat(0, 0, 0)

    def setCurrentDocument(self, doc):
        """ Called when the current document changes. """
        self.setMidiFiles(doc.updatedFiles()("mid*"))
        
    def jobFinished(self, job):
        """ Called when a LilyPond job finishes. """
        self.setMidiFiles(job.updatedFiles()("mid*"))
    
    def quit(self):
        """Called when the application exits."""
        QMetaObject.invokeMethod(self.player, "stop")
        self.player.closeUrl()
        
    def setMidiFiles(self, files):
        """ Sets the list of MIDI files that can be played. """
        self._currentFileList = files
        self.fileList.clear()
        self.fileList.addItems([os.path.basename(f) for f in files])
        self.fileList.setCurrentIndex(0)
        self.fileList.setEnabled(bool(files))
        if files and not self.isPlaying():
            self.loadFile(files[0])
        
    def loadFile(self, fileName, forceReload=False):
        if forceReload or self._currentFile != fileName:
            self._currentFile = fileName
            playing = self.isPlaying()
            if playing:
                QMetaObject.invokeMethod(self.player, 'stop')
            self.player.openUrl(KUrl(fileName))
            self.slotBeat(0, 0, 0)
            if playing:
                QMetaObject.invokeMethod(self.player, 'play')
        
    def slotItemActivated(self, index):
        self.loadFile(self._currentFileList[index])
    
    def slotPauseButtonClicked(self):
        QMetaObject.invokeMethod(self.player, 'pause')
        
    def slotStateChanged(self, state):
        if state == 1 and self._currentFile:
            # stopped
            if self._currentFileList:
                # if there are other files, load one
                if self._currentFile not in self._currentFileList:
                    self.loadFile(
                        self._currentFileList[self.fileList.currentIndex()])
            else:
                # no updated files to load, just close
                self.player.closeUrl()
        self.pauseButton.setDown(state == 2) # paused?
    
    def slotBeat(self, measnum, beat, measlen):
        self.lcd.display("{0}:{1}".format(measnum, beat))
        
    def state(self):
        """Returns the state of the player."""
        mobj = self.player.metaObject()
        prop = mobj.property(mobj.indexOfProperty('state'))
        return prop.read(self.player)
        
    def isPlaying(self):
        """Returns True if state is playing or paused."""
        return self.state() in (2, 3)
        


            