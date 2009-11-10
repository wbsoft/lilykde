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

import os, re, weakref
from rational import Rational

from PyQt4 import QtCore, QtGui

from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KDialog, KIcon, KMessageBox
from PyKDE4.ktexteditor import KTextEditor

import ly.rx, ly.pitch, ly.parse, ly.tokenize
from kateshell.app import lazymethod
from frescobaldi_app.widgets import promptText


class DocumentManipulator(object):
    """
    Can perform manipulations on a LilyPond document.
    """
    def __init__(self, doc):
        self.doc = weakref.proxy(doc)
        
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
        start = KTextEditor.Cursor(0, 0)
        selection = bool(self.doc.selectionText()) and self.doc.view.selectionRange()
        
        if selection:
            end = selection.end()
        else:
            # directly using doc.documentRange().end() causes a crash...
            docRange = self.doc.doc.documentRange()
            end = docRange.end()
        text = unicode(self.doc.doc.text(KTextEditor.Range(start, end)))
        
        writer = ly.pitch.pitchWriter[lang]
        reader = ly.pitch.pitchReader["nederlands"]
        tokenizer = RangeTokenizer()
        tokens = tokenizer.tokens(text)
        
        # Walk through not-selected text, to track the state and the 
        # current pitch language.
        if selection and selection.start().position() != (0, 0):
            for token in tokens:
                if isinstance(token, tokenizer.IncludeFile):
                    langName = token[1:-4]
                    if langName in ly.pitch.pitchInfo:
                        reader = ly.pitch.pitchReader[langName]
                if selection.contains(token.range.end()):
                    break
        
        # Now walk through the part that needs to be translated.
        changes = ChangeList()
        includeCommandChanged = False
        for token in tokens:
            if isinstance(token, tokenizer.IncludeFile):
                langName = token[1:-4]
                if langName in ly.pitch.pitchInfo:
                    reader = ly.pitch.pitchReader[langName]
                    changes.replace(token, '"%s.ly"' % lang)
                    includeCommandChanged = True
            elif isinstance(token, tokenizer.PitchWord):
                result = reader(token)
                if result:
                    note, alter = result
                    # Write out the translated pitch.
                    replacement = writer(note, alter, warn=True)
                    if not replacement:
                        KMessageBox.sorry(self.doc.app.mainwin, i18n(
                            "Can't perform the requested translation. "
                            "The music contains quarter-tone alterations, but "
                            "those are not available in the pitch language %1.",
                            lang))
                        return
                    changes.replace(token, replacement)
        
        # Apply the changes.
        self.doc.doc.startEditing()
        changes.apply(self.doc.doc)
        if not selection and not includeCommandChanged:
            self.addLineToTop('\\include "%s.ly"' % lang)
        self.doc.doc.endEditing()
        if selection and not includeCommandChanged:
            KMessageBox.information(self.doc.app.mainwin,
                '<p>%s</p><p><tt>\\include "%s.ly"</tt></p>' %
                (i18n("The pitch language of the selected text has been "
                        "updated, but you need to manually add the following "
                        "command to your document:"), lang),
                i18n("Pitch Name Language"))

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
        tokenizer = ly.tokenize.LineColumnTokenizer()
        for token in tokenizer.tokens(self.doc.text()):
            if (isinstance(token, tokenizer.Space)
                and tokenizer.depth() == (1, 0)
                and token.count('\n') > 1):
                if token.line >= lineNum:
                    break
                insert = token.line + 1 # next line is the line to insert at
        return insert or self.topInsertPoint()
    
    def findBlankLines(self, depth=(1, 0)):
        """
        Yields the ranges that represent blank lines in the given depth (count
        of parsers, level).
        """
        tokenizer = RangeTokenizer()
        for token in tokenizer.tokens(self.doc.text()):
            if (isinstance(token, tokenizer.Space)
                and tokenizer.depth() <= depth
                and token.count('\n') > 1):
                yield token.range

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
        
        # find out in what input mode we are
        mode = ""
        selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
        text = self.doc.textToCursor(selRange.start())
        tokenizer = ly.tokenize.Tokenizer()
        for token in tokenizer.tokens(text):
            pass
        for s in reversed(tokenizer.state):
            if isinstance(s, tokenizer.InputModeParser):
                if isinstance(s, tokenizer.LyricModeParser):
                    mode = " \\lyricmode"
                elif isinstance(s, tokenizer.ChordModeParser):
                    mode = " \\chordmode"
                elif isinstance(s, tokenizer.FigureModeParser):
                    mode = " \\figuremode"
                break
        
        currentLine = selRange.start().line()
        insertLine = self.findInsertPoint(currentLine)
        
        text = self.doc.selectionText().strip()
        if '\n' in text:
            result = "%s =%s {\n%s\n}\n" % (name, mode, text)
            result = self.doc.indent(result)
        else:
            result = "%s =%s { %s }\n" % (name, mode, text)
            
        if not isblank(self.doc.line(insertLine)):
            result += '\n'
        if insertLine > 0 and not isblank(self.doc.line(insertLine - 1)):
            result = '\n' + result
        
        # add space if necessary
        variable = "\\%s" % name
        end = selRange.end()
        if not isblank(self.doc.line(end.line())[end.column():end.column()+1]):
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
        while lineNum > 0 and isblank(self.doc.line(lineNum)):
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
        
        # remove octave mark from first pitch
        result = re.sub(ly.rx.named_pitch,
            lambda m: m.group('step') + m.group('cautionary'), result, 1)
        
        # add articulations, etc
        stuff = text[matchObj.end():]
        if not isblank(stuff):
            stuff = stuff.splitlines()[0]
            # Filter the things we want to repeat.  E.g. slur events don't
            # make much sense, but artications do.  We delete comments and
            # strings to avoid matching stuff inside those.
            result += ''.join(
                m.group(1)
                for m in re.compile(
                    r'('                            # keep:
                        r'[-_^][_.+|>^-]'           # - articulation shorthands
                        r'|[_^]?~'                  # - ties
                    r')'                            # delete:
                        r'|"(?:\\\\|\\\"|[^\"])*"'  # - quoted strings
                        r'|%.*?$'                   # - comments
                    ).finditer(stuff)
                if m.group(1))
        
        # write it in the document, add a space if necessary
        col = curPos.column()
        if col > 0 and not isblank(self.doc.line()[col-1]):
            result = " " + result
        self.doc.view.insertText(result + " ")
    
    def selectLines(self):
        """
        Adjust the selection so that full lines are selected.
        """
        if not self.doc.view.selection():
            return
            
        selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
        start = selRange.start()
        end = selRange.end()
        cursor = self.doc.view.cursorPosition()
        atStart = cursor.position() == start.position()
        
        if start.column() > 0:
            start.setColumn(0)
        if end.column() == 0 and end.line() > start.line():
            end.setLine(end.line() - 1)
        end.setColumn(len(self.doc.line(end.line())))
        self.doc.view.setSelection(KTextEditor.Range(start, end))
        if atStart:
            self.doc.view.setCursorPosition(start)
        else:
            self.doc.view.setCursorPosition(end)
    
    def selectFullLines(self):
        """
        Extends (if necessary) the selection to cover whole lines, including newline.
        """
        if not self.doc.view.selection():
            return

        selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
        start = selRange.start()
        end = selRange.end()
        cursor = self.doc.view.cursorPosition()
        atStart = cursor.position() == start.position()
        
        if start.column() > 0:
            start.setColumn(0)
        if end.column() > 0:
            if end.line() < self.doc.doc.lines():
                end.setColumn(0)
                end.setLine(end.line() + 1)
            else:
                end.setColumn(len(self.doc.line(end.line())))
        self.doc.view.setSelection(KTextEditor.Range(start, end))
        if atStart:
            self.doc.view.setCursorPosition(start)
        else:
            self.doc.view.setCursorPosition(end)
    
    def fixSelection(self):
        """
        Adjust the selection in the following way:
        start:
        - if at a pitch, check if we're inside a chord and if yes,
          move to the beginning of that chord.
        end:
        - if at a pitch:
            - if inside a chord: extend to contain chord + dur
            - else: extend to contain pitch + dur
        - if at a lyric word (i.e. not a command):
            - extend selection to contain word (+ dur)
        """
        if not self.doc.view.selection():
            return
        # We need to save the selectionRange Range instance otherwise
        # we crash in KDE 4.3 / PyQt 4.5.x.
        selRange = self.doc.view.selectionRange()
        start = selRange.start()
        end = selRange.end()
        # adjust start:
        text = self.doc.line(start.line())
        col = start.column()
        if re.match(ly.rx.step, text[col:]):
            for m in ly.rx.chord.finditer(text):
                if (m.group('chord')
                    and m.group('chord').startswith('<')
                    and m.start('chord') <= col <= m.end('chord')):
                    start.setColumn(m.start('chord'))
                    break
        # adjust end:
        text = self.doc.line(end.line())
        col = end.column()
        if re.match("%s|%s" % (ly.rx.step, ly.rx.rest), text[col:]):
            for m in ly.rx.chord_rest.finditer(text):
                if (m.group('chord')
                    and m.start('chord') <= col <= m.end('chord')):
                    end.setColumn(m.end('full'))
                    break
        elif col < len(text) and text[col] not in "\\-_^":
            end.setColumn(col + len(text[col:].split()[0]))
        self.doc.view.setSelection(KTextEditor.Range(start, end))
    
    def indent(self):
        """
        Indent the (selected) text.
        """
        selection = bool(self.doc.selectionText())
        if selection:
            start = None
            self.selectLines()
            selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
            cursor = selRange.start()
            startline = cursor.line()
            # find out if the selected snippet is scheme code
            tokenizer = ly.tokenize.Tokenizer()
            for token in tokenizer.tokens(self.doc.textToCursor(cursor)):
                pass
            startscheme = isinstance(tokenizer.parser(), tokenizer.SchemeParser)
            text = self.doc.selectionText()
        else:
            start = 0
            startline = 0
            startscheme = False
            text = self.doc.text()
        
        # save the old indents
        ind = lambda line: re.compile(r'[^\S\n]*').match(line).group()
        oldindents = map(ind, text.splitlines())
        text = self.doc.indent(text, start = start, startscheme = startscheme)
        newindents = map(ind, text.splitlines())
        
        # We don't just replace the text, because that would destroy smart
        # point and click. We only replace the indents.
        self.doc.doc.startEditing()
        for old, new in zip(oldindents, newindents):
            if old != new:
                self.doc.doc.replaceText(
                    KTextEditor.Range(startline, 0, startline, len(old)), new)
            startline += 1
        self.doc.doc.endEditing()
        self.doc.view.removeSelection()

    def populateContextMenu(self, menu):
        """
        Called as soon as the user requests the context menu.
        Displays relevant actions for the object clicked on.
        """
        menu.clear()
        self.addSpecialActionsToContextMenu(menu)
        if menu.actions():
            menu.addSeparator()
        # standard actions
        a = self.doc.app.mainwin.actionCollection().action("edit_cut_assign")
        if a and a.isEnabled():
            menu.addAction(a)
        for action in ("edit_cut", "edit_copy", "edit_paste"):
            a = self.doc.view.actionCollection().action(action)
            if a and a.isEnabled():
                menu.addAction(a)
        
        # Add selection to Expansion Manager
        a = self.doc.app.mainwin.actionCollection().action("edit_expand_add")
        if a and a.isEnabled():
            menu.addAction(a)
        
        # LilyPond Help
        if not self.doc.selectionText():
            tool = self.doc.app.mainwin.tools.get('lilydoc')
            if tool:
                cursor = self.doc.view.cursorPosition()
                line, col = cursor.line(), cursor.column()
                tool.docFinder().addHelpMenu(menu, self.doc.line(line), col)
        
        # Bookmarks
        a = self.doc.view.actionCollection().action("bookmarks")
        if a and a.isEnabled():
            menu.addSeparator()
            menu.addAction(a)

    def addSpecialActionsToContextMenu(self, menu):
        """
        Called by populateContextMenu, adds special actions dependent of
        cursor position.
        """
        selection = self.doc.selectionText()
        if selection:
            selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
            cursor = selRange.start()
        else:
            cursor = self.doc.view.cursorPosition()
        line, col = cursor.line(), cursor.column()
        text = self.doc.line(line)
        # special actions
        # \include file
        path = self.doc.localPath()
        if path:
            for m in re.finditer(r'\\include\s*"?([^"]+)', text):
                if m.start() <= col <= m.end():
                    fileName = m.group(1)
                    url = os.path.join(os.path.dirname(path), fileName)
                    a = menu.addAction(KIcon("document-open"), i18n("Open %1", fileName))
                    QtCore.QObject.connect(a, QtCore.SIGNAL("triggered()"),
                        lambda url=url: self.doc.app.openUrl(url).setActive())
                    return
        
        # Rhythm submenu
        if selection and ly.rx.chord_rest.search(selection):
            menu.addMenu(self.doc.app.mainwin.factory().container(
                "lilypond_edit_rhythm", self.doc.app.mainwin))
        
        # Brace selection
        if selection:
            a = self.doc.app.mainwin.actionCollection().action(
                "edit_insert_braces")
            if a and a.isEnabled():
                menu.addAction(a)
        
        # Repeat selected music
        a = self.doc.app.mainwin.actionCollection().action("edit_repeat")
        if a and a.isEnabled():
            menu.addAction(a)
        
        # run the parser to know more about the current context...
        tokenizer = ly.tokenize.Tokenizer()
        for token in tokenizer.tokens(self.doc.textToCursor(cursor)):
            pass
        
        # Hyphenate Lyrics
        if selection and isinstance(tokenizer.parser(), tokenizer.LyricModeParser):
            menu.addAction(
                self.doc.app.mainwin.actionCollection().action("lyrics_hyphen"))
        
    def insertTypographicalQuote(self, double = False):
        """
        Insert a single or double quotation mark at the current cursor position.
        If the character left to the cursor is a space or a double quote,
        use the left typographical quote, otherwise the right.
        """
        selection = self.doc.selectionText()
        if selection:
            repl = double and u'\u201C%s\u201D' or u'\u2018%s\u2019'
            self.doc.replaceSelectionWith(repl % selection, keepSelection=False)
        else:
            cursor = self.doc.view.cursorPosition()
            line, col = cursor.line(), cursor.column()
            right = col > 0 and self.doc.line(line)[col-1] not in '" \t'
            self.doc.view.insertText({
                (False, False): u'\u2018',     # LEFT SINGLE QUOTATION MARK
                (False, True ): u'\u2019',     # RIGHT SINGLE QUOTATION MARK
                (True,  False): u'\u201C',     # LEFT DOUBLE QUOTATION MARK
                (True,  True ): u'\u201D',     # RIGHT DOUBLE QUOTATION MARK
                }[(double, right)])

    def insertBarLine(self, bar):
        """
        Insert a \\bar ".." command with the given type.
        """
        self.doc.view.insertText('\\bar "%s"' % bar)
        
    def insertTemplate(self, text, cursor=None, remove=None, doIndent=True):
        """
        Inserts text into the document.  If cursor is not given,
        use the view's current cursor position.  If remove is given,
        it is expected to be a KTextEditor.Range() to replace with the
        text.
        
        If the text contains '(|)', the cursor is set there. If the string
        '(|)' appears twice, that range is selected after inserting the text.
        
        The text is also indented.
        """
        cursor = cursor or self.doc.view.cursorPosition()
        
        # place to set cursor or range to select after writing out the expansion
        newcursors = []
        
        # re-indent the text:
        if doIndent and '\n' in text:
            text = self.doc.indent(text, self.doc.currentIndent(cursor)).lstrip()
        
        # "(|)" is the place to position the cursor after inserting
        # if this sequence appears twice, the range is selected.
        if "(|)" in text:
            newcur = Cursor(cursor)
            for t in text.split("(|)", 2)[:-1]:
                newcur.walk(t)
                newcursors.append(newcur.kteCursor())
            text = text.replace("(|)", "")
        if remove:
            self.doc.doc.replaceText(remove, text)
        else:
            self.doc.doc.insertText(cursor, text)
        if newcursors:
            self.doc.view.setCursorPosition(newcursors[0])
            if len(newcursors) > 1:
                self.doc.view.setSelection(KTextEditor.Range(*newcursors[:2]))
        
    def addArticulation(self, art):
        """
        Add artication to selected notes or chord, or just insert it.
        """
        text = self.doc.selectionText()
        if text:
            pos = 0
            insertions = []
            selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
            cur = Cursor(selRange.start())
            for m in ly.rx.chord.finditer(text):
                if m.group('chord'):
                    cur.walk(text[pos:m.end('full')])
                    pos = m.end('full')
                    insertions.append(cur.kteCursor())
            self.doc.doc.startEditing()
            for i in reversed(insertions):
                self.doc.doc.insertText(i, art)
            self.doc.doc.endEditing()
            self.doc.view.removeSelection()
        else:
            self.doc.view.insertText(art)
        
    def wrapBrace(self, text, command='', alwaysMultiLine=False):
        """
        Wrap a piece of text inside a brace construct. Returns the replacement.
        The piece of text is also expected to be the selection of the document,
        because this routine needs to know the indent of the resulting text.
        E.g.:
        wrapBrace("c d e f", "\\relative c'") returns
        "\\relative c' { c d e f }"
        """
        if command != '':
            command += ' '
        # preserve space at start and end of selection
        space1, sel, space2 = re.compile(
            r'^(\s*)(.*?)(\s*)$', re.DOTALL).match(text).groups()
        if alwaysMultiLine or '\n' in text:
            result = "%s{\n%s\n}" % (command, sel)
            # indent the result corresponding with the first selection line.
            selRange = self.doc.view.selectionRange()
            indentDepth = self.doc.currentIndent(selRange.start(), False)
            result = self.doc.indent(result, indentDepth).lstrip()
        else:
            result = "%s{ %s }" % (command, sel)
        return ''.join((space1, result, space2))
        
    def moveSelectionUp(self):
        """
        Moves the selected block to the previous blank line.
        There MUST be a selection.
        """
        self.selectFullLines()
        cursor = self.doc.view.cursorPosition()
        selRange = self.doc.view.selectionRange()
        if selRange.start().position() == (0, 0):
            return
        text = self.doc.selectionText()
        self.doc.doc.startEditing()
        atStart = cursor.position() == selRange.start().position()
        # Determine current depth (we could be in a long \book block)
        tokenizer = ly.tokenize.Tokenizer()
        for token in tokenizer.tokens(self.doc.textToCursor(selRange.start())):
            pass
        self.doc.doc.removeText(selRange)
        insert = KTextEditor.Cursor(0, 0)
        for r in reversed(list(self.findBlankLines(tokenizer.depth()))):
            if r.end().position() < selRange.start().position():
                insert.setLine(r.end().line())
                break
        cursor = Cursor(insert)
        if not text.endswith('\n'):
            text += '\n'
        cursor.walk(text)
        self.doc.doc.insertText(insert, text)
        selRange = KTextEditor.Range(insert, cursor.kteCursor())
        self.doc.view.setSelection(selRange)
        if atStart:
            self.doc.view.setCursorPosition(selRange.start())
        else:
            self.doc.view.setCursorPosition(selRange.end())
        self.doc.doc.endEditing()
    
    def moveSelectionDown(self):
        """
        Moves the selected block to the next blank line.
        There MUST be a selection.
        """
        self.selectFullLines()
        cursor = self.doc.view.cursorPosition()
        docRange = self.doc.doc.documentRange()
        selRange = self.doc.view.selectionRange()
        if selRange.end().position() == docRange.end().position():
            return
        text = self.doc.selectionText()
        self.doc.doc.startEditing()
        atStart = cursor.position() == selRange.start().position()
        # Determine current depth (we could be in a long \book block)
        tokenizer = ly.tokenize.Tokenizer()
        for token in tokenizer.tokens(self.doc.textToCursor(selRange.start())):
            pass
        self.doc.doc.removeText(selRange)
        for r in self.findBlankLines(tokenizer.depth()):
            if r.start().position() > selRange.start().position():
                insert = KTextEditor.Cursor(r.end().line(), 0)
                break
        else:
            docRange = self.doc.doc.documentRange()
            self.doc.doc.insertText(docRange.end(), '\n')
            docRange = self.doc.doc.documentRange()
            insert = docRange.end()
        cursor = Cursor(insert)
        if not text.endswith('\n'):
            text += '\n'
        cursor.walk(text)
        self.doc.doc.insertText(insert, text)
        selRange = KTextEditor.Range(insert, cursor.kteCursor())
        self.doc.view.setSelection(selRange)
        if atStart:
            self.doc.view.setCursorPosition(selRange.start())
        else:
            self.doc.view.setCursorPosition(selRange.end())
        self.doc.doc.endEditing()

    def convertRelativeToAbsolute(self):
        """
        Convert \relative { }  music to absolute pitches.
        """
        selection = self.doc.view.selection()
        selRange = self.doc.view.selectionRange()
        docRange = self.doc.doc.documentRange()
        selection = selection and selRange.start().position() != selRange.end().position()
        end = selection and selRange.end() or docRange.end()
        text = self.doc.textToCursor(end)
        
        tokenizer = Tokenizer()
        tokens = tokenizer.tokens(text)
        
        # Walk through not-selected text, to track the state and the 
        # current pitch language (the LangReader instance does this).
        if selection and selRange.start().position() != (0, 0):
            for token in tokens:
                if selRange.contains(token.range.end()):
                    break
        
        changes = ChangeList()
        
        def newPitch(token, pitch, lastPitch):
            """
            Writes a new pitch with all parts except the octave taken from the
            token. The octave is set using lastPitch.
            """
            pitch.absolute(lastPitch)
            changes.replace(token, '%s%s%s' % (
                token.step,
                token.cautionary,
                pitch.octave < 0 and ',' * -pitch.octave or "'" * pitch.octave))
            
        class gen(object):
            """
            Advanced generator of tokens, discarding whitespace and comments,
            and automatically detecting \relative blocks and places where a new
            LilyPond parsing context is started, like \score inside \markup.
            """
            def __iter__(self):
                return self
                
            def next(self):
                token = tokens.next()
                while isinstance(token, (tokenizer.Space, tokenizer.Comment)):
                    token = tokens.next()
                if token == "\\relative":
                    relative(token.range.start())
                    token = tokens.next()
                elif isinstance(token, tokenizer.MarkupScore):
                    absolute()
                    token = tokens.next()
                return token
        
        source = gen()
        
        def consume():
            """ Consume tokens till the level drops (we exit a construct). """
            depth = tokenizer.depth()
            for token in source:
                yield token
                if tokenizer.depth() < depth:
                    return
        
        def absolute():
            """ Consume tokens while not doing anything. """
            for token in consume():
                pass
        
        def relative(start):
            """
            Called when a \\relative command is encountered.
            start is the position of the \\relative token, to remove it later.
            """
            # find the pitch after the relative command
            lastPitch = None
            for token in source:
                if not lastPitch and isinstance(token, tokenizer.Pitch):
                    lastPitch = Pitch.fromToken(token, tokenizer)
                    continue
                else:
                    if not lastPitch:
                        lastPitch = Pitch.c1()
                    # remove the \relative <pitch> tokens
                    changes.remove(KTextEditor.Range(start, token.range.start()))
                    # eat stuff like \new Staff == "bla" \new Voice \notes etc.
                    while True:
                        if token in ('\\new', '\\context'):
                            source.next() # skip context type
                            token = source.next()
                            if token == '=':
                                source.next() # skip context name
                                token = source.next()
                        elif isinstance(token, (tokenizer.ChordMode, tokenizer.NoteMode)):
                            token = source.next()
                        else:
                            break
                    if isinstance(token, tokenizer.OpenDelimiter):
                        # Handle full music expression { ... } or << ... >>
                        for token in consume():
                            # skip commands with pitches that do not count
                            if token in ('\\key', '\\transposition'):
                                source.next()
                            elif token == '\\transpose':
                                source.next()
                                source.next()
                            elif token == '\\octaveCheck':
                                start = KTextEditor.Cursor(token.range.start())
                                token = source.next()
                                if isinstance(token, tokenizer.Pitch):
                                    p = Pitch.fromToken(token, tokenizer)
                                    if p:
                                        lastPitch = p
                                        changes.remove(KTextEditor.Range(
                                            start, token.range.end()))
                            elif isinstance(token, tokenizer.OpenChord):
                                # handle chord
                                chord = [lastPitch]
                                for token in source:
                                    if isinstance(token, tokenizer.CloseChord):
                                        lastPitch = chord[:2][-1] # same or first
                                        break
                                    elif isinstance(token, tokenizer.Pitch):
                                        p = Pitch.fromToken(token, tokenizer)
                                        if p:
                                            newPitch(token, p, chord[-1])
                                            chord.append(p)
                            elif isinstance(token, tokenizer.Pitch):
                                p = Pitch.fromToken(token, tokenizer)
                                if p:
                                    newPitch(token, p, lastPitch)
                                    lastPitch = p
                    elif isinstance(token, tokenizer.OpenChord):
                        # Handle just one chord
                        for token in source:
                            if isinstance(token, tokenizer.CloseChord):
                                break
                            elif isinstance(token, tokenizer.Pitch):
                                p = Pitch.fromToken(token, tokenizer)
                                if p:
                                    newPitch(token, p, lastPitch)
                                    lastPitch = p
                    elif isinstance(token, tokenizer.Pitch):
                        # Handle just one pitch
                        p = Pitch.fromToken(token, tokenizer)
                        if p:
                            newPitch(token, p, lastPitch)
                    return
        
        # Do it!
        for token in source:
            pass
        changes.apply(self.doc.doc)
                    
    def convertAbsoluteToRelative(self):
        """
        Converts the selected music expression or all toplevel expressions to \relative ones.
        """
        selection = self.doc.view.selection()
        selRange = self.doc.view.selectionRange()
        docRange = self.doc.doc.documentRange()
        selection = selection and selRange.start().position() != selRange.end().position()
        end = selection and selRange.end() or docRange.end()
        text = self.doc.textToCursor(end)
        
        tokenizer = Tokenizer()
        tokens = tokenizer.tokens(text)
        
        # Walk through not-selected text, to track the state and the 
        # current pitch language (the LangReader instance does this).
        if selection and selRange.start().position() != (0, 0):
            for token in tokens:
                if selRange.contains(token.range.end()):
                    break
        
        changes = ChangeList()
        
        def newPitch(token, pitch):
            """
            Writes a new pitch with all parts except the octave taken from the
            token.
            """
            changes.replace(token, '%s%s%s' % (
                token.step,
                token.cautionary,
                pitch.octave < 0 and ',' * -pitch.octave or "'" * pitch.octave))
            
        class gen(object):
            """
            Advanced generator of tokens, discarding whitespace and comments,
            and automatically detecting \relative blocks and places where a new
            LilyPond parsing context is started, like \score inside \markup.
            """
            def __iter__(self):
                return self
                
            def next(self):
                token = tokens.next()
                while isinstance(token, (tokenizer.Space, tokenizer.Comment)):
                    token = tokens.next()
                if token == "\\relative":
                    relative()
                    token = tokens.next()
                elif isinstance(token, tokenizer.ChordMode):
                    absolute() # do not change chords
                elif isinstance(token, tokenizer.MarkupScore):
                    absolute()
                    token = tokens.next()
                return token
        
        source = gen()
        
        def consume():
            """ Consume tokens till the level drops (we exit a construct). """
            depth = tokenizer.depth()
            for token in source:
                yield token
                if tokenizer.depth() < depth:
                    return
        
        def absolute():
            """ Consume tokens while not doing anything. """
            for token in consume():
                pass
        
        def relative():
            """ Consume the whole \relative expression without doing anything. """
            # skip pitch argument
            token = source.next()
            if isinstance(token, tokenizer.Pitch):
                token = source.next()
            if isinstance(token, tokenizer.OpenDelimiter):
                for token in consume():
                    pass
            elif isinstance(token, tokenizer.OpenChord):
                while not isinstance(token, tokenizer.CloseChord):
                    token = source.next()
        
        # Do it!
        startToken = None
        for token in source:
            if isinstance(token, tokenizer.OpenDelimiter):
                # Ok, parse current expression.
                startToken = token # before which to insert the \relative command
                lastPitch = None
                chord = None
                try:
                    for token in consume():
                        # skip commands with pitches that do not count
                        if token in ('\\key', '\\transposition'):
                            source.next()
                        elif token == '\\transpose':
                            source.next()
                            source.next()
                        elif isinstance(token, tokenizer.OpenChord):
                            # Handle chord
                            chord = []
                        elif isinstance(token, tokenizer.CloseChord):
                            if chord:
                                lastPitch = chord[0]
                            chord = None
                        elif isinstance(token, tokenizer.Pitch):
                            # Handle pitch
                            p = Pitch.fromToken(token, tokenizer)
                            if p:
                                if lastPitch is None:
                                    lastPitch = Pitch.c1()
                                    lastPitch.octave = p.octave
                                    if p.note > 3:
                                        lastPitch.octave += 1
                                    changes.insert(startToken.range.start(),
                                        "\\relative %s " %
                                        lastPitch.output(tokenizer.language))
                                newPitch(token, p.relative(lastPitch))
                                lastPitch = p
                                # remember the first pitch of a chord
                                chord == [] and chord.append(p)
                except StopIteration:
                    pass # because of the source.next() statements
        if startToken is None:  # no single expression converted?
            KMessageBox.error(self.doc.app.mainwin, i18n(
                "Please select a music expression, enclosed in << ... >> or { ... }."))
            return
        changes.apply(self.doc.doc)

    def transpose(self):
        """
        Transpose all or selected pitches.
        """
        selection = self.doc.view.selection()
        selRange = self.doc.view.selectionRange()
        docRange = self.doc.doc.documentRange()
        selection = selection and selRange.start().position() != selRange.end().position()
        end = selection and selRange.end() or docRange.end()
        text = self.doc.textToCursor(end)
        
        # run the parser once to determine the language and key signature
        tokenizer = Tokenizer()
        tokens = iter(tokenizer.tokens(text))
        keyPitch = Pitch.c1()
        
        for token in tokens:
            if token == "\\key":
                for token in tokens:
                    if not isinstance(token, (tokenizer.Space, tokenizer.Comment)):
                        break
                if isinstance(token, tokenizer.Pitch):
                    p = Pitch.fromToken(token, tokenizer)
                    if p:
                        keyPitch = p
                        keyPitch.octave = 1
        
        # present a dialog
        dlg = self.transposeDialog()
        dlg.setLanguage(tokenizer.language)
        dlg.setInitialPitch(keyPitch)
        if not dlg.exec_():
            return
        transposer = dlg.transposer()
        if not transposer:
            KMessageBox.sorry(self.doc.app.mainwin, i18n(
                "Could not understand the entered pitches.\n\n"
                "Please make sure you use pitch names in the language \"%1\".",
                tokenizer.language))
            return
            
        # Go!
        tokenizer = Tokenizer()
        tokens = tokenizer.tokens(text)
        changes = ChangeList()
        
        class gen(object):
            """
            Advanced generator of tokens, discarding whitespace and comments,
            and automatically detecting \relative blocks and places where a new
            LilyPond parsing context is started, like \score inside \markup.
            
            It also handles transposition tasks that are the same in relative
            and absolute environments.
            """
            def __init__(self):
                self.inSelection = not selection
                
            def __iter__(self):
                return self
                
            def next(self):
                while True:
                    token = tokens.next()
                    if isinstance(token, (tokenizer.Space, tokenizer.Comment)):
                        continue
                    elif not self.inSelection and selRange.contains(token.range):
                        self.inSelection = True
                    # Handle stuff that's the same in relative and absolute here
                    if token == "\\relative":
                        relative()
                    elif isinstance(token, tokenizer.MarkupScore):
                        absolute(consume())
                    elif isinstance(token, tokenizer.ChordMode):
                        chordmode()
                    elif token == "\\transposition":
                        source.next() # skip pitch
                    elif token == "\\transpose":
                        if self.inSelection:
                            for token in source.next(), source.next():
                                if isinstance(token, tokenizer.Pitch):
                                    transpose(token)
                        else:
                            source.next(), source.next()
                    elif token == "\\key":
                        token = source.next()
                        if self.inSelection and isinstance(token, tokenizer.Pitch):
                            transpose(token, 0)
                    else:
                        return token
        
        source = gen()
        
        def consume():
            """ Consume tokens till the level drops (we exit a construct). """
            depth = tokenizer.depth()
            for token in source:
                yield token
                if tokenizer.depth() < depth:
                    return
        
        def transpose(token, resetOctave = None):
            """ Transpose absolute pitch in token, must be tokenizer.Pitch """
            p = Pitch.fromToken(token, tokenizer)
            if p:
                transposer.transpose(p)
                if resetOctave is not None:
                    p.octave = resetOctave
                changes.replace(token, p.output(tokenizer.language))
        
        def relative():
            """ Called when \\relative is encountered. """
            
            def transposeRelative(token, tokenizer, lastPitch):
                """
                Make a new relative pitch from token, if possible.
                Return the last pitch used (untransposed).
                """
                p = Pitch.fromToken(token, tokenizer)
                if p:
                    # absolute pitch determined from untransposed pitch of lastPitch
                    p.absolute(lastPitch)
                    if source.inSelection:
                        # we may change this pitch. Make it relative against the
                        # transposed lastPitch.
                        try:
                            last = lastPitch.transposed
                        except AttributeError:
                            last = lastPitch
                        # transpose a copy and store that in the transposed
                        # attribute of lastPitch. Next time that is used for
                        # making the next pitch relative correctly.
                        copy = p.copy()
                        transposer.transpose(copy)
                        p.transposed = copy # store transposed copy in new lastPitch
                        new = copy.relative(last)
                        if p.octaveCheck:
                            new.octaveCheck = copy.octave
                        if relPitchToken:
                            # we are allowed to change the pitch after the
                            # \relative command. lastPitch contains this pitch.
                            lastPitch.octave += new.octave
                            new.octave = 0
                            changes.replace(relPitchToken[0], lastPitch.output(tokenizer.language))
                            del relPitchToken[:]
                        changes.replace(token, new.output(tokenizer.language))
                    return p
                return lastPitch
            
            lastPitch = None
            relPitchToken = [] # we use a list so it can be changed from inside functions

            for token in source:
                if not lastPitch and isinstance(token, tokenizer.Pitch):
                    lastPitch = Pitch.fromToken(token, tokenizer)
                    if lastPitch and source.inSelection:
                        relPitchToken.append(token)
                    continue
                else:
                    if not lastPitch:
                        lastPitch = Pitch.c1()
                    # eat stuff like \new Staff == "bla" \new Voice \notes etc.
                    while True:
                        if token in ('\\new', '\\context'):
                            source.next() # skip context type
                            token = source.next()
                            if token == '=':
                                source.next() # skip context name
                                token = source.next()
                        elif isinstance(token, tokenizer.NoteMode):
                            token = source.next()
                        else:
                            break
                    if isinstance(token, tokenizer.OpenDelimiter):
                        # Handle full music expression { ... } or << ... >>
                        for token in consume():
                            if token == '\\octaveCheck':
                                token = source.next()
                                if isinstance(token, tokenizer.Pitch):
                                    p = Pitch.fromToken(token, tokenizer)
                                    if p:
                                        if source.inSelection:
                                            transposer.transpose(p)
                                            changes.replace(token, p.output(tokenizer.language))    
                                        lastPitch = p
                                        del relPitchToken[:]
                            elif isinstance(token, tokenizer.OpenChord):
                                chord = [lastPitch]
                                for token in source:
                                    if isinstance(token, tokenizer.CloseChord):
                                        lastPitch = chord[:2][-1] # same or first
                                        break
                                    elif isinstance(token, tokenizer.Pitch):
                                        chord.append(transposeRelative(token, tokenizer, chord[-1]))
                            elif isinstance(token, tokenizer.Pitch):
                                lastPitch = transposeRelative(token, tokenizer, lastPitch)
                    elif isinstance(token, tokenizer.OpenChord):
                        # Handle just one chord
                        for token in source:
                            if isinstance(token, tokenizer.CloseChord):
                                break
                            elif isinstance(token, tokenizer.Pitch):
                                lastPitch = transposeRelative(token, tokenizer, lastPitch)
                    elif isinstance(token, tokenizer.Pitch):
                        # Handle just one pitch
                        transposeRelative(token, tokenizer, lastPitch)
                    return
            
        def chordmode():
            """ Called inside \\chordmode or \\chords. """
            for token in consume():
                if source.inSelection and isinstance(token, tokenizer.Pitch):
                    transpose(token, 0)
                
        def absolute(tokens):
            """ Called when outside a possible \\relative environment. """
            for token in tokens:
                if source.inSelection and isinstance(token, tokenizer.Pitch):
                    transpose(token)
        
        # Do it!
        absolute(source)
        changes.apply(self.doc.doc)

    @lazymethod
    def transposeDialog(self):
        return TransposeDialog(self.doc.view)


class TransposeDialog(KDialog):
    def __init__(self, parent):
        KDialog.__init__(self, parent)
        self.setCaption(i18n("Transpose"))
        self.language = ""
        self.initialPitchSet = False
        w = self.mainWidget()
        w.setLayout(QtGui.QGridLayout())
        l = QtGui.QLabel(i18n("Please enter a start pitch and a destination pitch:"))
        w.layout().addWidget(l, 0, 0, 1, 4)
        self.fromPitch = QtGui.QComboBox()
        self.toPitch = QtGui.QComboBox()
        l = QtGui.QLabel(i18n("Transpose from:"))
        l.setBuddy(self.fromPitch)
        w.layout().addWidget(l, 1, 0, QtCore.Qt.AlignRight)
        w.layout().addWidget(self.fromPitch, 1, 1)
        l = QtGui.QLabel(i18n("to:"))
        l.setBuddy(self.toPitch)
        w.layout().addWidget(l, 1, 2, QtCore.Qt.AlignRight)
        w.layout().addWidget(self.toPitch, 1, 3)
        
        self.fromPitch.setEditable(True)
        self.toPitch.setEditable(True)
        self.fromPitch.setModel(self.toPitch.model())
        
    def setLanguage(self, language):
        if language != self.language:
            fromIndex = self.fromPitch.currentIndex()
            toIndex = self.toPitch.currentIndex()
            self.fromPitch.clear()
            for octave in (",", "", "'"):
                for note in range(7):
                    for alter in Rational(-1, 2), 0, Rational(1, 2):
                        self.fromPitch.insertItem(0,
                            ly.pitch.pitchWriter[language](note, alter) + octave)
            fromIndex != -1 and self.fromPitch.setCurrentIndex(fromIndex)
            toIndex != -1 and self.toPitch.setCurrentIndex(toIndex)
            self.language = language
    
    def setInitialPitch(self, pitch):
        if not self.language:
            self.setLanguage("nederlands")
        if not self.initialPitchSet:
            index = self.fromPitch.findText(pitch.output(self.language))
            if index != -1:
                self.fromPitch.setCurrentIndex(index)
                self.toPitch.setCurrentIndex(index)
                self.initialPitchSet = True
        
    def exec_(self):
        if not self.initialPitchSet:
            self.setInitialPitch(Pitch.c1())
        return KDialog.exec_(self)
    
    def pitchFrom(self, combobox):
        t = unicode(combobox.currentText())
        p = Pitch()
        p.octave = t.count("'") - t.count(",")
        result = ly.pitch.pitchReader[self.language](
            t.replace(",", "").replace("'", ""))
        if result:
            p.note, p.alter = result
            return p
            
    def transposer(self):
        fromPitch = self.pitchFrom(self.fromPitch)
        toPitch = self.pitchFrom(self.toPitch)
        if fromPitch and toPitch:
            return ly.pitch.Transposer(fromPitch, toPitch)
        
        
class Pitch(object):
    def __init__(self):
        self.note = 0           # base note (c, d, e, f, g, a, b)
        self.alter = 0          # # = 2; b = -2; natural = 0
        self.octave = 0         # '' = 2; ,, = -2
        self.cautionary = ''    # '!' or '?' or ''
        self.octaveCheck = None
    
    @classmethod
    def c1(cls):
        """ Return a pitch c' """
        p = cls()
        p.octave = 1
        return p

    @classmethod
    def fromToken(cls, token, tokenizer):
        result = tokenizer.readStep(token)
        if result:
            p = cls()
            p.note, p.alter = result
            p.octave = token.octave.count("'") - token.octave.count(",")
            p.cautionary = token.cautionary
            if token.octcheck:
                p.octaveCheck = token.octcheck.count("'") - token.octcheck.count(",")
            return p

    def copy(self):
        """ Return a new instance with our attributes. """
        p = self.__class__()
        p.note = self.note
        p.alter = self.alter
        p.cautionary = self.cautionary
        p.octave = self.octave
        return p
        
    def absolute(self, lastPitch):
        """
        Set our octave height from lastPitch (which is absolute), as if
        we are a relative pitch. If the octaveCheck attribute is set to an
        octave number, that is used instead.
        """
        if self.octaveCheck is not None:
            self.octave = self.octaveCheck
        else:
            dist = self.note - lastPitch.note
            if dist > 3:
                dist -= 7
            elif dist < -3:
                dist += 7
            self.octave += lastPitch.octave  + (lastPitch.note + dist) // 7
        
    def relative(self, lastPitch):
        """
        Returns a new Pitch instance with the current pitch relative to
        the absolute pitch in lastPitch.
        """
        p = self.copy()
        dist = self.note - lastPitch.note
        p.octave = self.octave - lastPitch.octave + (dist + 3) // 7
        return p
        
    def output(self, language):
        return '%s%s%s' % (
            ly.pitch.pitchWriter[language](self.note, self.alter),
            self.cautionary,
            self.octave < 0 and ',' * -self.octave or "'" * self.octave)
    

class ChangeList(object):
    """
    Represents a list of changes to a KTextEditor.Document.
    A change consists of a token (from which the range is saved) and possibly a 
    replacement string.
    
    Changes must be appended in sequential order.  Call applyChanges() with
    the document from which the text originated to have the changes applied.
    (This is done in reverse order, so the ranges remain valid.)
    """
    def __init__(self):
        self._changes = []
        
    def replace(self, tokenOrRange, replacement):
        """
        Adds a token and its replacement.
        If the token is not a KTextEditor.Range, it must have a range attribute
        with the KTextEditor.Range it represents.
        """
        if isinstance(tokenOrRange, KTextEditor.Range):
            self._changes.append((tokenOrRange, replacement))
        elif tokenOrRange != replacement:
            self._changes.append((tokenOrRange.range, replacement))
    
    def insert(self, cursor, text):
        """
        Add a text insertion at the given cursor position.
        """
        self._changes.append((cursor, text))
    
    def remove(self, tokenOrRange):
        """
        Add a token or range to be removed.
        """
        if isinstance(tokenOrRange, KTextEditor.Range):
            self._changes.append((tokenOrRange, None))
        else:
            self._changes.append((tokenOrRange.range, None))
        
    def apply(self, doc):
        """
        Apply the changes to KTextEditor.Document doc.
        This is done in a way that does not disturb smart point and click.
        """
        doc.startEditing()
        for rangeCur, text in reversed(self._changes):
            if isinstance(rangeCur, KTextEditor.Cursor):
                doc.insertText(rangeCur, text)
            else:
                if text:
                    # dont disturb point and click
                    doc.insertText(rangeCur.end(), text)
                doc.removeText(rangeCur)
        doc.endEditing()


class Cursor(ly.tokenize.Cursor):
    """
    A Cursor that can easily interchange with KTextEditor.Cursor.
    """
    def __init__(self, ktecursor = None):
        super(Cursor, self).__init__()
        if ktecursor:
            self.line = ktecursor.line()
            self.column = ktecursor.column()
            
    def kteCursor(self):
        """ Return a corresponding KTextEditor.Cursor instance """
        return KTextEditor.Cursor(self.line, self.column)
    

class RangeMixin(object):
    """
    Mixin with a Tokenizer (sub)class to iterate over the tokens returned by
    tokenizer.tokens(), adding a KTextEditor.Range to every token, describing
    its place. See the ly.tokenize module.
    Mixin before classes that drop tokens, otherwise the cursorpositions will
    not be updated correctly.
    """
    def tokens(self, text, pos = 0, cursor = None):
        if cursor is None:
            cursor = Cursor()
        if pos:
            cursor.walk(text[:pos])
        start = cursor.kteCursor()
        for token in super(RangeMixin, self).tokens(text, pos):
            cursor.walk(token)
            end = cursor.kteCursor()
            token.range = KTextEditor.Range(start, end)
            start = end
            yield token


class RangeTokenizer(RangeMixin, ly.tokenize.Tokenizer):
    """ A Tokenizer that adds ranges to the tokens. """
    pass


class LangReaderMixin(object):
    """
    Mixin with a Tokenizer (sub)class to read tokens from a source and
    remember the pitch name language (from \include "language.ly" statements).
    """
    def reset(self, *args):
        super(LangReaderMixin, self).reset(*args)
        self.language = "nederlands"
        
    def tokens(self, text, pos = 0):
        for token in super(LangReaderMixin, self).tokens(text, pos):
            if isinstance(token, self.IncludeFile):
                langName = token[1:-4]
                if langName in ly.pitch.pitchInfo:
                    self.language = langName
            yield token


class Tokenizer(LangReaderMixin, RangeMixin, ly.tokenize.MusicTokenizer):
    """
    A Tokenizer that remenmbers its pitch name language and adds ranges
    to all tokens.
    """
    def readStep(self, pitchToken):
        return ly.pitch.pitchReader[self.language](pitchToken.step)



def isblank(text):
    """ Returns True if text is None, empty or only contains spaces. """
    return not text or text.isspace()
