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
Preview dialog for the Score Wizard (scorewiz/__init__.py).
In separate file to ease maintenance.
"""

import math, os, sip, shutil, tempfile
import ly, ly.dom

from PyQt4.QtCore import QSize
from PyQt4.QtGui import QStackedWidget, QWidget
from PyKDE4.kdecore import KGlobal, KPluginLoader, KUrl, i18n
from PyKDE4.kdeui import KDialog
from PyKDE4.kio import KRun

from signals import Signal

from frescobaldi_app.scorewiz import config, onSignal
from frescobaldi_app.runlily import LogWidget, Ly2PDF


class PreviewDialog(KDialog):
    def __init__(self, scorewiz):
        self.closed = Signal()
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
                # default to single page layout
                a = part.actionCollection().action("view_render_mode_single")
                if a and not a.isChecked():
                    a.trigger()
        self.setMinimumSize(QSize(400, 300))
        self.restoreDialogSize(config("scorewiz").group("preview"))
        self.directory = None
        @onSignal(self, "finished()")
        def close():
            self.saveDialogSize(config("scorewiz").group("preview"))
            self.closed()
            if self.directory:
                shutil.rmtree(self.directory)
        
    def showPreview(self):
        self.directory = tempfile.mkdtemp()
        self.show()
        self.stack.setCurrentWidget(self.log)
        
        builder = self.scorewiz.builder()
        builder.midi = False # not needed
        doc = builder.document()

        keysig = doc.findChild(ly.dom.KeySignature) 
        timesig = doc.findChild(ly.dom.TimeSignature)
        partial = doc.findChild(ly.dom.Partial)
        # create a list of durations for the example notes.
        durs = []
        if partial:
            durs.append((partial.dur, partial.dots))
        if timesig:
            dur = int(math.log(int(timesig.beat), 2))
            num = min(int(timesig.num)*2, 10)
        else:
            dur, num = 2, 4
        durs += [(dur, 0)] * num
        
        def addItems(stub, generator):
            for dur, dots in durs:
                node = generator.next()
                node.append(ly.dom.Duration(dur, dots))
                stub.append(node)
            
        lyrics = lyricsGen(len(durs)).next
        # iter over all the Assignments to add example notes etc.
        for a in doc.findChildren(ly.dom.Assignment, 1):
            stub = a[-1]
            if isinstance(stub, ly.dom.LyricMode):
                stub.append(lyrics())
            elif isinstance(stub, ly.dom.Relative):
                addItems(stub[-1], pitchGen(keysig))
            elif isinstance(stub, ly.dom.ChordMode):
                addItems(stub, chordGen(keysig))
            elif isinstance(stub, ly.dom.FigureMode):
                addItems(stub, figureGen())
            elif isinstance(stub, ly.dom.DrumMode):
                addItems(stub, drumGen())

        # write the doc to a temporary file...
        lyfile = os.path.join(self.directory, 'preview.ly')
        text = builder.ly(doc)
        file(lyfile, 'w').write(text.encode('utf-8'))
        
        # ... and run LilyPond.
        self.job = Ly2PDF(lyfile, self.log)
        self.closed.connect(self.job.abort)
        self.job.done.connect(self.finished)
    
    def finished(self):
        pdfs = self.job.updatedFiles()("pdf")
        if pdfs:
            self.openPDF(pdfs[0])
        del self.job
    
    def openPDF(self, fileName):
        if self.part:
            if self.part.openUrl(KUrl.fromPath(fileName)):
                self.stack.setCurrentWidget(self.part.widget())
        else:
            sip.transferto(
                KRun(KUrl.fromPath(fileName), self.scorewiz.mainwin), None)


# Generators for different kinds of example input
def pitchGen(startPitch):
    note = startPitch.note
    while True:
        for n in (note, note, (note + 9 ) % 7, (note + 8) % 7,
                  note, (note + 11) % 7, note):
            chord = ly.dom.Chord()
            ly.dom.Pitch(-1, n, startPitch.alter, parent=chord)
            yield chord

def chordGen(startPitch):
    for n in pitchGen(startPitch):
        yield n
        for i in 1, 2, 3:
            yield ly.dom.TextDur("\\skip")
        
def lyricsGen(length):
    while True:
        for i in "ha", "hi", "ho", "he", "hu":
            result = [i]*length
            result[0] = result[0].title()
            yield ly.dom.Text(' '.join(result))

def figureGen():
    while True:
        for i in 5, 6, 3, 8, 7:
            for s in "<%s>" % i, "\\skip", "\\skip":
                yield ly.dom.TextDur(s)
            
def drumGen():
    while True:
        for s in "bd", "hh", "sn", "hh":
            yield ly.dom.TextDur(s)


# Easily get our global config
def config(group="preferences"):
    return KGlobal.config().group(group)
 