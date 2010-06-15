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
LilyPond auto completion
"""

import re

from PyQt4.QtCore import QModelIndex, Qt
from PyQt4.QtGui import QBrush, QColor, QTextFormat
from PyKDE4.kdecore import KGlobal
from PyKDE4.ktexteditor import KTextEditor

import ly.tokenize, ly.version, ly.words, ly.colors
import frescobaldi_app.version
from frescobaldi_app.mainapp import lilyPondCommand


class CompletionHelper(object):
    """
    Helper class that contains a list of completions.
    """
    # roles on the Name column
    roles = {
        KTextEditor.CodeCompletionModel.CompletionRole:
            KTextEditor.CodeCompletionModel.FirstProperty |
            KTextEditor.CodeCompletionModel.Public |
            KTextEditor.CodeCompletionModel.LastProperty,
        KTextEditor.CodeCompletionModel.ScopeIndex: 0,
        KTextEditor.CodeCompletionModel.MatchQuality: 10,
        KTextEditor.CodeCompletionModel.HighlightingMethod: None,
        KTextEditor.CodeCompletionModel.InheritanceDepth: 0,
    }
    
    def __init__(self, model, resultList=None):
        """
        model is the KTextEditor.CodeCompletionModel helped
        by this object.
        """
        self.model = model
        self.resultList = resultList or []
    
    def index(self, row, column, parent):
        if (row < 0 or row >= len(self.resultList) or
            column < 0 or column >= KTextEditor.CodeCompletionModel.ColumnCount or
            parent.isValid()):
            return QModelIndex()
        return self.model.createIndex(row, column, 0)
        
    def rowCount(self, parent):
        if parent.isValid():
            return 0 # Do not make the model look hierarchical
        else:
            return len(self.resultList)

    def data(self, index, role):
        if index.column() == KTextEditor.CodeCompletionModel.Name:
            if role == Qt.DisplayRole:
                return self.resultList[index.row()]
            try:
                return self.roles[role]
            except KeyError:
                pass
    
    def executeCompletionItem(self, doc, word, row):
        pass


class CompletionList(CompletionHelper):
    """
    Contains completions presented as a simple list.
    """
    def executeCompletionItem(self, doc, word, row):
        text = self.resultList[row]
        if '{}' in text:
            text = text.replace('{}', '{\n(|)\n}')
            self.model.doc.manipulator().insertTemplate(text, word.start(), word)
            return True


class VarCompletions(CompletionHelper):
    """
    List of vars, that get ' = ' after themselves.
    """
    def executeCompletionItem(self, doc, word, row):
        text = self.resultList[row]
        line = doc.line(word.end().line())[word.end().column():]
        if not line.lstrip().startswith('='):
            text += ' = '
        doc.replaceText(word, text)
        return True


class ColorCompletions(CompletionHelper):
    """
    Completions with color, that show the color name highlighted
    """
    roles = CompletionHelper.roles.copy()
    roles.update({
        KTextEditor.CodeCompletionModel.HighlightingMethod:
            KTextEditor.CodeCompletionModel.CustomHighlighting
    })
    
    def data(self, index, role):
        if index.column() == KTextEditor.CodeCompletionModel.Name:
            name, (r, g, b) = self.resultList[index.row()]
            if role == Qt.DisplayRole:
                return name
            elif role == KTextEditor.CodeCompletionModel.CustomHighlight:
                format = QTextFormat()
                color = QColor.fromRgbF(r, g, b)
                format.setBackground(QBrush(color))
                return [0, len(name), format]
        return super(ColorCompletions, self).data(index, role)


class ExpansionCompletions(CompletionHelper):
    """
    Looks in the expansions, but skips expansions.
    """
    def __init__(self, model):
        self.mgr = model.doc.app.mainwin.expandManager()
        self.expansions = self.mgr.expansionsList()
        descriptions = [self.mgr.description(name) for name in self.expansions]
        result = ['{0} ({1})'.format(e, d) for e, d in zip(self.expansions, descriptions)]
        super(ExpansionCompletions, self).__init__(model, result)

    def executeCompletionItem(self, doc, word, row):
        self.mgr.doExpand(self.expansions[row], word)
        return True


def getCompletions(model, view, word, invocationType):
    """
    Returns an object that describes the matches that
    are useful in the current context.
    """
    matches = findMatches(model, view, word, invocationType)
    if isinstance(matches, CompletionHelper):
        return matches
    else:
        return CompletionList(model, matches)
        
def findMatches(model, view, word, invocationType):
    """
    Return either a simple list of matches that are useful in the current
    context, or a CompletionHelper instance that can handle specialized
    completions itself.
    """
    doc = view.document()
    line, col = word.start().line(), word.start().column()
    text = doc.line(line)[:col]
    
    # determine what the user tries to type
    # very specific situations:
    if re.search(r'\\(consists|remove)\s*"?$', text):
        return ly.words.engravers
    if re.search(r'\bmidiInstrument\s*=\s*#?"$', text):
        return ly.words.midi_instruments
    if re.search(r'\\musicglyph\s*#"$', text):
        return musicglyph_names()
    if re.search(r'\bmarkFormatter\s*=\s*#$', text):
        return ly.words.mark_formatters
    if re.search(r'\\key\s+[a-z]+\s*\\$', text):
        return ly.words.modes
    if re.search(r'\\(un)?set\b\s*$', text):
        return ly.words.contexts + ly.words.contextproperties
    if re.search(r'\\(new|change|context)\s+$', text):
        return ly.words.contexts
    if ly.words.set_context_re.search(text):
        return ly.words.contextproperties
    if ly.words.context_re.search(text):
        return ly.words.grobs
    if text.endswith("#'"):
        m = ly.words.grob_re.search(text[:-2])
        if m:
            return ly.words.schemeprops(m.group(1))
        if re.search(r"\\tweak\b\s*$", text[:-2]):
            return ly.words.schemeprops()
    if re.search(r"\\(override|revert)\s+$", text):
        return ly.words.contexts + ly.words.grobs
    if re.search(r'\\repeat\s+"?$', text):
        return ly.words.repeat_types
    if re.search(r'\\clef\s*"$', text):
        return ly.words.clefs
    if re.search(r"\\clef\s+$", text):
        return ly.words.clefs_plain
    if re.search(r"\bcolor\s*=?\s*#$", text):
        return ColorCompletions(model, ly.colors.colors_predefined)
    if re.search(r"\bx11-color\s*'$", text):
        return ColorCompletions(model, ly.colors.colors_x11)
    if re.search(r"#'break-visibility\s*=\s*#$", text):
        return ly.words.break_visibility
    # parse to get current context
    fragment = doc.text(KTextEditor.Range(
        KTextEditor.Cursor(0, 0), word.start()))
    tokenizer = ly.tokenize.Tokenizer()
    token = None # in case the next loop does not run at all
    for token in tokenizer.tokens(fragment):
        pass
    # don't bother if we are inside a string or comment
    if isinstance(token, (tokenizer.Incomplete, tokenizer.Comment)):
        return
    
    if text.endswith("\\"):
        if isinstance(tokenizer.parser(), tokenizer.MarkupParser):
            if tokenizer.parser().token == "\\markuplines":
                return ly.words.markupcommands + ly.words.markuplistcommands
            else:
                return ly.words.markupcommands
        commands = (ly.words.keywords + ly.words.keywords_completion
            + ly.words.musiccommands + ly.words.musiccommands_completion
            + lilyPondVersion())
        if tokenizer.parser().token == "\\context":
            return commands + ly.words.contexts
        else:
            return commands

    if isinstance(tokenizer.parser(), tokenizer.SchemeParser):
        # is the last token the scheme-introducing '#' ?
        if token is tokenizer.parser().token:
            return ('UP', 'DOWN', 'CENTER', 'LEFT', 'RIGHT')
        else:
            if text.endswith("#("):
                if tokenizer.parser(-2).token == "\\paper":
                    return ('set-paper-size',)
            elif text.endswith("#:"):
                return ly.words.markupcommands
            elif text.endswith("#(set-accidental-style '"):
                return ly.words.accidentalstyles
            return ly.words.schemefuncs
        
    if col == 0 or text[-1] in " \t":
        # all kinds of variables only at start of line or after whitespace
        # the VarCompletions model can add ' = ' after them
        if tokenizer.parser().token == "\\header":
            return VarCompletions(model, ly.words.headervars)
        if tokenizer.parser().token == "\\paper":    
            return VarCompletions(model, ly.words.papervars)
        if tokenizer.parser().token == "\\layout":
            return VarCompletions(model, ly.words.layoutvars)
        if tokenizer.parser().token in ("\\context", "\\with"):
            return VarCompletions(model, ly.words.contextproperties)
    
    if not text.strip():
         # only on an empty line: show the expansions
         return ExpansionCompletions(model)


# load some (cached) data
def musicglyph_names():
    font = ly.version.LilyPondInstance(lilyPondCommand()).fontInfo("emmentaler-20")
    if font:
        return tuple(font.glyphs())
    return ()

def lilyPondVersion():
    ver = frescobaldi_app.version.defaultVersion()
    return ('version "{0}"'.format(ver),) if ver else ()

