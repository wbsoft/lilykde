# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
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

from __future__ import unicode_literals

"""
Advanced manipulations on LilyPond documents.
"""

import os, re, weakref
from fractions import Fraction

from PyQt4 import QtCore, QtGui

from PyKDE4.kdecore import KGlobal, i18n
from PyKDE4.kdeui import KDialog, KIcon, KMessageBox
from PyKDE4.ktexteditor import KTextEditor

import ly.rx, ly.dynamic, ly.pitch, ly.parse, ly.tokenize, ly.tools, ly.version
from kateshell.app import cacheresult
from kateshell.widgets import promptText
from kateshell.mainwindow import addAccelerators
from frescobaldi_app.mainapp import lilyPondCommand


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
            a.triggered.connect((lambda lang: lambda: self.changeLanguage(lang))(lang))
        addAccelerators(menu.actions())
    
    def changeLanguage(self, lang):
        """
        Change the LilyPond pitch name language in our document to lang.
        """
        text, start = self.doc.selectionOrDocument()
        try:
            changes, includeCommandChanged = ly.tools.translate(text, lang, start)
        except ly.QuarterToneAlterationNotAvailable:
            KMessageBox.sorry(self.doc.app.mainwin, i18n(
                "Can't perform the requested translation.\n\n"
                "The music contains quarter-tone alterations, but "
                "those are not available in the pitch language \"%1\".",
                lang))
            return
        
        # Apply the changes.
        with self.doc.editContext():
            changes.applyToCursor(EditCursor(self.doc.doc))
            if not start and not includeCommandChanged:
                self.addLineToTop('\\include "{0}.ly"'.format(lang))
        if start and not includeCommandChanged:
            KMessageBox.information(self.doc.app.mainwin,
                '<p>{0}</p><p><tt>\\include "{1}.ly"</tt></p>'.format(
                i18n("The pitch language of the selected text has been "
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
            result = "{0} ={1} {{\n{2}\n}}\n".format(name, mode, text)
            result = self.doc.indent(result)
        else:
            result = "{0} ={1} {{ {2} }}\n".format(name, mode, text)
            
        if not isblank(self.doc.line(insertLine)):
            result += '\n'
        if insertLine > 0 and not isblank(self.doc.line(insertLine - 1)):
            result = '\n' + result
        
        # add space if necessary
        variable = "\\" + name
        end = selRange.end()
        if not isblank(self.doc.line(end.line())[end.column():end.column()+1]):
            variable += " "

        # do it:
        cursor = KTextEditor.Cursor(insertLine, 0)
        with self.doc.editContext():
            self.doc.replaceSelectionWith(variable, keepSelection=False)
            self.doc.doc.insertText(cursor, result)
        
    def repeatLastExpression(self):
        """
        Repeat the last entered music expression (without duration)
        """
        # find the last non-empty line
        curPos = self.doc.view.cursorPosition()
        lineNum = curPos.line()
        while lineNum > 0 and isblank(self.doc.line(lineNum)):
            lineNum -= 1
            
        text = self.doc.doc.text(
            KTextEditor.Range(KTextEditor.Cursor(lineNum, 0), curPos))
        matchObj = None
        for m in ly.rx.chord.finditer(text):
            if m.group('chord'):
                matchObj = m
        if not matchObj:
            return # nothing to repeat
        
        # leave out the duration
        result = matchObj.group('chord')
        
        # remove octave mark from first pitch if in relative mode
        tokenizer = RelativeTokenizer()
        for token in tokenizer.tokens(self.doc.textToCursor()):
            pass
        if isinstance(tokenizer.parser(), tokenizer.RelativeParser):
            result = re.sub(ly.rx.named_pitch,
                lambda m: m.group('step') + m.group('cautionary'), result, 1)
        
        # add articulations, etc
        stuff = text[matchObj.end():]
        if not isblank(stuff):
            stuff = stuff.splitlines()[0]
            # Filter the things we want to repeat.  E.g. slur events don't
            # make much sense, but artications do.  We skip comments and
            # strings to avoid matching stuff inside those.
            result += ''.join(
                m.group(1)
                for m in re.compile(
                    r'('                            # keep:
                        r'[-_^][_.+|>^-]'           # - articulation shorthands
                        r'|[_^]?~'                  # - ties
                        r'|\\rest(?![A-Za-z])'      # - pitched rests
                    r')'                            # skip:
                        r'|"(?:\\\\|\\\"|[^\"])*"'  # - quoted strings
                        r'|%.*?$'                   # - comments
                    ).finditer(stuff)
                if m.group(1))
        
        # write it in the document, add a space if necessary
        col = curPos.column()
        if col > 0 and not isblank(self.doc.line()[col-1]):
            result = " " + result
        self.doc.view.insertText(result)
    
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
            if end.line() < self.doc.doc.lines() - 1:
                end.setColumn(0)
                end.setLine(end.line() + 1)
            else:
                end.setColumn(len(self.doc.line(end.line())))
        self.doc.view.setSelection(KTextEditor.Range(start, end))
        if atStart:
            self.doc.view.setCursorPosition(start)
        else:
            self.doc.view.setCursorPosition(end)
    
    def adjustCursorToChords(self):
        """
        Adjust the cursor position in the following way:
        
        if the cursor is inside a chord, pitch or rest:
            position the cursor right after the chord
        """
        cursor = self.doc.view.cursorPosition()
        col = cursor.column()
        text = self.doc.line(cursor.line())
        # inside a chord?
        for m in ly.rx.chord_rest.finditer(text):
            if (m.group('full')
                and m.start() <= col <= m.end()):
                cursor.setColumn(m.end())
                self.doc.view.setCursorPosition(cursor)
                return
        
    def adjustSelectionToChords(self):
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
        if re.match(ly.rx.step + "|" + ly.rx.rest, text[col:]):
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
        with self.doc.editContext():
            for old, new in zip(oldindents, newindents):
                if old != new:
                    self.doc.doc.replaceText(
                        KTextEditor.Range(startline, 0, startline, len(old)), new)
                startline += 1
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
        for m in re.finditer(r'\\include\s*"?([^"]+)', text):
            if m.start() <= col <= m.end():
                fileName = m.group(1)
                a = menu.addAction(KIcon("document-open"), i18n("Open %1", fileName))
                a.triggered.connect(lambda: self.openIncludeFile(fileName))
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
            menu.addSeparator()
            menu.addAction(
                self.doc.app.mainwin.actionCollection().action("lyrics_hyphen"))
            menu.addAction(
                self.doc.app.mainwin.actionCollection().action("lyrics_copy_dehyphen"))
    
    def openIncludeFile(self, fileName):
        """
        Opens a fileName that was found after an \\include command.
        First, it tries to open the local file, if that fails, look in the
        LilyPond data directory.
        """
        path = self.doc.localPath()
        if path:
            localdir = os.path.dirname(path)
        else:
            localdir = self.doc.app.defaultDirectory() or os.getcwd()
        url = os.path.normpath(os.path.join(localdir, fileName))
        if not os.path.exists(url):
            datadir = ly.version.LilyPondInstance(lilyPondCommand()).datadir()
            if datadir and os.path.exists(os.path.join(datadir, 'ly', fileName)):
                url = os.path.join(datadir, 'ly', fileName)
        self.doc.app.openUrl(url).setActive()
        
    def insertTypographicalQuote(self, double = False):
        """
        Insert a single or double quotation mark at the current cursor position.
        If the character left to the cursor is a space or a double quote,
        use the left typographical quote, otherwise the right.
        """
        selection = self.doc.selectionText()
        if selection:
            repl = double and '\u201C{0}\u201D' or '\u2018{0}\u2019'
            self.doc.replaceSelectionWith(repl.format(selection), keepSelection=False)
        else:
            cursor = self.doc.view.cursorPosition()
            line, col = cursor.line(), cursor.column()
            right = col > 0 and self.doc.line(line)[col-1] not in '" \t'
            self.doc.view.insertText({
                (False, False): '\u2018',     # LEFT SINGLE QUOTATION MARK
                (False, True ): '\u2019',     # RIGHT SINGLE QUOTATION MARK
                (True,  False): '\u201C',     # LEFT DOUBLE QUOTATION MARK
                (True,  True ): '\u201D',     # RIGHT DOUBLE QUOTATION MARK
                }[(double, right)])

    def insertBarLine(self, bar):
        """
        Insert a \\bar ".." command with the given type.
        """
        self.insertIndented('\\bar "{0}"'.format(bar))
    
    def insertBreathingSign(self, sign):
        """
        Insert a \\breathe mark with possibly an override for another shape.
        """
        if sign == 'rcomma':
            text = '\\breathe'
        else:
            text = ("\\once \\override BreathingSign #'text = "
                    '#(make-musicglyph-markup "scripts.{0}")\n'
                    "\\breathe").format(sign.replace('_', '.'))
        self.insertIndented(text)
        
    def insertIndented(self, text, cursor=None, wholeLines=None):
        """Inserts text on the given or current cursor position.
        
        The following protocol is used:
        
        - if there is a newline in the text or wholeLines is True:
            add newlines if necessary to have the text on its own lines.
        - if wholeLines is False:
            don't add newlines
        - if no newlines were added:
            - if the cursor is at a non-space character:
                add a space after the text
            - if the cursor is just after a non-space character:
                add a space before the text.
        """
        cursor = cursor or self.doc.view.cursorPosition()
        line, col = cursor.line(), cursor.column()
        before = self.doc.line(line)[:col]
        after = self.doc.line(line)[col:]
        remove = None
        if wholeLines or (wholeLines is None and '\n' in text):
            if not isblank(after):
                text += '\n'
                spaces = len(after) - len(after.lstrip())
                if spaces:
                    remove = KTextEditor.Range(line, col, line, col + spaces)
            text = '\n' + self.doc.indent(text, self.doc.currentIndent(cursor))
            if isblank(before):
                text = text.lstrip()
        else:
            if before and not before[-1].isspace():
                text = ' ' + text
            if after and not after[0].isspace():
                text += ' '
        if remove:
            self.doc.doc.replaceText(remove, text)
        else:
            self.doc.doc.insertText(cursor, text)
        
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
        See lqi.py Articulations.
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
            with self.doc.editContext():
                for i in reversed(insertions):
                    self.doc.doc.insertText(i, art)
            self.doc.view.removeSelection()
        else:
            self.adjustCursorToChords()
            self.doc.view.insertText(art)
    
    _spannerDynamics = {
        'hairpin_cresc': '\\<',
        'hairpin_dim':   '\\>',
        'cresc':         '\\cresc',
        'decresc':       '\\decresc',
        'dim':           '\\dim',
    }
        
    def addDynamic(self, name, direction):
        """
        Add dynamics with name, direction (-1, 0 or 1).
        See lqi.py Dynamics.
        """
        isSpanner = name in self._spannerDynamics
        if isSpanner:
            dynamic = self._spannerDynamics[name]
        elif name in ly.dynamic.marks:
            dynamic = '\\' + name
        else:
            return
        direction = ['_', '', '^'][direction+1]
        
        text = self.doc.selectionText()
        if text:
            items = list(m for m in ly.rx.chord_rest.finditer(text) if m.group('full'))
            if len(items) >= 2:
                # match objects for the first note and the last in the selection
                first, last = items[0], items[-1]
                
                # text after the first note/chord/rest
                afterFirst = text[first.end('full'):]
                
                # text after the last note/chord/rest
                afterLast = text[last.end('full'):]
                selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
                docRange = self.doc.doc.documentRange()
                afterLast += self.doc.doc.text(
                    KTextEditor.Range(selRange.end(), docRange.end()))[:10]
                
                start = Cursor(selRange.start())
                start.walk(text[:first.end('full')])
                end = Cursor(selRange.start())
                end.walk(text[:last.end('full')])
                
                if isSpanner:
                    with self.doc.editContext():
                        # don't terminate the spanner if it already ends with a dynamic
                        if not ly.rx.dynamic_mark.match(afterLast):
                            self.doc.doc.insertText(end.kteCursor(), '\\!')
                        # skip a dynamic mark that might already be at the start
                        m = ly.rx.dynamic_mark.match(afterFirst)
                        if m:
                            start.walk(text[:m.end()])
                            direction = ''
                        # on this place, insert the spanner
                        self.doc.doc.insertText(start.kteCursor(), direction + dynamic)
                else:
                    # if a spanner ends on the end, replace it with our dynamic
                    if afterLast.startswith('\\!'):
                        r = KTextEditor.Range(
                            end.line, end.column, end.line, end.column + 2)
                        self.doc.doc.replaceText(r, dynamic)
                    elif ly.rx.dynamic_mark.match(afterFirst):
                        self.doc.doc.insertText(end.kteCursor(), direction + dynamic)
                    else:
                        self.doc.doc.insertText(start.kteCursor(), direction + dynamic)
                return
        self.adjustCursorToChords()
        self.doc.view.insertText(direction + dynamic)
        
    def addSpanner(self, name, direction=0):
        """ Add a simple spanner to the selected music. """
        if name == "slur":
            spanner = '(', ')'
        elif name == "beam":
            spanner = '[', ']'
        elif name == "trill":
            spanner = '\\startTrillSpan', '\\stopTrillSpan'
        
        text = self.doc.selectionText()
        if not text:
            return
            
        items = list(m for m in ly.rx.chord_rest.finditer(text) if m.group('full'))
        if len(items) < 2:
            return # can't add spanner to one note or chord
        
        first, last = items[0], items[-1]
        selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
        start = Cursor(selRange.start())
        start.walk(text[:first.end('full')])
        end = Cursor(selRange.start())
        end.walk(text[:last.end('full')])
        
        with self.doc.editContext():
            self.doc.doc.insertText(end.kteCursor(), spanner[1])
            self.doc.doc.insertText(start.kteCursor(), spanner[0])

    def wrapSelection(self, text, before='{', after='}', alwaysMultiLine=False):
        """
        Wrap a piece of text inside some kind of brace construct. Returns the
        replacement. The piece of text is also expected to be the selection of
        the document, because this routine needs to know the indent of the
        resulting text. E.g.:
        wrapSelection("c d e f", "\\relative c' {", "}") returns
        "\\relative c' { c d e f }"
        """
        # preserve space at start and end of selection
        space1, sel, space2 = re.compile(
            r'^(\s*)(.*?)(\s*)$', re.DOTALL).match(text).groups()
        if alwaysMultiLine or '\n' in text:
            result = "{0}\n{1}\n{2}".format(before, sel, after)
            # indent the result corresponding with the first selection line.
            selRange = self.doc.view.selectionRange()
            indentDepth = self.doc.currentIndent(selRange.start(), False)
            result = self.doc.indent(result, indentDepth).lstrip()
        else:
            result = "{0} {1} {2}".format(before, sel, after)
        # re-add the space at start and end of selection
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
        with self.doc.editContext():
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
        with self.doc.editContext():
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

    def convertRelativeToAbsolute(self):
        """
        Convert \relative { }  music to absolute pitches.
        """
        text, start = self.doc.selectionOrDocument()
        ly.tools.relativeToAbsolute(text, start).applyToCursor(EditCursor(self.doc.doc))
    
    def convertAbsoluteToRelative(self):
        """
        Converts the selected music expression or all toplevel expressions to \relative ones.
        """
        text, start = self.doc.selectionOrDocument()
        try:
            ly.tools.absoluteToRelative(text, start).applyToCursor(EditCursor(self.doc.doc))
        except ly.NoMusicExpressionFound:
            KMessageBox.error(self.doc.app.mainwin, i18n(
                "Please select a music expression, enclosed in << ... >> or { ... }."))

    def transpose(self):
        """
        Transpose all or selected pitches.
        """
        text, start = self.doc.selectionOrDocument()
    
        # determine the language and key signature
        language, keyPitch = ly.tools.languageAndKey(text)
        
        # present a dialog
        dlg = self.transposeDialog()
        dlg.setLanguage(language)
        dlg.setInitialPitch(keyPitch)
        if not dlg.exec_():
            return
        transposer = dlg.transposer()
        if not transposer:
            KMessageBox.sorry(self.doc.app.mainwin, i18n(
                "Could not understand the entered pitches.\n\n"
                "Please make sure you use pitch names in the language \"%1\".",
                language))
            return
        try:
            ly.tools.transpose(text, transposer, start).applyToCursor(EditCursor(self.doc.doc))
        except ly.QuarterToneAlterationNotAvailable:
            KMessageBox.sorry(self.doc.app.mainwin, i18n(
                "Can't perform the requested transposition.\n\n"
                "The transposed music would contain quarter-tone alterations "
                "that are not available in the pitch language \"%1\".",
                language))
        
    @cacheresult
    def transposeDialog(self):
        return TransposeDialog(self.doc.view)


class TransposeDialog(KDialog):
    def __init__(self, parent):
        KDialog.__init__(self, parent)
        self.setCaption(i18n("Transpose"))
        self.setHelp("transpose")
        self.setButtons(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel | KDialog.Help ))
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
        
        for c in self.fromPitch, self.toPitch:
            c.setEditable(True)
            c.setInsertPolicy(QtGui.QComboBox.NoInsert)
            c.setCompleter(None)
        self.fromPitch.setModel(self.toPitch.model())
        
    def setLanguage(self, language):
        if language != self.language:
            fromIndex = self.fromPitch.currentIndex()
            toIndex = self.toPitch.currentIndex()
            self.fromPitch.clear()
            for octave in (",", "", "'"):
                for note in range(7):
                    for alter in Fraction(-1, 2), 0, Fraction(1, 2):
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
            self.setInitialPitch(ly.pitch.Pitch.c0())
        self.toPitch.setFocus()
        return KDialog.exec_(self)
    
    def pitchFrom(self, combobox):
        t = combobox.currentText()
        p = ly.pitch.Pitch()
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
    Mixin before classes that drop tokens, otherwise the cursor positions will
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


class RelativeTokenizer(ly.tokenize.Tokenizer):
    """
    A tokenizer to quickly check if we are in relative mode.
    """
    class Relative(ly.tokenize.Tokenizer.Command):
        rx = r"\\relative\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.RelativeParser, self)
    
    class ToplevelParser(ly.tokenize.Tokenizer.ToplevelParser):
        items = staticmethod(lambda cls: (cls.Relative,) +
            ly.tokenize.Tokenizer.ToplevelParser.items(cls))
            
    class RelativeParser(ToplevelParser):
        argcount = 2 # TODO: account for (deprecated) \relative without pitch
        

class EditCursor(ly.tokenize.Cursor):
    """
    Translates changes to a Python string in a ly.tokenize.ChangeList
    to changes to a KTextEditor.Document and applies them.
    Can be used as a context manager, in which case it folds all edits
    in one undo action.
    """
    def __init__(self, doc):
        super(EditCursor, self).__init__()
        self.doc = doc
    
    def __enter__(self):
        self.doc.startEditing()
        
    def __exit__(self, *args):
        self.doc.endEditing()
        
    def insertText(self, text):
        self.doc.insertText(KTextEditor.Cursor(self.line, self.column), text)
        
    def replaceText(self, text):
        # Avoid disturbing point and click
        self.doc.insertText(KTextEditor.Cursor(self.anchorLine, self.anchorColumn), text)
        self.removeText()
        
    def removeText(self):
        self.doc.removeText(KTextEditor.Range(
            self.line, self.column, self.anchorLine, self.anchorColumn))
    

def isblank(text):
    """ Returns True if text is None, empty or only contains spaces. """
    return not text or text.isspace()
