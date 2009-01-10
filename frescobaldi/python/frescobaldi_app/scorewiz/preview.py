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
Preview dialog for the Score Wizard (scorewiz/__init__.py).
In separate file to ease maintenance.
"""

import os, sip, shutil, tempfile
import ly, ly.dom

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import KGlobal, KPluginLoader, KUrl, i18n
from PyKDE4.kdeui import KDialog
from PyKDE4.kio import KRun

from kateshell.mainwindow import listeners
from frescobaldi_app.scorewiz import config, onSignal
from frescobaldi_app.runlily import LogWidget, Ly2PDF


class PreviewDialog(KDialog):
    def __init__(self, scorewiz):
        listeners.add(self.close)
        self.scorewiz = scorewiz
        KDialog.__init__(self, scorewiz)
        self.setModal(True)
        self.setCaption(i18n("PDF Preview"))
        self.setButtons(KDialog.ButtonCode(KDialog.Close))

        self.stack = QStackedWidget()
        self.setMainWidget(self.stack)

        # The widget stack has two widgets, a log and a PDF preview.
        # the Log:
        self.log = LogWidget(self.stack)
        self.stack.addWidget(self.log)
        
        # the PDF preview, load Okular part.
        # If not, we just run the default PDF viewer.
        self.part = None
        factory = KPluginLoader("okularpart").factory()
        if factory:
            part = factory.create(self)
            if part:
                self.part = part
                self.stack.addWidget(part.widget())
                # hide mini pager
                w = part.widget().findChild(QWidget, "miniBar")
                if w:
                    w.parent().hide()
                # hide left panel
                a = part.actionCollection().action("show_leftpanel")
                if a and a.isChecked():
                    a.toggle()
        self.setMinimumSize(QSize(400, 300))
        self.restoreDialogSize(config("scorewiz").group("preview"))
        self.directory = None
        @onSignal(self, "finished()")
        def close():
            self.saveDialogSize(config("scorewiz").group("preview"))
            listeners.call(self.close)
            if self.directory:
                shutil.rmtree(self.directory)
        
    def showPreview(self):
        self.directory = tempfile.mkdtemp()
        self.show()
        self.stack.setCurrentWidget(self.log)
        
        doc = self.scorewiz.buildDocument()
        
        printer = ly.dom.Printer()
        printer.indentString = "  " # FIXME get indent-width somehow...
        printer.typographicalQuotes = self.scorewiz.settings.typq.isChecked()

        # iter over all the Assignments to add some example notes and
        # other stuff
        for a in doc.findChildren(ly.dom.Assignment, 1):
            stub = a[-1]
            if isinstance(stub, ly.dom.LyricMode):
                ly.dom.Text('He', parent=stub)
            elif isinstance(stub, ly.dom.Relative):
                node = stub[-1]
                ly.dom.Pitch(octave=-1, parent=node)
                
        
        # write the doc to a temporary file and run LilyPond
        lyfile = os.path.join(self.directory, 'preview.ly')
        
        text = printer.indent(doc)
        print text #DEBUG
        file(lyfile, 'w').write(text.encode('utf-8'))
        
        # Now run LilyPond
        job = Ly2PDF(lyfile, self.log)
        def finished():
            listeners[self.close].remove(job.abort)
            pdfs = job.updatedFiles()("pdf")
            if pdfs:
                self.openPDF(pdfs[0])
        listeners[self.close].append(job.abort)
        listeners[job.finished].append(finished)
    
    def openPDF(self, fileName):
        if self.part:
            self.stack.setCurrentWidget(self.part.widget())
            self.part.openUrl(KUrl.fromPath(fileName))
        else:
            sip.transferto(
                KRun(KUrl.fromPath(fileName), self.scorewiz.mainwin), None)

       
        

# Easily get our global config
def config(group="preferences"):
    return KGlobal.config().group(group)
 