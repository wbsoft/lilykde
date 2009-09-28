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

from PyQt4 import QtCore, QtGui

from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KIcon, KMessageBox
from PyKDE4.ktexteditor import KTextEditor

import ly.rx, ly.pitch, ly.parse, ly.tokenize
from frescobaldi_app.widgets import promptText

class DocumentManipulator(object):
    """
    Can perform manipulations on a LilyPond document.
    """
    def __init__(self, doc):
        self._doc = weakref.ref(doc)

    @property
    def doc(self):
        return self._doc()
        
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
        
        state = ly.tokenize.State()
        lastCommand = None
        writer = ly.pitch.pitchWriter[lang]
        reader = ly.pitch.pitchReader["nederlands"]
        tokenizer = tokenizeRange(text, state=state)
        
        # Walk through not-selected text, to track the state and the 
        # current pitch language.
        if selection:
            for token in tokenizer:
                if isinstance(token, ly.tokenize.Command):
                    lastCommand = token
                elif (isinstance(token, ly.tokenize.String)
                    and lastCommand == "\\include"):
                    langName = token[1:-4]
                    if langName in ly.pitch.pitchInfo.keys():
                        reader = ly.pitch.pitchReader[langName]
                if selection.contains(token.range.end()):
                    break
        
        # Now walk through the part that needs to be translated.
        changes = ChangeList()
        includeCommandChanged = False
        for token in tokenizer:
            if isinstance(token, ly.tokenize.Command):
                lastCommand = token
            elif (isinstance(token, ly.tokenize.String)
                and lastCommand == "\\include"):
                langName = token[1:-4]
                if langName in ly.pitch.pitchInfo.keys():
                    reader = ly.pitch.pitchReader[langName]
                    changes.append(token, '"%s.ly"' % lang)
                    includeCommandChanged = True
            elif isinstance(token, ly.tokenize.PitchWord):
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
                    changes.append(token, replacement)
        
        # Apply the changes.
        self.doc.doc.startEditing()
        changes.applyChanges(self.doc.doc)
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
        
        # find out in what input mode we are
        mode = ""
        state = ly.tokenize.State()
        selRange = self.doc.view.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
        text = self.doc.textToCursor(selRange.start())
        for token in ly.tokenize.tokenize(text, state=state):
            pass
        for s in reversed(state.state):
            if isinstance(s, ly.tokenize.InputModeParser):
                if isinstance(s, ly.tokenize.LyricModeParser):
                    mode = " \\lyricmode"
                elif isinstance(s, ly.tokenize.ChordModeParser):
                    mode = " \\chordmode"
                elif isinstance(s, ly.tokenize.FigureModeParser):
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
        
        if start.column() > 0:
            start.setColumn(0)
        if end.column() == 0 and end.line() > start.line():
            end.setLine(end.line() - 1)
        end.setColumn(len(self.doc.line(end.line())))
        self.doc.view.setSelection(KTextEditor.Range(start, end))
            
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
            state = ly.tokenize.State()
            for token in ly.tokenize.tokenize(self.doc.textToCursor(cursor), state=state):
                pass
            startscheme = isinstance(state.parser(), ly.tokenize.SchemeParser)
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
        state = ly.tokenize.State()
        for token in ly.tokenize.tokenize(self.doc.textToCursor(cursor), state=state):
            pass
        
        # Hyphenate Lyrics
        if selection and isinstance(state.parser(), ly.tokenize.LyricModeParser):
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
        

class ChangeList(object):
    """
    Represents a list of changes to a KTextEditor.Document.
    A change consists of a token (from which the range is saved) and a 
    replacement string.
    
    Changes must be appended in sequential order.  Call applyChanges() with
    the document from which the text originated to have the changes applied.
    (This is done in reverse order, so the ranges remain valid.)
    """
    def __init__(self):
        self._changes = []
        
    def append(self, token, replacement):
        """
        Adds a token and its replacement.
        The token must have a range attribute with the KTextEditor.Range it
        represents. See the tokenizeRange function.
        """
        if token != replacement:
            self._changes.append((token.range, replacement))

    def applyChanges(self, doc):
        """
        Apply the changes to KTextEditor.Document doc.
        This is done in a way that does not disturb smart point and click.
        """
        doc.startEditing()
        for r, text in reversed(self._changes):
            doc.insertText(r.end(), text)
            doc.removeText(r)
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
    

def tokenizeRange(text, pos = 0, state = None, cursor = None):
    """
    Iterate over the tokens returned by tokenize(), adding a
    KTextEditor.Range to every token, describing its place.
    See the ly.tokenize module.
    """
    if cursor is None:
        cursor = Cursor()
    if pos:
        cursor.walk(text[:pos])
    start = cursor.kteCursor()
    for token in ly.tokenize.tokenize(text, pos, state):
        cursor.walk(token)
        end = cursor.kteCursor()
        token.range = KTextEditor.Range(start, end)
        start = end
        yield token
 
def isblank(text):
    """ Returns True if text is None, empty or only contains spaces. """
    return not text or text.isspace()
