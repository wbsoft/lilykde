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
Advanced manipulations on LilyPond documents.
"""

from PyQt4 import QtCore, QtGui
from PyKDE4.ktexteditor import KTextEditor

import ly.pitch, ly.parse, ly.tokenize

class DocumentManipulator(object):
    """
    Can perform manipulations on a LilyPond document.
    """
    def __init__(self, doc):
        self.doc = doc

    def populateLanguageMenu(self, menu):
        menu.clear()
        group = QtGui.QActionGroup(menu)
        group.setExclusive(True)
        # determine doc language
        currentLang = ly.parse.documentLanguage(self.doc.text()) or "nederlands"
        for lang in sorted(ly.pitch.pitchInfo.keys()):
            a = menu.addAction(lang.title())
            a.setCheckable(True)
            group.addAction(a)
            if lang == currentLang:
                a.setChecked(True)
            QtCore.QObject.connect(a, QtCore.SIGNAL("triggered()"),
                lambda lang=lang: self.changeLanguage(lang))
                
    def changeLanguage(self, lang):
        """
        Change the LilyPond pitch name language in our document to lang.
        """
        if self.doc.view.selection():
            changetext = unicode(self.doc.view.selectionText())
            pretext = unicode(self.doc.doc.text(
                KTextEditor.Range(
                    KTextEditor.Cursor(0, 0),
                    self.doc.view.selectionRange().start())))
        else:
            changetext = self.doc.text()
            pretext = ''

        # iterate over the document and replace pitches in the text section.
        state = [ly.tokenize.LilyState()]
        output = None
        level = []
        lastCommand = None
        writer = ly.pitch.pitchWriter[lang]
        reader = ly.pitch.pitchReader["nederlands"]
        for text in pretext, changetext:
            for token in ly.tokenize.tokenize(text, state=state):
                if isinstance(token, ly.tokenize.Command):
                    lastCommand = token
                elif isinstance(token, ly.tokenize.OpenDelimiter):
                    level.append(lastCommand in noMusicCommands)
                elif level and isinstance(token, ly.tokenize.CloseDelimiter):
                    level.pop()
                elif (
                    output is not None and isinstance(token, ly.tokenize.Word)
                    and ((level and level[-1]) or lastCommand in pitchCommands)
                    ):
                    result = reader(token)
                    if result:
                        # result is a two-tuple (note, alter)
                        # Write out the translated pitch.
                        token = writer(*result)
                elif (isinstance(token, ly.tokenize.String)
                    and lastCommand == "\\include"):
                    langName = token[1:-4]
                    if langName in ly.pitch.pitchInfo.keys():
                        reader = ly.pitch.pitchReader[langName]
                        token = '"%s.ly"' % langName
                elif not isinstance(token, (ly.tokenize.String, ly.tokenize.Space)):
                    lastCommand = None
                if output is not None:
                    output.append(token)
            output = [] # start writing the changed output


noMusicCommands = (
    '\\lyricsto', '\\lyricmode', '\\addlyrics', '\\oldaddlyrics',
)

pitchCommands = (
    '\\relative', '\\key', '\\transpose', '\\transposition',
)
