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

import math
import ly, ly.dom

from frescobaldi_app.runlily import LilyPreviewDialog
from frescobaldi_app.scorewiz import config

class PreviewDialog(LilyPreviewDialog):
    def __init__(self, scorewiz):
        self.scorewiz = scorewiz
        LilyPreviewDialog.__init__(self, scorewiz)
    
    def loadSettings(self):
        self.restoreDialogSize(config("preview"))
        
    def saveSettings(self):
        self.saveDialogSize(config("preview"))
        
    def showPreview(self):
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
                node = next(generator)
                node.append(ly.dom.Duration(dur, dots))
                stub.append(node)
            
        lyrics = lyricsGen(len(durs))
        # iter over all the Assignments to add example notes etc.
        for a in doc.findChildren(ly.dom.Assignment, 1):
            stub = a[-1]
            if isinstance(stub, ly.dom.LyricMode):
                stub.append(next(lyrics))
            elif isinstance(stub, ly.dom.Relative):
                addItems(stub[-1], pitchGen(keysig))
            elif isinstance(stub, ly.dom.ChordMode):
                addItems(stub, chordGen(keysig))
            elif isinstance(stub, ly.dom.FigureMode):
                addItems(stub, figureGen())
            elif isinstance(stub, ly.dom.DrumMode):
                addItems(stub, drumGen())

        LilyPreviewDialog.showPreview(self, builder.ly(doc))


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
            for s in "<{0}>".format(i), "\\skip", "\\skip":
                yield ly.dom.TextDur(s)
            
def drumGen():
    while True:
        for s in "bd", "hh", "sn", "hh":
            yield ly.dom.TextDur(s)


 