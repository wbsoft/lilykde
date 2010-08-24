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
Code that manages the progress bar at the bottom of
the Frescobaldi main window
"""

from PyQt4.QtCore import QTimer

_ticks = 10     # ticks per second

class ProgressBarManager(object):
    
    def __init__(self, jobmanager, progressbar):
        self.bar = progressbar
        self.man = jobmanager
        self.timer = QTimer()
        self.hideTimer = QTimer()
        
        self.timer.setInterval(1000 / _ticks)
        self.timer.timeout.connect(self.timeout)
        self.hideTimer.setInterval(3000)
        self.hideTimer.setSingleShot(True)
        self.hideTimer.timeout.connect(self.bar.hide)
        self.man.jobStarted.connect(self.start)
        self.man.jobFinished.connect(self.stop)
        
    def start(self, job):
        """ Call this when a job has started. """
        doc = job.document
        lastruntime = doc.metainfo["build time"]
        if lastruntime == 0.0:
            lastruntime = 3.0 + doc.lines() / 20 # very arbitrary estimate...
        
        if self.man.count() == 1:
            self.hideTimer.stop()
            self.bar.show()
            self.bar.setValue(0)
            self.bar.setMaximum(0)
            self.timer.start()
        self.bar.setMaximum(self.bar.maximum() + int(_ticks * lastruntime))
                
    def stop(self, job, success):
        """ Call this when a job has stopped. """
        if success:
            job.document.metainfo["build time"] = job.buildTime
        
        if self.man.count() == 0:
            self.timer.stop()
            if success:
                self.bar.setValue(self.bar.maximum())
                self.hideTimer.start()
            else:
                self.bar.hide()
                
    def timeout(self):
        self.bar.setValue(self.bar.value() + 1)
        

