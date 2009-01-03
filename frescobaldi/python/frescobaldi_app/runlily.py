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

def config(group):
    return KGlobal.config().group(group)

# to find filenames with line:col pairs in LilyPond output
_ly_message_re = re.compile(r"^((.*?):(\d+)(?::(\d+))?)(?=:)", re.M)

class Ly2PDF(object):
    def __init__(self, doc, log, preview):
        listeners.add(self.finished)

        self.log = log

        lyfile = doc.localPath()
        lvars = doc.variables()
        ly = lvars.get(preview and 'master-preview' or 'master-publish') or lvars.get('master')
        if ly:
            lyfile = os.path.join(os.path.dirname(lyfile), ly)
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
        self.log.updateActions(self)
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
    
    def updatedFiles(self, ext="*"):
        """
        Returns a list of files updated by this process, with given
        extension.
        """
        files = glob.glob(self.basename + "." + ext)
        files += glob.glob(self.basename + "?*." + ext)
        return [f for f in files if os.path.getmtime(f) >= self.startTime]


class LogWidget(QWidget):
    def __init__(self, tool, doc):
        QWidget.__init__(self, tool.widget)
        self.tool = tool
        self.doc = doc
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
        self.actionBar = ActionBar(self)
        layout.addWidget(self.actionBar)
        self.actionBar.hide()
    
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

    def updateActions(self, job):
        """
        Updates the list of actions that are possible after this LilyPond
        run. If any files are updated, a button or menu is created and
        the action bar is shown.
        The job object should have a method updatedFiles(ext) to get the
        files that were updated by that job.
        """
        if self.actionBar.updateActions(job):
            self.checkScroll(self.actionBar.show)
        

class ActionBar(QToolBar):
    def __init__(self, parent):
        QToolBar.__init__(self, parent)
        self.setFloatable(False)
        self.setMovable(False)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QSize(16, 16))
        
    def updateActions(self, job):
        """
        Updates the list of actions that are possible after this LilyPond
        run. If any files are updated, a suitable button or menu is created.
        The job object should have a method updatedFiles(ext) to get the
        files that were updated by that job.
        Returns True if there are any actions.
        """
        self.clear()
        pdfs = job.updatedFiles("pdf")
        if pdfs:
            a = self.addAction(KIcon("application-pdf"), i18n("Open PDF"))
        
        return bool(len(self.actions()))
        


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
