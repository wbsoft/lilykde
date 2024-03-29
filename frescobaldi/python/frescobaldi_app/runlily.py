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

""" Code to run LilyPond and display its output in a LogWidget """

import math, os, re, shutil, sys, tempfile, time
from itertools import count, repeat

from PyQt4.QtCore import QProcess, QSize, QTimer, QUrl, Qt
from PyQt4.QtGui import (
    QBrush, QCheckBox, QColor, QFont, QLabel, QListWidget, QListWidgetItem,
    QStackedWidget, QTextBrowser, QTextCharFormat, QTextCursor, QVBoxLayout,
    QWidget)
from PyKDE4.kdecore import KGlobal, KPluginLoader, KProcess, KUrl, i18n
from PyKDE4.kdeui import (
    KApplication, KDialog, KIcon, KMenu, KMessageBox, KStandardGuiItem)
from PyKDE4.kio import KEncodingFileDialog

from signals import Signal, SignalProxy

from kateshell.app import resolvetabs_text
from frescobaldi_app.actions import openPDF
from frescobaldi_app.mainapp import (
    automaticLilyPondCommand, lilyPondCommand, lilyPondVersion, updatedFiles)


def config(group):
    return KGlobal.config().group(group)

# to find filenames with line:col pairs in LilyPond output
_ly_message_re = re.compile(r"^((.*?):(\d+)(?::(\d+))?)(?=:)", re.M)


class BasicLilyPondJob(object):
    """
    Performs one job to run LilyPond.
    
    Set different parameters and then call start() to start.
    The Signal done(success, self) is emitted when the job has finished.
    The SignalProxy output(msg, type, newline=False) is emitted when there is output
    (stderr and stdout).  This proxy is called like Log and LogWidget.
    Don't use (Basic)LilyPondJob for more than one run.
    """
    
    # these are default values for attributes that can be set:
    
    command = "lilypond"        # lilypond command to run
    arguments = ["--pdf"]       # arguments
    include = []                # directories to add to include path
    lyfile = None               # lilypond document filename to run on
    
    preview = False             # run with point and click
    verbose = False             # run with --verbose
    delfiles = True             # delete intermediate files
    
    startTime = 0.0             # time.time() this job started
    buildTime = 0.0             # time in seconds this job has been running
    
    done = Signal(fireOnce=True)
    output = SignalProxy()
    
    def __init__(self):
        pass
        
    def start(self):
        """ Starts the process. """
        # save some values
        self._directory, self._basename = os.path.split(self.lyfile)
        
        # construct the full LilyPond command.
        cmd = [self.command]
        self.verbose and cmd.append("--verbose")
        cmd.append("-dpoint-and-click=" + scmbool(self.preview))
        cmd.append("-ddelete-intermediate-files=" + scmbool(self.delfiles))
        for path in self.include:
            cmd.append("--include")
            cmd.append(path)
        cmd.extend(self.arguments)
        cmd.append(self._basename)
        
        # create KProcess instance that does the work
        p = self._p = KProcess()
        p.setOutputChannelMode(KProcess.MergedChannels)
        p.setWorkingDirectory(self._directory)
        p.setProgram(cmd)
        p.finished.connect(self._finished)
        p.error.connect(self._error)
        p.readyRead.connect(self._readOutput)
        
        mode = i18n("preview mode") if self.preview else i18n("publish mode")
        version = lilyPondVersion(self.command)
        if version:
            self.output.writeLine(i18n("LilyPond %1 [%2] starting (%3)...",
                format(version), self._basename, mode))
        else:
            self.output.writeLine(i18n("LilyPond [%1] starting (%2)...",
                self._basename, mode))
        
        self.startTime = time.time()
        p.start()
    
    def _exit(self, success):
        """ Called when the job is finished (successfully or not).
        
        Emits the done(success, self) signal.
        
        """
        self.buildTime = time.time() - self.startTime
        self.done(success, self)
        
    def abort(self):
        """ Abort the LilyPond job """
        self._p.terminate()

    def kill(self):
        """ Immediately kill the job, and disconnect it's output signals, etc.
        
        Will exit the job with success = False.
        
        """
        self._p.finished.disconnect(self._finished)
        self._p.error.disconnect(self._error)
        self._p.readyRead.disconnect(self._readOutput)
        self._p.kill()
        self._p.waitForFinished(2000)
        self._exit(False)
        
    def _finished(self, exitCode, exitStatus):
        if exitCode:
            self.output.writeMsg(i18n("LilyPond [%1] exited with return code %2.",
                self._basename, exitCode), "msgerr")
        elif exitStatus:
            self.output.writeMsg(i18n("LilyPond [%1] exited with exit status %2.",
                self._basename, exitStatus), "msgerr")
        else:
            # We finished successfully, show elapsed time...
            minutes, seconds = divmod(time.time() - self.startTime, 60)
            f = "{0:.0f}'{1:.0f}\"" if minutes else '{1:.1f}"'
            self.output.writeMsg(i18n("LilyPond [%1] finished (%2).",
                self._basename, f.format(minutes, seconds)), "msgok")
        
        # otherwise we delete ourselves during our event handler, causing crash
        QTimer.singleShot(0, lambda: self._exit(not (exitCode or exitStatus)))
    
    def _error(self, errCode):
        """ Called when QProcess encounters an error """
        if errCode == QProcess.FailedToStart:
            self.output.writeMsg(i18n(
                "Could not start LilyPond. Please check path and permissions."),
                "msgerr")
        elif errCode == QProcess.ReadError:
            self.output.writeMsg(i18n("Could not read from the LilyPond process."),
                "msgerr")
        elif self._p.state() == QProcess.NotRunning:
            self.output.writeMsg(i18n("An unknown error occured."), "msgerr")
        if self._p.state() == QProcess.NotRunning:
            # otherwise we delete ourselves during our event handler, causing crash
            QTimer.singleShot(0, lambda: self._exit(False))
        
    def _readOutput(self):
        encoding = sys.getfilesystemencoding() or 'utf-8'
        text = str(self._p.readAllStandardOutput()).decode(encoding, 'replace')
        parts = iter(_ly_message_re.split(text))
        # parts has an odd length(1, 6, 11 etc)
        # message, <url, path, line, col, message> etc.
        self.output.write(next(parts))
        for url, path, line, col, msg in zip(*repeat(parts, 5)):
            path = os.path.join(self._directory, path)
            line = int(line or "1") or 1
            col = int(col or "0")
            self.output.writeFileRef(url, path, line, col)
            self.output.write(msg)
    
    def updatedFiles(self):
        """
        Returns a function that can list updated files based on extension.
        """
        return updatedFiles(self.lyfile, math.floor(self.startTime))


class LilyPondJob(BasicLilyPondJob):
    """
    A LilyPondJob with default settings from Frescobaldi config.
    """
    def __init__(self):
        super(LilyPondJob, self).__init__()
        self.command = lilyPondCommand()
        self.arguments = ["--pdf"]
        self.verbose = config("preferences").readEntry("verbose lilypond output", False)
        self.delfiles = config("preferences").readEntry("delete intermediate files", True)
        self.include = config("preferences").readPathEntry("lilypond include path", [])


class DocumentJob(LilyPondJob):
    """
    A job to be run on a Document instance.
    The document is available in the document attribute.
    """
    document = None
    
    def __init__(self, doc=None):
        self.document = doc
        super(DocumentJob, self).__init__()
        
    def start(self):
        if self.document.needsLocalFileManager():
            # handle nonlocal or unnamed documents
            lyfile = self.document.localFileManager(True).makeLocalFile()
        else:
            # look for %%master directives
            lyfile = self.document.localPath()
            lvars = self.document.variables()
            ly = (lvars.get(self.preview and 'master-preview' or 'master-publish')
                  or lvars.get('master'))
            if ly:
                lyfile = os.path.join(os.path.dirname(lyfile), ly)
        self.lyfile = lyfile
        self.document.closed.connect(self.kill)
        super(DocumentJob, self).start()


class RunLilyPondDialog(KDialog):
    """
    A dialog where a DocumentJob can be configured before it's started.
    """
    def __init__(self, mainwin):
        self.mainwin = mainwin
        KDialog.__init__(self, mainwin)
        self.setCaption(i18n("Run LilyPond"))
        self.setButtons(KDialog.ButtonCode(
            KDialog.Help | KDialog.Ok | KDialog.Cancel ))
        self.setButtonText(KDialog.Ok, i18n("Run LilyPond"))
        self.setButtonIcon(KDialog.Ok, KIcon("run-lilypond"))
        self.setHelp("running")
        
        layout = QVBoxLayout(self.mainWidget())
        
        layout.addWidget(QLabel(i18n(
            "Select which LilyPond version you want to run:")))
            
        self.lilypond = QListWidget()
        self.lilypond.setIconSize(QSize(22, 22))
        self.lilypond.setSpacing(4)
        layout.addWidget(self.lilypond)
        
        self.preview = QCheckBox(i18n(
            "Run LilyPond in preview mode (with Point and Click)"))
        layout.addWidget(self.preview)
        
        self.verbose = QCheckBox(i18n("Run LilyPond with verbose output"))
        layout.addWidget(self.verbose)
        
    def configureJob(self, job, doc=None):
        """Configure a job, belonging to document.
        
        If the document is not given, it is expected to live in the document
        attribute of the job. If there is already a job running, we just display,
        but disable the Run button, until the old job finishes.
        """
        doc = doc or job.document
        
        # populate the dialog based on remembered settings for this document
        self.lilypond.clear()
        
        # find the configured lilypond versions
        conf = config("lilypond")
        paths = conf.readEntry("paths", ["lilypond"]) or ["lilypond"]
        default = conf.readEntry("default", "lilypond")
        
        import ly.version
        
        # get all versions
        ver = dict((path, lilyPondVersion(path)) for path in paths)
        
        # default
        if default not in paths:
            default = paths[0]
            
        # Sort on version
        paths.sort(key=ver.get)
        versions = [format(ver.get(p)) for p in paths]
        
        # Determine automatic version (lowest possible)
        autopath = None
        docVersion = doc.lilyPondVersion()
        if docVersion:
            autopath = automaticLilyPondCommand(docVersion)
        
        def addItem(version, path, icon, title, tooltip):
            item = QListWidgetItem(self.lilypond)
            item.setIcon(KIcon(icon))
            item.setText("{0}\n{1}: {2}".format(title, i18n("Command"), path))
            item.setToolTip(tooltip)
            version or item.setFlags(Qt.NoItemFlags)
        
        # Add all available LilyPond versions:
        for path in paths:
            if ver[path]:
                title = i18n("LilyPond %1", format(ver[path]))
                tooltip = i18n("Use LilyPond version %1", format(ver[path]))
                addenda, tips = [], []
                if path == default:
                    addenda.append(i18n("default"))
                    tips.append(i18n("Default LilyPond Version."))
                if path == autopath:
                    addenda.append(i18n("automatic"))
                    tips.append(i18n("Automatic LilyPond Version (determined from document)."))
                if addenda:
                    title += " [{0}]".format(", ".join(addenda))
                    tooltip += "\n{0}".format("\n".join(tips))
                addItem(format(ver[path]), path, "run-lilypond", title,
                    tooltip + "\n" + i18n("Path: %1",
                        ly.version.LilyPondInstance(path).command() or path))
            else:
                addItem("", path, "dialog-error",
                    i18n("LilyPond (version unknown)"),
                    i18n("Use LilyPond (version unknown)\nPath: %1",
                        ly.version.LilyPondInstance(path).command() or path))
        
        # Copy the settings from the document:
        self.preview.setChecked(doc.metainfo["custom preview"])
        self.verbose.setChecked(doc.metainfo["custom verbose"])
        
        try:
            self.lilypond.setCurrentRow(versions.index(
                doc.metainfo["custom lilypond version"]))
        except ValueError:
            cmd = autopath if autopath and conf.readEntry("automatic version",
                False) else default
            self.lilypond.setCurrentRow(paths.index(cmd))
            
        # Focus our listbox:
        self.lilypond.setFocus()
        
        # Disable the Run button if a job is running for this document
        oldjob = self.mainwin.jobManager().job(doc)
        self.enableButtonOk(not oldjob)
        if oldjob:
            enable = lambda: self.enableButtonOk(True)
            oldjob.done.connect(enable)
        
        # Wait for user interaction:
        result = self.exec_()
        
        # If a job was running, don't listen to it anymore
        if oldjob:
            oldjob.done.disconnect(enable)
        
        if not result:
            return False # cancelled
        
        # Save the settings in the document's metainfo and configure job:
        doc.metainfo["custom preview"] = job.preview = self.preview.isChecked()
        doc.metainfo["custom verbose"] = job.verbose = self.verbose.isChecked()
        index = self.lilypond.currentRow()
        doc.metainfo["custom lilypond version"] = versions[index]
        job.command = paths[index]
        return True


class LogWidget(QTextBrowser):
    
    def __init__(self, parent=None):
        QTextBrowser.__init__(self, parent)
        self.setFocusPolicy(Qt.NoFocus)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.insertCursor = QTextCursor(self.document())
        self.formats = textFormats()
    
    def checkScroll(self, func):
        """
        Checks if we were scrolled to the bottom, calls func and then
        again makes sure to scroll to the bottom, if we were.
        """
        sb = self.verticalScrollBar()
        # were we scrolled to the bottom?
        bottom = sb.value() == sb.maximum()
        func()
        # if yes, keep it that way.
        if bottom:
            sb.setValue(sb.maximum())
        
    def write(self, text, format='log'):
        self.checkScroll(lambda:
            self.insertCursor.insertText(text, self.formats[format]))

    def writeMsg(self, text, format='msg'):
        # start on a new line if necessary
        if self.insertCursor.columnNumber() > 0:
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
        self.anchorgen = anchorgen()
        LogWidget.__init__(self, tool.widget)
        self.anchorClicked.connect(self.slotAnchorClicked)
        # context menu:
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
    
    def clear(self):
        self.anchors.clear()
        self.anchorgen = anchorgen()
        super(Log, self).clear()
        
    def show(self):
        """ Really show our log, e.g. when there are errors """
        self.tool.showLog(self.doc)
        self.tool.show()

    def writeFileRef(self, text, path, line, column, tooltip=None, format='url'):
        anchor = next(self.anchorgen)
        self.anchors[anchor] = FileRef(self.doc.app, path, line, column)
        f = self.formats[format]
        f.setAnchorHref(anchor)
        f.setToolTip(tooltip or i18n("Click to edit this file"))
        self.write(text, format)
        self.show() # because this refers to a warning or error
    
    def slotAnchorClicked(self, url):
        ref = self.anchors.get(str(url.path()))
        if ref:
            ref.activate()
    
    def showContextMenu(self, pos):
        m = KMenu(self)
        m.aboutToHide.connect(m.deleteLater)
        m.addTitle(i18n("LilyPond Log"))
        self.addContextMenuActions(m)
        m.popup(self.mapToGlobal(pos))
        
    def addContextMenuActions(self, menu):
        a = menu.addAction(KIcon("edit-copy"), i18n("&Copy"))
        a.triggered.connect(self.copyLog)
        g = KStandardGuiItem.saveAs()
        a = menu.addAction(g.icon(), g.text())
        a.triggered.connect(self.saveLogAs)

    def copyLog(self):
        text = (self.textCursor().selection().toPlainText()
                or self.toPlainText())
        if text:
            KApplication.clipboard().setText(text)
        
    def saveLogAs(self):
        startDir, fileName = os.path.split(self.doc.localPath())
        fileName = (os.path.splitext(fileName)[0] or "lilypond") + ".log"
        dlg = KEncodingFileDialog(startDir, 'utf-8', '',
            i18n("Save LilyPond Log as"),
            KEncodingFileDialog.Saving, self)
        dlg.setSelection(fileName)
        dlg.setConfirmOverwrite(True)
        if not dlg.exec_():
            return # Cancelled
        encoding = dlg.selectedEncoding()
        fileName = dlg.selectedFile()
        text = (self.textCursor().selection().toPlainText()
                or self.toPlainText())
        try:
            with open(fileName, 'w') as f:
                f.write(text.encode(encoding, 'replace'))
                f.write('\n')
        except (OSError, IOError) as e:
            KMessageBox.error(self,
                i18n("Could not save LilyPond log:\n\n%1", unicode(e)))


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
        path = self.doc.url().path()
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
        with open(lyfile, 'w') as f:
            f.write(self.doc.text().encode(self.doc.encoding() or 'utf-8'))
        return lyfile
 

class BackgroundJob(object):
    """
    Manages LilyPond jobs in the background. Can display a dialog with the log
    output if there was an error.
    Subclass this at your liking.
    """
    def __init__(self, log=None):
        self.log = log or LogWidget()
        self._directory = None
        self.job = None
        
    def directory(self):
        if self._directory is None:
            self._directory = tempfile.mkdtemp()
        return self._directory
        
    def run(self, text, fileName='output.ly'):
        lyfile = os.path.join(self.directory(), fileName)
        with open(lyfile, 'w') as f:
            f.write(text.encode('utf-8'))
        self.log.clear()
        # ... and run LilyPond.
        job = self.job = LilyPondJob()
        job.lyfile = lyfile
        job.output.connect(self.log)
        job.done.connect(self.finished)
        job.start()
    
    def finished(self):
        """
        Called when the job is done.
        """
        pass
    
    def cleanup(self):
        """
        Stop a job if running and remove temporary files.
        """
        if self.job:
            self.job.done.disconnect(self.finished)
            self.job.abort()
            self.job = None
        if self._directory:
            shutil.rmtree(self._directory)
            self._directory = None
    
    def showLog(self, message, title='', parent=None):
        """
        Show the log in a simple modal dialog.
        """
        dlg = KDialog(parent)
        if title:
            dlg.setCaption(title)
        dlg.setButtons(KDialog.ButtonCode(KDialog.Close))
        dlg.setMainWidget(self.log)
        self.log.writeMsg(message, 'msgerr')
        dlg.setInitialSize(QSize(500, 300))
        return dlg.exec_()
            

class LilyPreviewWidget(BackgroundJob, QStackedWidget):
    """
    A widget that can display a string of LilyPond code as a PDF.
    If the code is changed, the PDF is automagically rebuilt.
    Also the signal done(success) is then emitted.
    """
    def __init__(self, *args):
        QStackedWidget.__init__(self, *args)
        BackgroundJob.__init__(self)
        # The widget stack has two widgets, a log and a PDF preview.
        # the Log is already created in BackgroundJob
        self.addWidget(self.log)
        self.setCurrentWidget(self.log)
        
        # the PDF preview, load Okular part.
        # If not, we just run the default PDF viewer.
        self.part = None
        factory = KPluginLoader("okularpart").factory()
        if factory:
            part = factory.create(self)
            if part:
                self.part = part
                self.addWidget(part.widget())
                self.setCurrentWidget(part.widget())
                # hide mini pager
                w = part.widget().findChild(QWidget, "miniBar")
                if w:
                    w.parent().hide()
                # hide left panel
                a = part.actionCollection().action("show_leftpanel")
                if a and a.isChecked():
                    a.toggle()
                # default to single page layout
                a = part.actionCollection().action("view_render_mode_single")
                if a and not a.isChecked():
                    a.trigger()
                # change shortcut context for this one (bound to Esc)
                a = part.actionCollection().action("close_find_bar")
                if a:
                    a.setShortcutContext(Qt.WidgetShortcut)
            
    def preview(self, text):
        """
        Runs LilyPond on the text and update the preview.
        """
        if self.job:
            self.job.disconnect(self.finished)
            self.job.abort()
        self.run(text, 'preview.ly')
        self.setCurrentWidget(self.log)
    
    def finished(self):
        pdfs = self.job.updatedFiles()("pdf")
        if pdfs:
            self.openPDF(pdfs[0])
        self.job = None

    def openPDF(self, fileName):
        if self.part:
            if self.part.openUrl(KUrl.fromPath(fileName)):
                self.setCurrentWidget(self.part.widget())
        else:
            openPDF(fileName, self.window())

    
class LilyPreviewDialog(KDialog):
    def __init__(self, parent):
        KDialog.__init__(self, parent)
        self.setCaption(i18n("PDF Preview"))
        self.setButtons(KDialog.ButtonCode(KDialog.Close))
        self.preview = LilyPreviewWidget(self)
        self.setMainWidget(self.preview)
        self.setMinimumSize(QSize(400, 300))
        self.loadSettings()
        self.finished.connect(self.slotFinished)
        
    def loadSettings(self):
        self.restoreDialogSize(config("preview dialog"))
        
    def saveSettings(self):
        self.saveDialogSize(config("preview dialog"))
        
    def slotFinished(self):
        self.saveSettings()
        self.preview.cleanup()
    
    def showPreview(self, ly):
        self.preview.preview(ly)
        self.exec_()



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
    for num in count(num):
        yield "anchor{0}".format(num)


def scmbool(value):
    """
    Returns the Scheme notation for the boolean value.
    """
    return "#t" if value else "#f"

