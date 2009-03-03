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

import ly.rx, ly.pitch, ly.parse, ly.tokenize
from frescobaldi_app.widgets import promptText

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
            elif isinstance(token, ly.tokenize.PitchWord):
                result = reader(token)
                if result:
                    note, alter = result
                    # Write out the translated pitch.
                    token = writer(note, alter, warn=True)
                    if not token:
                        KMessageBox.sorry(self.doc.app.mainwin, i18n(
                            "Can't perform the requested translation. "
                            "The music contains quarter-tone alterations, but "
                            "those are not available in the pitch language %1.",
                            lang))
                        return
            output.append(token)
        if self.doc.view.selection():
            self.doc.replaceSelectionWith("".join(output))
            if not includeCommandChanged:
                KMessageBox.information(self.doc.app.mainwin,
                    '<p>%s</p><p><tt>\\include "%s.ly"</tt></p>' %
                    (i18n("The pitch language of the selected text has been "
                          "updated, but you need to manually add the following "
                          "command to your document:"), lang),
                    i18n("Pitch Name Language"))
        else:
            self.doc.doc.startEditing()
            self.doc.doc.setText("".join(output))
            if not includeCommandChanged:
                self.addLineToTop('\\include "%s.ly"' % lang)
            self.doc.doc.endEditing()

    def addLineToTop(self, text):
        """
        Adds text to the beginning of the document, but below a \version
        command.
        """
        self.doc.doc.insertLine(self.topInsertPoint(), text)

    def topInsertPoint(self):
        """
        Finds the topmost place to add text, but below a \version command.
        """
        for line in range(20):
            if re.search(r'\\version\s*".*?"', self.doc.line(line)):
                return line + 1
        else:
            return 0
        
    def findInsertPoint(self, lineNum):
        """
        Finds the last possible toplevel insertion point before line number
        lineNum. Returns the line number to insert text at.
        """
        insert = 0
        state = ly.tokenize.State()
        for token in ly.tokenize.tokenizeLineColumn(self.doc.text(), state=state):
            if (isinstance(token, ly.tokenize.Space)
                and state.depth() == (1, 0)
                and token.count('\n') > 1):
                if token.line >= lineNum:
                    break
                insert = token.line + 1 # next line is the line to insert at
        return insert or self.topInsertPoint()
        
    def assignSelectionToVariable(self):
        """
        Cuts out selected text and stores it under a variable name, adding a
        reference to that variable in the original place.
        There MUST be a selection.
        """
        # ask the variable name
        name = promptText(self.doc.app.mainwin, i18n(
            "Please enter the name for the variable to assign the selected "
            "text to:"), i18n("Cut and Assign"), rx="[a-zA-Z]*", help="cut-assign")
        if not name:
            return
        currentLine = self.doc.view.selectionRange().start().line()
        insertLine = self.findInsertPoint(currentLine)
        
        text = self.doc.selectionText().strip()
        if '\n' in text:
            # re-indent the text
            lines = text.splitlines()
            indent = min(len(re.match(r'\s*', line).group()) for line in lines[1:])
            text = '\n  '.join(lines[:1] + [line[indent:] for line in lines[1:]])
            result = "%s = {\n  %s\n}\n" % (name, text)
        else:
            result = "%s = { %s }\n" % (name, text)
            
        if self.doc.line(insertLine).strip():
            result += '\n'
        if insertLine > 0 and self.doc.line(insertLine - 1).strip():
            result = '\n' + result
        
        # add space if necessary
        variable = "\\%s" % name
        end = self.doc.view.selectionRange().end()
        if self.doc.line(end.line())[end.column():end.column()+1].strip():
            variable += " "

        # do it:
        cursor = KTextEditor.Cursor(insertLine, 0)
        self.doc.doc.startEditing()
        self.doc.replaceSelectionWith(variable, keepSelection=False)
        self.doc.doc.insertText(cursor, result)
        self.doc.doc.endEditing()
        
    def repeatLastExpression(self):
        """
        Repeat the last entered music expression (without duration)
        """
        # find the last non-empty line
        curPos = self.doc.view.cursorPosition()
        lineNum = curPos.line()
        while lineNum > 0 and not self.doc.line(lineNum).strip():
            lineNum -= 1
            
        text = unicode(self.doc.doc.text(
            KTextEditor.Range(KTextEditor.Cursor(lineNum, 0), curPos)))
        matchObj = None
        for m in ly.rx.chord_rest.finditer(text):
            if m.group('chord'):
                matchObj = m
        if not matchObj:
            return # nothing to repeat
        
        # leave out the duration
        result = matchObj.group('chord')
        
        # add articulations, etc
        stuff = text[matchObj.start() + len(matchObj.group()):].strip()
        if stuff:
            result += stuff.splitlines()[0]
        
        # write it in the document, add a space if necessary
        col = curPos.column()
        if col > 0 and self.doc.line()[col-1].strip():
            result = " " + result
        self.doc.view.insertText(result + " ")
    
