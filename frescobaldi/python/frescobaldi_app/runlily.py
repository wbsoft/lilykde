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

""" Code to run LilyPond and display its output in a LogWidget """

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *

from kateshell.mainwindow import listeners

class Ly2PDF():
    def __init__(self, doc, log, preview):
        listeners.add(self.finished)
        
    def finished(self):
        listeners.call(self.finished)
        listeners.remove(self.finished)

    def start(self):
        """ Start the LilyPond job """
        pass # TODO implement

    def abort(self):
        """ Abort the LilyPond job """
        self.finished() # TODO really implement


class LogWidget(QTextEdit):
    def __init__(self, tool, doc):
        QTextEdit.__init__(self, tool.widget)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setText("hello") # TEST
        

