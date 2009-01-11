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

import math, os, sip, shutil, tempfile
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
        
        lyrics = lyricsGen(len(durs)).next
        # iter over all the Assignments to add example notes etc.
        for a in doc.findChildren(ly.dom.Assignment, 1):
            stub = a[-1]
            if isinstance(stub, ly.dom.LyricMode):
                ly.dom.Text(lyrics(), parent=stub)
            elif isinstance(stub, ly.dom.Relative):
                node = stub[-1]
                pitch = pitchGen(keysig).next
                for dur, dots in durs:
                    chord = ly.dom.Chord(node)
                    chord.append(pitch())
                    chord.append(ly.dom.Duration(dur, dots))
            elif isinstance(stub, ly.dom.ChordMode):
                pitch = pitchGen(keysig).next
                for dur, dots in durs[:5]:
                    chord = ly.dom.Chord(stub)
                    chord.append(pitch())
                    chord.append(ly.dom.Duration(dur, dots))
            elif isinstance(stub, ly.dom.FigureMode):
                figure = figureGen().next
                for dur, dots in durs:
                    fig = ly.dom.TextDur(figure(), stub)
                    fig.append(ly.dom.Duration(dur, dots))
            elif isinstance(stub, ly.dom.DrumMode):
                drum = drumGen().next
                for dur, dots in durs:
                    dr = ly.dom.TextDur(drum(), stub)
                    dr.append(ly.dom.Duration(dur, dots))

        # write the doc to a temporary file and run LilyPond
        lyfile = os.path.join(self.directory, 'preview.ly')
        
        text = builder.ly(doc)
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
            yield ly.dom.Pitch(-1, n, startPitch.alter)
        
def lyricsGen(length):
    while True:
        for i in "ha", "hi", "ho", "he", "hu":
            result = [i]*length
            result[0] = result[0].title()
            yield ' '.join(result)

def figureGen():
    while True:
        for i in 5, 6, 3, 8, 7:
            yield "<%s>" % i
            
def drumGen():
    while True:
        for i in "bd", "hh", "sn", "hh":
            yield i


# Easily get our global config
def config(group="preferences"):
    return KGlobal.config().group(group)
 