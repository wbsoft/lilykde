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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kparts import KParts



class Player(QWidget):
    
    def __init__(self, tool):
        super(Player, self).__init__(tool.mainwin)
        self.player = None
        
        layout = QGridLayout()
        self.setLayout(layout)
        
        # load the KMid Part
        factory = KPluginLoader("kmid_part").factory()
        if factory:
            part = factory.create(self)
            if part:
                self.player = part
                self.widget = part.widget()
                layout.addWidget(self.widget, 0, 0, 1, 1)
                
                # set auto start off
                mobj = part.metaObject()
                prop = mobj.property(mobj.indexOfProperty('autoStart'))
                prop.write(part, False)
        
        if not self.player:
            label = QLabel(i18n(
                "Could not load the KMid part.\n"
                "Please install KMid 2.4.0 or higher."))
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
    
        
    def setCurrentDocument(self, doc):
        """ Called when the current document changes. """
        self.setMidiFiles(doc.updatedFiles()("mid*"))
        
    def jobFinished(self, job):
        """ Called when a LilyPond job finishes. """
        self.setMidiFiles(job.updatedFiles()("mid*"))
    
    def quit(self):
        """Called when the application exits."""
        
    def setMidiFiles(self, files):
        """ Sets the list of MIDI files that can be played. """
        if not files or not self.player:
            return
            
        self.player.openUrl(KUrl(files[0]))
        



            