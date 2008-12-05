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

# to find filenames with line:col pairs in LilyPond output
_ly_message_re = re.compile(r"^((.*?):(\d+)(?::(\d+))?)(?=:)", re.M)

class Ly2PDF(object):
    def __init__(self, doc, log, preview):
        listeners.add(self.finished)

        self.log = log
        lyfile = doc.localPath()
        base = os.path.splitext(lyfile)[0]
        self.lyfile_arg = os.path.basename(lyfile)
        self.directory = os.path.dirname(lyfile)

        self.p = KProcess()
        self.p.setOutputChannelMode(KProcess.MergedChannels)
        self.p.setWorkingDirectory(self.directory)
        cmd = [config("commands").readEntry("lilypond", "lilypond"), "--pdf"]
        cmd.append(preview and "-dpoint-and-click" or "-dno-point-and-click")
        if config("preferences").readEntry("delete intermediate files",
                                           QVariant(True)).toBool():
            cmd.append("-ddelete-intermediate-files")
        cmd += ["-o", base, self.lyfile_arg]
        
        # encode arguments correctly
        enc = sys.getfilesystemencoding() or 'utf-8'
        cmd = [unicode(a).encode(enc) for a in cmd]
        
        self.p.setProgram(cmd)
        QObject.connect(self.p, SIGNAL("finished(int, QProcess::ExitStatus)"),
                        self.finished)
        QObject.connect(self.p, SIGNAL("readyRead()"), self.readOutput)
        
        self.log.clear()
        mode = unicode(preview and i18n("preview") or i18n("publish"))
        self.log.writeMsg(i18n("LilyPond [%1] starting (%2)...\n", self.lyfile_arg, mode))
        self.log.show()
        self.p.start()
        
    def finished(self, exitCode, exitStatus):
        if exitCode:
            self.log.writeMsg(i18n("LilyPond [%1] exited with return code %2.",
                self.lyfile_arg, exitCode), "msgerr")
        elif exitStatus:
            self.log.writeMsg(i18n("LilyPond [%1] exited with exit status %2.",
                self.lyfile_arg, exitStatus), "msgerr")
        else:
            self.log.writeMsg(i18n("LilyPond [%1] finished.", self.lyfile_arg),
                "msgok")
        listeners.call(self.finished)
        listeners.remove(self.finished)
        self.p = None

    def abort(self):
        """ Abort the LilyPond job """
        if self.p:
            self.p.terminate()

    def readOutput(self):
        text = unicode(self.p.readAllStandardOutput())
        parts = _ly_message_re.split(text)
        # parts has an odd length(1, 6, 11 etc)
        # message, <url, path, line, col, message> etc.
        self.log.write(parts.pop(0))
        while len(parts[:5]) == 5:
            url, path, line, col, msg = parts[:5]
            path = os.path.join(self.directory, path)
            line = int(line or "1") or 1
            col = int(col or "0")
            href = "textedit://%s:%d:%d:%d" % (path, line, col, col)
            self.log.writeUrl(url, href, i18n("Click to edit this file"))
            self.log.write(msg)
            del parts[:5]
    

class LogWidget(QTextBrowser):
    def __init__(self, tool, doc):
        QTextEdit.__init__(self, tool.widget)
        self.tool = tool
        self.doc = doc
        self.setFocusPolicy(Qt.NoFocus)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        QObject.connect(self, SIGNAL("anchorClicked(QUrl)"), self.anchorClicked)

        self.formats = {}
        
        f = QTextCharFormat()
        f.setFontFamily("monospace")
        self.formats['log'] = f
        
        f = QTextCharFormat()
        f.setFontFamily("monospace")
        f.setForeground(QBrush(QColor("blue")))
        f.setFontUnderline(True)
        f.setAnchor(True)
        self.formats['url'] = f
        
        f = QTextCharFormat()
        f.setFontFamily("sans-serif")
        f.setFontWeight(QFont.Bold)
        self.formats['msg'] = f
        
        f = QTextCharFormat()
        f.setFontFamily("sans-serif")
        f.setFontWeight(QFont.Bold)
        f.setForeground(QBrush(QColor("green")))
        self.formats['msgok'] = f
        
        f = QTextCharFormat()
        f.setFontFamily("sans-serif")
        f.setFontWeight(QFont.Bold)
        f.setForeground(QBrush(QColor("red")))
        self.formats['msgerr'] = f
        
    def write(self, text, format='log'):
        self.setCurrentCharFormat(self.formats[format])
        sb = self.verticalScrollBar()
        # were we scrolled to the bottom?
        bottom = sb.value() == sb.maximum()
        self.insertPlainText(text)
        # if yes, keep it that way.
        if bottom:
            sb.setValue(sb.maximum())

    def writeMsg(self, text, format='msg'):
        # start on a new line if necessary
        if self.textCursor().columnNumber() > 0:
            self.write('\n', format)
        self.write(text, format)

    def writeUrl(self, text, href, tooltip=None, format='url'):
        f = self.formats[format]
        f.setAnchorHref(href)
        if tooltip:
            f.setToolTip(tooltip)
        self.write(text, format)

    def show(self):
        """ Really show our log, e.g. when there are errors """
        self.tool.showLog(self.doc)
        self.tool.show()

    def anchorClicked(self, url):
        url = unicode(url.toString())
        self.doc.app.openUrl(url)
