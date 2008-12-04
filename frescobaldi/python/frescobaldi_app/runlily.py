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

import os, re, sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *

from kateshell.mainwindow import listeners

def config(group):
    return KGlobal.config().group(group)

class Ly2PDF(object):
    def __init__(self, doc, log, preview):
        listeners.add(self.finished)

        self.log = log
        lyfile = doc.localPath()
        base = os.path.splitext(lyfile)[0]
        lyfile_arg = os.path.basename(lyfile)

        self.p = KProcess()
        self.p.setOutputChannelMode(KProcess.MergedChannels)
        self.p.setWorkingDirectory(os.path.dirname(lyfile))
        cmd = [config("commands").readEntry("lilypond", "lilypond"), "--pdf"]
        cmd.append(preview and "-dpoint-and-click" or "-dno-point-and-click")
        if config("preferences").readEntry("delete intermediate files",
                                           QVariant(True)).toBool():
            cmd.append("-ddelete-intermediate-files")
        cmd += ["-o", base, lyfile_arg]
        
        # encode arguments correctly
        enc = sys.getfilesystemencoding() or 'utf-8'
        cmd = [unicode(a).encode(enc) for a in cmd]
        
        self.p.setProgram(cmd)
        QObject.connect(self.p, SIGNAL("finished(int, QProcess::ExitStatus)"),
                        self.finished)
        QObject.connect(self.p, SIGNAL("readyRead()"), self.readOutput)
        
        self.log.clear()
        self.log.writeMsg("LilyPond started.\n")
        self.log.show()
        self.p.start()
        
    def finished(self, exitCode, exitStatus):
        self.log.writeMsg("Exited: %d %d" % (exitCode, exitStatus))
        listeners.call(self.finished)
        listeners.remove(self.finished)
        self.p = None

    def abort(self):
        """ Abort the LilyPond job """
        if self.p:
            self.p.terminate()

    def readOutput(self):
        self.log.write(unicode(self.p.readAllStandardOutput()))
    

class LogWidget(QTextBrowser):
    def __init__(self, tool, doc):
        QTextEdit.__init__(self, tool.widget)
        self.tool = tool
        self.doc = doc
        self.setFocusPolicy(Qt.NoFocus)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)

        self.formats = {}
        f = QTextCharFormat()
        f.setFontFamily("monospace")
        self.formats['log'] = f
        
        f = QTextCharFormat()
        f.setFontFamily("sans-serif")
        f.setFontWeight(QFont.Bold)
        self.formats['msg'] = f
        
    def write(self, text, format='log'):
        self.setCurrentCharFormat(self.formats[format])
        self.insertPlainText(text)
        self.ensureCursorVisible()

    def writeMsg(self, text):
        self.write(text, 'msg')
        

    def show(self):
        """ Really show our log, e.g. when there are errors """
        self.tool.showLog(self.doc)
        self.tool.show()
        