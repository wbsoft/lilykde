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

import re

from PyQt4 import QtCore, QtGui
from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KMessageBox
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
        # determine doc language
        currentLang = ly.parse.documentLanguage(self.doc.text()) or "nederlands"
        for lang in sorted(ly.pitch.pitchInfo.keys()):
            a = menu.addAction(lang.title())
            a.setCheckable(True)
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
        state = ly.tokenize.State()
        lastCommand = None
        writer = ly.pitch.pitchWriter[lang]
        reader = ly.pitch.pitchReader["nederlands"]
        # Walk through not-selected text, to track the state and the 
        # current pitch language.
        for token in ly.tokenize.tokenize(pretext, state=state):
            if isinstance(token, ly.tokenize.Command):
                lastCommand = token
            elif (isinstance(token, ly.tokenize.String)
                and lastCommand == "\\include"):
                langName = token[1:-4]
                if langName in ly.pitch.pitchInfo.keys():
                    reader = ly.pitch.pitchReader[langName]

        # Now walk through the part that needs to be translated.
        output = []
        includeCommandChanged = False
        for token in ly.tokenize.tokenize(changetext, state=state):
            if isinstance(token, ly.tokenize.Command):
                lastCommand = token
            elif (isinstance(token, ly.tokenize.String)
                and lastCommand == "\\include"):
                langName = token[1:-4]
                if langName in ly.pitch.pitchInfo.keys():
                    reader = ly.pitch.pitchReader[langName]
                    token = '"%s.ly"' % lang
                    includeCommandChanged = True
            elif isinstance(token, ly.tokenize.Word):
                result = reader(token)
                if result:
                    # result is a two-tuple (note, alter)
                    # Write out the translated pitch.
                    token = writer(*result)
            output.append(token)
        if self.doc.view.selection():
            self.doc.replaceSelectionWith("".join(output))
            if not includeCommandChanged:
                KMessageBox.information(self.doc.app.mainwin,
                    '<p>%s</p><p><tt>\\include "%s.ly"</tt></p>' %
                    (i18n("The pitch language of the selected text has been "
                          "updated, but you need to add manually the following "
                          "command:"), lang),
                    i18n("Change Pitch Language"))
        else:
            self.doc.doc.startEditing()
            self.doc.doc.setText("".join(output))
            if not includeCommandChanged:
                lineNum = re.search(r'\\version\s*"', self.doc.line(0)) and 1 or 0
                self.doc.doc.insertLine(lineNum, '\\include "%s.ly"' % lang)
            self.doc.doc.endEditing()
