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

"""
Actions (that can be performed on files generated by running LilyPond
"""

import os, sip
from subprocess import Popen, PIPE

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import KRun

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
            name = '"%s"' % os.path.basename(pdf)
            a = menu.addAction(KIcon("application-pdf"),
                i18n("Open %1 in external viewer", name))
            QObject.connect(a, SIGNAL("triggered()"),
                lambda pdf=pdf: self.openFile(pdf))
            a = menu.addAction(KIcon("document-print"), i18n("Print %1", name))
            QObject.connect(a, SIGNAL("triggered()"),
                lambda pdf=pdf: self.printPDF(pdf))
            menu.addSeparator()
        # MIDIs
        midis = updatedFiles("mid*")
        for midi in midis:
            name = '"%s"' % os.path.basename(midi)
            a = menu.addAction(KIcon("media-playback-start"), i18n("Play %1", name))
            QObject.connect(a, SIGNAL("triggered()"),
                lambda midi=midi: self.openFile(midi))

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
                    QObject.connect(a, SIGNAL("triggered()"),
                        lambda item=items[0]: func(item))
                else:
                    menu = QMenu(bar.widgetForAction(a))
                    a.setMenu(menu)
                    bar.widgetForAction(a).setPopupMode(QToolButton.InstantPopup)
                    sip.transferto(menu, None) # let C++ take ownership
                    for item in items:
                        a = menu.addAction(icon, os.path.basename(item))
                        QObject.connect(a, SIGNAL("triggered()"),
                            lambda item=item: func(item))

        pdfs = updatedFiles("pdf")
        make_action(pdfs, self.openFile, "application-pdf", i18n("Open PDF"))
        make_action(pdfs, self.printPDF, "document-print", i18n("Print"))
        make_action(updatedFiles("mid*"), self.openFile, "media-playback-start",
            i18n("Play MIDI"))
        if updatedFiles():
            a = bar.addAction(KIcon("mail-send"), i18n("Email..."))
            QObject.connect(a, SIGNAL("triggered()"), lambda:
                self.email(updatedFiles, log.preview))
        
        if len(bar.actions()) > 0:
            log.checkScroll(bar.show)
        
    def openFile(self, fileName):
        """ Opens a file in its default viewer."""
        # let C++ own the KRun object, it will delete itself.
        sip.transferto(KRun(KUrl.fromPath(fileName), self.mainwin), None)
        
    def printPDF(self, pdfFileName):
        """ Prints the PDF using the configured print command """
        cmd, err = KShell.splitArgs(
            config("commands").readEntry("lpr", "lpr"))
        if err == KShell.NoError:
            cmd = [unicode(arg) for arg in cmd]
            cmd.append(pdfFileName)
            try:
                p = Popen(cmd, stderr=PIPE)
                if p.wait() != 0:
                    KMessageBox.error(self.mainwin,
                        i18n("Printing failed: %1", p.stderr.read()))
                else:
                    KMessageBox.information(self.mainwin,
                        i18n("The document has been sent to the printer."))
            except OSError, e:
                KMessageBox.error(self.mainwin, i18n(
                    "Printing failed: %1\n\nThe print command %2 does "
                    "probably not exist. Please check your settings.",
                    unicode(e), cmd[0]))
        else:
            KMessageBox.error(self.mainwin,
                i18n("The print command contains errors. "
                        "Please check your settings."))

    def openDirectory(self, directory=None):
        """
        Opens a folder. If None, opes the document folder if any, or else
        the current working directory in the default KDE file manager.
        """
        if directory is not None:
            url = KUrl(directory)
        elif self.mainwin.currentDocument().url().isEmpty():
            url = KUrl.fromPath(os.getcwd())
        else:
            url = KUrl(self.mainwin.currentDocument().url().resolved(KUrl('.')))
        url.adjustPath(KUrl.RemoveTrailingSlash)
        sip.transferto(KRun(url, self.mainwin), None) # C++ will delete it

    def email(self, updatedFiles, warnpreview=False):
        """
        Collects updated files and provides a nice dialog to send them.
        If warnpreview, the user is warned because he/she would send a PDF
        with point-and-click links in it. The PDFs are MUCH larger in that case.
        """
        pass # TODO: implement
        
        
        