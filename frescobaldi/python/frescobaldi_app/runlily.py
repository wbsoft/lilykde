# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
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

""" Code to run LilyPond and display its output in a LogWidget """

import os, re, time

from PyQt4.QtCore import (
    QObject, QProcess, QSize, QTimer, QUrl, QVariant, Qt, SIGNAL)
from PyQt4.QtGui import (
    QBrush, QColor, QFont, QFrame, QTextBrowser, QTextCharFormat, QTextCursor,
    QToolBar, QVBoxLayout)
from PyKDE4.kdecore import KGlobal, KProcess, i18n

from signals import Signal

import frescobaldi_app.mainapp

def config(group):
    return KGlobal.config().group(group)

# to find filenames with line:col pairs in LilyPond output
_ly_message_re = re.compile(r"^((.*?):(\d+)(?::(\d+))?)(?=:)", re.M)


class Ly2PDF(object):
    """
    An object of this class performs one LilyPond run on a LilyPond file
    given in filename, with output to the LogWidget log.
    
    It emits the signal done(success, self) when the jobs has finished.
    The updatedFiles method then can return a function that returns the
    updated files of a given type.
    """
    preview = False
    def __init__(self, lyfile, log):
        self.done = Signal()
        # save this so the log knows if we built a PDF with point and click:
        log.preview = self.preview
        self.log = log
        
        self.lyfile = lyfile
        self.basename = os.path.splitext(lyfile)[0]
        self.directory, self.lyfile_arg = os.path.split(lyfile)

        self.p = KProcess()
        self.p.setOutputChannelMode(KProcess.MergedChannels)
        self.p.setWorkingDirectory(self.directory)
        cmd = [config("commands").readEntry("lilypond", "lilypond"), "--pdf"]
        cmd.append(self.preview and "-dpoint-and-click" or "-dno-point-and-click")
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
        mode = unicode(self.preview and i18n("preview mode") or i18n("publish mode"))
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
        self.bye(not (exitCode or exitStatus))
    
    def error(self, errCode):
        """ Called when QProcess encounters an error """
        if errCode == QProcess.FailedToStart:
            self.log.writeMsg(i18n(
                "Could not start LilyPond. Please check path and permissions."),
                "msgerr")
        elif errCode == QProcess.ReadError:
            self.log.writeMsg(i18n("Could not read from the LilyPond process."),
                "msgerr")
        elif self.p.state() == QProcess.NotRunning:
            self.log.writeMsg(i18n("An unknown error occured."), "msgerr")
        if self.p.state() == QProcess.NotRunning:
            # otherwise we delete ourselves during our event handler, crashing...
            self.bye(False)
        
    def bye(self, success):
        QTimer.singleShot(0, lambda: self.done(success, self))

    def abort(self):
        """ Abort the LilyPond job """
        self.p.terminate()

    def kill(self):
        """
        Immediately kill the job, and disconnect it's output signals, etc.
        Emits the done(False) signal.
        """
        QObject.disconnect(self.p,
            SIGNAL("finished(int, QProcess::ExitStatus)"), self.finished)
        QObject.disconnect(self.p,
            SIGNAL("error(QProcess::ProcessError)"), self.error)
        QObject.disconnect(self.p, SIGNAL("readyRead()"), self.readOutput)
        self.p.kill()
        print "kill called"#DEBUG
        time.sleep(5)
        print "slept!"
        self.done(False, self)
        
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

    def __del__(self):
        print "job deleted"
        

class LyDoc2PDF(Ly2PDF):
    """
    Runs LilyPond on the given Document.
    """
    def __init__(self, doc, log, preview):
        self.preview = preview
        lyfile = doc.localPath()
        lvars = doc.variables()
        ly = lvars.get(preview and 'master-preview' or 'master-publish') or lvars.get('master')
        if ly:
            lyfile = os.path.join(os.path.dirname(lyfile), ly)
        super(LyDoc2PDF, self).__init__(lyfile, log)
        doc.closed.connect(self.kill)
        

class JobManager(object):
    """
    Manages LilyPond jobs.
    
    Create new jobs with the createJob method.
    (Stop jobs by calling abort() on the job).
    Emits:
    jobStarted(Document)
    jobFinished(Document, success, job)
    """
    def __init__(self, mainwin):
        self.mainwin = mainwin
        self.jobs = {}
        self.jobStarted = Signal()
        self.jobFinished = Signal()
        
    def job(self, doc):
        return self.jobs.get(doc)
    
    def count(self):
        return len(self.jobs)
        
    def docs(self):
        return self.jobs.keys()
        
    def createJob(self, doc, log, preview):
        if doc in self.jobs:
            return
        self.jobs[doc] = LyDoc2PDF(doc, log, preview)
        self.jobStarted(doc)
        def finished(success, job):
            del self.jobs[doc]
            self.jobFinished(doc, success, job)
        self.jobs[doc].done.connect(finished)
        return self.jobs[doc]


class LogWidget(QFrame):
    def __init__(self, parent=None):
        QFrame.__init__(self, parent)
        self.preview = False # this is used by Ly2PDF and the ActionManager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.textBrowser = QTextBrowser(self)
        self.textBrowser.setFocusPolicy(Qt.NoFocus)
        self.textBrowser.setOpenLinks(False)
        self.textBrowser.setOpenExternalLinks(False)
        self.textCursor = QTextCursor(self.textBrowser.document())
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
        self.checkScroll(lambda:
            self.textCursor.insertText(text, self.formats[format]))

    def writeMsg(self, text, format='msg'):
        # start on a new line if necessary
        if self.textCursor.columnNumber() > 0:
            self.write('\n', format)
        self.write(text, format)

    def writeLine(self, text, format='msg'):
        self.writeMsg(text + '\n', format)
        
    def writeUrl(self, text, href, tooltip=None, format='log'):
        self.write(text, format)


class Log(LogWidget):
    """
    A more advanced version of the logwidget, designed for embedding
    in a tool.
    """
    def __init__(self, tool, doc):
        self.tool = tool
        self.doc = doc
        LogWidget.__init__(self, tool.widget)
        QObject.connect(self.textBrowser, SIGNAL("anchorClicked(QUrl)"),
            self.anchorClicked)
    
    def show(self):
        """ Really show our log, e.g. when there are errors """
        self.tool.showLog(self.doc)
        self.tool.show()

    def anchorClicked(self, url):
        self.doc.app.openUrl(url)

    def writeUrl(self, text, href, tooltip=None, format='url'):
        f = self.formats[format]
        f.setAnchorHref(href)
        if tooltip:
            f.setToolTip(tooltip)
        self.write(text, format)


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

