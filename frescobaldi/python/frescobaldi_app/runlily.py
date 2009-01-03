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

import glob, os, re, sys, time

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

from kateshell.mainwindow import listeners
import frescobaldi_app.mainapp

def config(group):
    return KGlobal.config().group(group)

# to find filenames with line:col pairs in LilyPond output
_ly_message_re = re.compile(r"^((.*?):(\d+)(?::(\d+))?)(?=:)", re.M)

class Ly2PDF(object):
    def __init__(self, doc, log, preview):
        listeners.add(self.finished)

        self.log = log
        # save this so the log knows if we built a PDF with point and click:
        self.log.preview = preview      

        lyfile = doc.localPath()
        lvars = doc.variables()
        ly = lvars.get(preview and 'master-preview' or 'master-publish') or lvars.get('master')
        if ly:
            lyfile = os.path.join(os.path.dirname(lyfile), ly)
        self.lyfile = lyfile
        self.basename = os.path.splitext(lyfile)[0]
        self.directory, self.lyfile_arg = os.path.split(lyfile)

        self.p = KProcess()
        self.p.setOutputChannelMode(KProcess.MergedChannels)
        self.p.setWorkingDirectory(self.directory)
        cmd = [config("commands").readEntry("lilypond", "lilypond"), "--pdf"]
        cmd.append(preview and "-dpoint-and-click" or "-dno-point-and-click")
        if config("preferences").readEntry("delete intermediate files",
                                           QVariant(True)).toBool():
            cmd.append("-ddelete-intermediate-files")
        cmd.append(self.lyfile_arg)
        
        self.p.setProgram(cmd)
        QObject.connect(self.p, SIGNAL("finished(int, QProcess::ExitStatus)"),
                        self.finished)
        QObject.connect(self.p, SIGNAL("error(QProcess::ProcessError)"), self.error)
        QObject.connect(self.p, SIGNAL("readyRead()"), self.readOutput)
        
        self.log.clear()
        mode = unicode(preview and i18n("preview mode") or i18n("publish mode"))
        self.log.writeLine(i18n("LilyPond [%1] starting (%2)...", self.lyfile_arg, mode))
        self.startTime = time.time()
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
        # so we see the log message before Okular loads...
        QTimer.singleShot(0, self.bye)
    
    def error(self, errCode):
        """ Called when QProcess encounters an error """
        def w(msg):
            self.log.writeMsg(msg, "msgerr")
        if errCode == QProcess.FailedToStart:
            w(i18n("Could not start LilyPond. Please check path and permissions."))
        elif errCode == QProcess.Crashed:
            w(i18n("LilyPond crashed."))
        elif errCode == QProcess.ReadError:
            w(i18n("Could not read from the LilyPond process."))
        else:
            w(i18n("An unknown error occured."))
        # Otherwise we delete ourselves during our event handler, crashing...
        QTimer.singleShot(0, self.bye)
        
    def bye(self):
        listeners.call(self.finished)
        listeners.remove(self.finished)

    def abort(self):
        """ Abort the LilyPond job """
        self.p.terminate()

    def readOutput(self):
        text = str(self.p.readAllStandardOutput()).decode('utf-8')
        parts = _ly_message_re.split(text)
        # parts has an odd length(1, 6, 11 etc)
        # message, <url, path, line, col, message> etc.
        self.log.write(parts.pop(0))
        if parts:
            self.log.show() # warnings or errors will be printed
        while len(parts[:5]) == 5:
            url, path, line, col, msg = parts[:5]
            path = os.path.join(self.directory, path).encode('utf-8')
            line = int(line or "1") or 1
            col = int(col or "0")
            href = "textedit://%s:%d:%d:%d" % (path, line, col, col)
            self.log.writeUrl(url, href, i18n("Click to edit this file"))
            self.log.write(msg)
            del parts[:5]
    
    def updatedFiles(self):
        """
        Returns a function that can list updated files based on extension.
        """
        return frescobaldi_app.mainapp.updatedFiles(self.lyfile, self.startTime)


class LogWidget(QFrame):
    def __init__(self, tool, doc):
        QFrame.__init__(self, tool.widget)
        self.tool = tool
        self.doc = doc
        self.preview = False # this is used by Ly2PDF and the ActionManager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.textBrowser = QTextBrowser(self)
        self.textBrowser.setFocusPolicy(Qt.NoFocus)
        self.textBrowser.setOpenLinks(False)
        self.textBrowser.setOpenExternalLinks(False)
        QObject.connect(self.textBrowser, SIGNAL("anchorClicked(QUrl)"),
            self.anchorClicked)
        self.formats = textFormats()
        layout.addWidget(self.textBrowser)
        self.actionBar = QToolBar(self)
        self.actionBar.setFloatable(False)
        self.actionBar.setMovable(False)
        self.actionBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.actionBar.setIconSize(QSize(16, 16))
        self.actionBar.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.actionBar)
        self.actionBar.hide()
        # frame style:
        self.setFrameStyle(self.textBrowser.frameStyle())
        self.textBrowser.setFrameStyle(QFrame.NoFrame)
    
    def clear(self):
        self.textBrowser.clear()
        self.actionBar.clear()
        self.actionBar.hide()
    
    def checkScroll(self, func):
        """
        Checks if we were scrolled to the bottom, calls func and then
        again makes sure to scroll to the bottom, if we were.
        """
        sb = self.textBrowser.verticalScrollBar()
        # were we scrolled to the bottom?
        bottom = sb.value() == sb.maximum()
        func()
        # if yes, keep it that way.
        if bottom:
            sb.setValue(sb.maximum())
        
    def write(self, text, format='log'):
        self.textBrowser.setCurrentCharFormat(self.formats[format])
        self.checkScroll(lambda: self.textBrowser.insertPlainText(text))

    def writeMsg(self, text, format='msg'):
        # start on a new line if necessary
        if self.textBrowser.textCursor().columnNumber() > 0:
            self.write('\n', format)
        self.write(text, format)

    def writeLine(self, text, format='msg'):
        self.writeMsg(text + '\n', format)
        
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


def textFormats():
    """ Return a dict with text formats """
    log = QTextCharFormat()
    log.setFontFamily("monospace")
    
    url = QTextCharFormat(log)
    url.setForeground(QBrush(QColor("blue")))
    url.setFontUnderline(True)
    url.setAnchor(True)
    
    msg = QTextCharFormat()
    msg.setFontFamily("sans-serif")
    msg.setFontWeight(QFont.Bold)
    
    msgok = QTextCharFormat(msg)
    msgok.setForeground(QBrush(QColor("green")))
    
    msgerr = QTextCharFormat(msg)
    msgerr.setForeground(QBrush(QColor("red")))
    
    return locals()

