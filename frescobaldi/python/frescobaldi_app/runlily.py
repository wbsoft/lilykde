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

import math, os, re, shutil, sys, tempfile, time

from PyQt4.QtCore import (
    QObject, QProcess, QSize, QTimer, QUrl, QVariant, Qt, SIGNAL)
from PyQt4.QtGui import (
    QBrush, QColor, QFont, QFrame, QTextBrowser, QTextCharFormat, QTextCursor,
    QToolBar, QVBoxLayout)
from PyKDE4.kdecore import KGlobal, KProcess, i18n

from signals import Signal

from kateshell.app import resolvetabs_text
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
        self.done = Signal(fireonce=True)
        # save this so the log knows if we built a PDF with point and click:
        log.preview = self.preview
        self.log = log
        
        self.lyfile = lyfile
        self.basename = os.path.splitext(lyfile)[0]
        self.directory, self.lyfile_arg = os.path.split(lyfile)

        self.p = KProcess()
        self.p.setOutputChannelMode(KProcess.MergedChannels)
        self.p.setWorkingDirectory(self.directory)
        cmd = [config("commands").readEntry("lilypond", QVariant("lilypond")).toString(), "--pdf"]
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
        self.startTime = math.floor(time.time())
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
            self.bye(False)
        
    def bye(self, success):
        # otherwise we delete ourselves during our event handler, causing crash
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
        self.p.waitForFinished(2000)
        self.done(False, self)
        
    def readOutput(self):
        encoding = sys.getfilesystemencoding() or 'utf-8'
        text = str(self.p.readAllStandardOutput()).decode(encoding)
        parts = _ly_message_re.split(text)
        # parts has an odd length(1, 6, 11 etc)
        # message, <url, path, line, col, message> etc.
        self.log.write(parts.pop(0))
        if parts:
            self.log.show() # warnings or errors will be printed
        while len(parts[:5]) == 5:
            url, path, line, col, msg = parts[:5]
            path = os.path.join(self.directory, path)
            line = int(line or "1") or 1
            col = int(col or "0")
            self.log.writeFileRef(url, path, line, col)
            self.log.write(msg)
            del parts[:5]
    
    def updatedFiles(self):
        """
        Returns a function that can list updated files based on extension.
        """
        return frescobaldi_app.mainapp.updatedFiles(self.lyfile, self.startTime)
        

class LyDoc2PDF(Ly2PDF):
    """
    Runs LilyPond on the given Document.
    """
    def __init__(self, doc, log, preview):
        self.preview = preview
        if doc.needsLocalFileManager():
            # handle nonlocal or unnamed documents
            lyfile = doc.localFileManager(True).makeLocalFile()
        else:
            lyfile = doc.localPath()
            lvars = doc.variables()
            ly = (lvars.get(preview and 'master-preview' or 'master-publish')
                  or lvars.get('master'))
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
        
    def writeFileRef(self, text, path, line, column, tooltip=None, format='log'):
        self.write(text, format)


class Log(LogWidget):
    """
    A more advanced version of the logwidget, designed for embedding
    in a tool.
    """
    def __init__(self, tool, doc):
        self.tool = tool
        self.doc = doc
        self.anchors = {}
        self.anchorgen = anchorgen().next
        LogWidget.__init__(self, tool.widget)
        QObject.connect(self.textBrowser, SIGNAL("anchorClicked(QUrl)"),
            self.anchorClicked)
    
    def clear(self):
        self.anchors.clear()
        self.anchorgen = anchorgen().next
        super(Log, self).clear()
        
    def show(self):
        """ Really show our log, e.g. when there are errors """
        self.tool.showLog(self.doc)
        self.tool.show()

    def writeFileRef(self, text, path, line, column, tooltip=None, format='url'):
        anchor = self.anchorgen()
        self.anchors[anchor] = FileRef(self.doc.app, path, line, column)
        f = self.formats[format]
        f.setAnchorHref(anchor)
        f.setToolTip(tooltip or i18n("Click to edit this file"))
        self.write(text, format)
    
    def anchorClicked(self, url):
        ref = self.anchors.get(str(url.path()))
        if ref:
            ref.activate()
    

class FileRef(object):
    """
    A reference to a file position (name, line, column).
    Contacts documents if loaded and uses smart cursors to maintain the
    position if the document is changed.
    
    Also listens to the application if a document is opened that might be
    interesting for us.
    """
    def __init__(self, app, path, line, column):
        self.path = path
        self.line = line
        self.column = column
        
        self.smartCursor = None
        self.doc = None
        
        # listen to the application:
        self.app = app
        self.app.documentMaterialized.connect(self.documentOpened)
        # if named doc is loaded get a smart cursor
        doc = self.app.findDocument(path)
        if doc:
            self.bind(doc)
        
    def bind(self, doc):
        """
        Connects to the document (that must have our path) and tries
        to get a SmartCursor from it.
        If the document is closed, the binding is deleted.
        TODO: update our cursor pos before document is closed...
        """
        if doc.doc:
            iface = doc.doc.smartInterface()
            if iface:
                column = resolvetabs_text(self.column, doc.line(self.line - 1))
                iface.smartMutex().lock()
                iface.clearRevision()
                self.smartCursor = iface.newSmartCursor(self.line - 1, column)
                iface.smartMutex().unlock()
                self.doc = doc
                doc.closed.connect(self.unbind)
                doc.urlChanged.connect(self.unbind)
                # no need to listen anymore
                self.app.documentMaterialized.disconnect(self.documentOpened)
    
    def unbind(self):
        """
        Deletes the binding to a document.
        """
        self.doc.closed.disconnect(self.unbind)
        self.doc.urlChanged.disconnect(self.unbind)
        self.smartCursor = None
        self.doc = None
        # listen again
        self.app.documentMaterialized.connect(self.documentOpened)
        
    def activate(self):
        """
        Open our file and put the cursor in the right place.
        """
        doc = self.doc or self.app.openUrl(self.path)
        doc.setActive() # this binds our document! (via documentMaterialized)
        # If we're still not bound, it's because there wasn't a smartInterface.
        # In that case we just position the cursor ourselves.
        if self.doc:
            self.doc.view.setCursorPosition(self.smartCursor)
        else:
            doc.setCursorPosition(self.line, self.column, translate=False)

    def documentOpened(self, doc):
        if not self.doc and doc.localPath() == self.path:
            self.bind(doc)


class LocalFileManager(object):
    """
    Manages the local storage of remote or unnamed LilyPond files,
    so LilyPond can be run on those files.
    This is instantiated upon request (to save a remote or unnamed LilyPond
    document to a local file), and is deleted (by the Document) as soon as the
    url of the document changes or the document closes.
    """
    def __init__(self, doc):
        self.doc = doc
        self.directory = tempfile.mkdtemp()
        path = unicode(self.doc.url().path())
        self.filename = path and os.path.basename(path) or "music.ly"

    def __del__(self):
        shutil.rmtree(self.directory, ignore_errors=True)
        
    def path(self):
        """
        Return the path, without actually saving the document contents.
        """
        return os.path.join(self.directory, self.filename)
        
    def makeLocalFile(self):
        """
        Return the path of the LilyPond file the unnamed or remote
        file is cached to.  If needed the contents of the document are saved
        into this file as well.
        """
        lyfile = self.path()
        # Save the file to our local storage
        # TODO: error handling
        file(lyfile, 'w').write(self.doc.text().encode(self.doc.encoding() or 'utf-8'))
        return lyfile
 

def textFormats():
    """ Return a dict with text formats for the log view """
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


def anchorgen(num = 0):
    """
    Generates an infinite row of anchor names, named
    "anchor0", "anchor1", etc.
    """
    while True:
        yield "anchor%d" % num
        num += 1
