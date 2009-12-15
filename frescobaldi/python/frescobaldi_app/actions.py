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

"""
Actions (that can be performed on files generated by running LilyPond)
"""

import os, sip
from subprocess import Popen, PIPE

from PyQt4.QtCore import QSize, Qt
from PyQt4.QtGui import (
    QAbstractItemView, QKeySequence, QLabel, QListWidget, QListWidgetItem,
    QMenu, QToolButton)
from PyKDE4.kdecore import KGlobal, KShell, KToolInvocation, KUrl, i18n, i18np
from PyKDE4.kdeui import KDialog, KIcon, KMessageBox, KVBox
from PyKDE4.kio import KRun

import ly.parse

# Easily get our global config
def config(group):
    return KGlobal.config().group(group)


class ActionManager(object):
    def __init__(self, mainwin):
        self.mainwin = mainwin
        
    def addActionsToMenu(self, updatedFiles, menu):
        """
        Queries updatedFiles() and adds corresponding actions to the menu.
        """
        # PDFs
        pdfs = updatedFiles("pdf")
        for pdf in pdfs:
            name = '"{0}"'.format(os.path.basename(pdf))
            a = menu.addAction(KIcon("application-pdf"),
                i18n("Open %1 in external viewer", name))
            a.triggered.connect((lambda pdf: lambda: self.openPDF(pdf))(pdf))
            a = menu.addAction(KIcon("document-print"), i18n("Print %1", name))
            a.triggered.connect((lambda pdf: lambda: self.printPDF(pdf))(pdf))
            menu.addSeparator()
        # MIDIs
        midis = updatedFiles("mid*")
        for midi in midis:
            name = '"{0}"'.format(os.path.basename(midi))
            a = menu.addAction(KIcon("media-playback-start"), i18n("Play %1", name))
            a.triggered.connect((lambda midi: lambda: self.openMIDI(midi))(midi))

    def addActionsToLog(self, updatedFiles, log):
        """
        Queries updatedFiles() and adds corresponding actions to the log.
        See runlily.py for the LogWidget
        """
        bar = log.actionBar
        bar.clear() # clear all actions
        def make_action(items, func, icon, title):
            if items:
                icon = KIcon(icon)
                a = bar.addAction(icon, title)
                if len(items) == 1:
                    a.triggered.connect((lambda item: lambda: func(item))(items[0]))
                else:
                    menu = QMenu(bar.widgetForAction(a))
                    a.setMenu(menu)
                    bar.widgetForAction(a).setPopupMode(QToolButton.InstantPopup)
                    sip.transferto(menu, None) # let C++ take ownership
                    for item in items:
                        a = menu.addAction(icon, os.path.basename(item))
                        a.triggered.connect((lambda item: lambda: func(item))(item))

        pdfs = updatedFiles("pdf")
        make_action(pdfs, self.openPDF, "application-pdf", i18n("Open PDF"))
        make_action(pdfs, self.printPDF, "document-print", i18n("Print"))
        make_action(updatedFiles("mid*"), self.openMIDI, "media-playback-start",
            i18n("Play MIDI"))
        # if any actions were added, also add the email action and show.
        if len(bar.actions()) > 0:
            a = bar.addAction(KIcon("mail-send"), i18n("Email..."))
            a.setShortcut(QKeySequence("Ctrl+E"))
            a.setToolTip("{0} ({1})".format(a.toolTip(), a.shortcut().toString()))
            a.triggered.connect(lambda: self.email(updatedFiles, log.preview))
            log.checkScroll(bar.show)
        
    def openPDF(self, fileName):
        """
        Opens a PDF in the configured external PDF viewer, or in the
        KDE default one.
        """
        openPDF(fileName, self.mainwin)
    
    def openMIDI(self, fileName):
        """
        Opens a MIDI in the configured external MIDI player, or in the
        KDE default one.
        """
        openMIDI(fileName, self.mainwin)
    
    def printPDF(self, pdfFileName):
        """ Prints the PDF using the configured print command """
        printPDF(pdfFileName, self.mainwin)

    def openDirectory(self, path=None):
        """
        Opens a folder. If None, opes the document folder if any, or else
        the current working directory in the default KDE file manager.
        """
        if path is None:
            d = self.mainwin.currentDocument()
            if d.url().isEmpty():
                if d.localFileManager():
                    path = d.localFileManager().directory
                else:
                    path = self.mainwin.app.defaultDirectory() or os.getcwd()
            else:
                path = d.url().resolved(KUrl('.'))
        url = KUrl(path)
        url.adjustPath(KUrl.RemoveTrailingSlash)
        sip.transferto(KRun(url, self.mainwin), None) # C++ will delete it

    def email(self, updatedFiles, warnpreview=False):
        """
        Collects updated files and provides a nice dialog to send them.
        If warnpreview, the user is warned because he/she would send a PDF
        with point-and-click links in it. The PDFs are MUCH larger in that case.
        """
        if os.path.exists(updatedFiles.lyfile):
            EmailDialog(self.mainwin, updatedFiles, warnpreview).exec_()
        else:
            KMessageBox.sorry(self.mainwin,
                i18n("There are no files to send via email."),
                i18n("No files to send"))
                
        
class EmailDialog(KDialog):
    def __init__(self, parent, updatedFiles, warnpreview):
        KDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setButtons(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel))
        self.setCaption(i18n("Email documents"))
        self.showButtonSeparator(True)
        b = KVBox(self)
        b.setSpacing(4)
        QLabel(i18n("Please select the files you want to send:"), b)
        fileList = QListWidget(b)
        fileList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        fileList.setIconSize(QSize(22, 22))
        fileList.setWhatsThis(i18n(
            "These are the files that are up-to-date (i.e. newer than "
            "the LilyPond source document).  Also LilyPond files included "
            "by the source document are shown."))
        
        lyFiles = ly.parse.findIncludeFiles(updatedFiles.lyfile)
        pdfFiles = updatedFiles("pdf")
        midiFiles = updatedFiles("mid*")
        
        if warnpreview and pdfFiles:
            l = QLabel(i18np(
                "Note: this PDF file has been created with "
                "embedded point-and-click URLs (preview mode), which "
                "increases the file size dramatically. "
                "Please consider to rebuild the file in publish mode, "
                "because then the PDF file is much smaller.",
                "Note: these PDF files have been created with "
                "embedded point-and-click URLs (preview mode), which "
                "increases the file size dramatically. "
                "Please consider to rebuild the files in publish mode, "
                "because then the PDF files are much smaller.",
                len(pdfFiles)), b)
            l.setWordWrap(True)
        
        self.fileList = fileList
        self.setMainWidget(b)
        self.resize(450, 300)
        
        basedir = os.path.dirname(updatedFiles.lyfile)
        exts = config("general").readEntry("email_extensions", [".pdf"])
        
        class Item(QListWidgetItem):
            def __init__(self, icon, fileName):
                directory, name = os.path.split(fileName)
                if directory != basedir:
                    name += " ({0})".format(os.path.normpath(directory))
                QListWidgetItem.__init__(self, KIcon(icon), name, fileList)
                self.fileName = fileName
                self.ext = os.path.splitext(fileName)[1]
                if self.ext in exts:
                    self.setSelected(True)

            def url(self):
                return KUrl.fromPath(self.fileName).url()
                
        # insert the files
        for lyfile in lyFiles:
            Item("text-x-lilypond", lyfile)
        for pdf in pdfFiles:
            Item("application-pdf", pdf)
        for midi in midiFiles:
            Item("audio-midi", midi)
        
    def done(self, result):
        if result:
            # Save selected extensions to preselect next time.
            exts = list(set(item.ext for item in self.fileList.selectedItems()))
            config("general").writeEntry("email_extensions", exts)
            self.sendEmail()
        KDialog.done(self, result)
        
    def sendEmail(self):
        """ Now do it. """
        urls = [item.url() for item in self.fileList.selectedItems()]
        to, cc, bcc, subject, body, msgfile = '', '', '', '', '', ''
        KToolInvocation.invokeMailer(to, cc, bcc, subject, body, msgfile, urls)
        
        
        
def openPDF(fileName, window):
    """
    Opens a PDF in the configured external PDF viewer, or in the
    KDE default one.
    """
    openFile(fileName, window, config("commands").readEntry("pdf viewer", ""))

def openMIDI(fileName, window):
    """
    Opens a MIDI in the configured external MIDI player, or in the
    KDE default one.
    """
    openFile(fileName, window, config("commands").readEntry("midi player", ""))

def openFile(fileName, window, cmd = None):
    """
    Opens a file with command cmd (string, read from config)
    or with the KDE default application (via KRun).
    """
    if cmd:
        cmd, err = KShell.splitArgs(cmd)
        if err == KShell.NoError:
            cmd.append(fileName)
            try:
                Popen(cmd)
                return
            except OSError:
                pass
    # let C++ own the KRun object, it will delete itself.
    sip.transferto(KRun(KUrl.fromPath(fileName), window), None)
    
def printPDF(pdfFileName, window):
    """ Prints the PDF using the configured print command """
    cmd, err = KShell.splitArgs(config("commands").readEntry("lpr", "lpr"))
    if err == KShell.NoError:
        cmd.append(pdfFileName)
        try:
            p = Popen(cmd, stderr=PIPE)
            if p.wait() != 0:
                KMessageBox.error(window,
                    i18n("Printing failed: %1", p.stderr.read()))
            else:
                KMessageBox.information(window,
                    i18n("The document has been sent to the printer."))
        except OSError as e:
            KMessageBox.error(window, i18n(
                "Printing failed: %1\n\nThe print command %2 does "
                "probably not exist. Please check your settings.",
                unicode(e), cmd[0]))
    else:
        KMessageBox.error(window,
            i18n("The print command contains errors. "
                    "Please check your settings."))

