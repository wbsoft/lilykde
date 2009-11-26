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
Very basic LilyPond syntax highlighter for QTextEdit.
"""

import sip

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QBrush, QFont, QTextBlockUserData, QTextCharFormat, QSyntaxHighlighter

import ly.tokenize

def formats():
    command = QTextCharFormat()
    command.setForeground(QBrush(Qt.darkBlue))

    string = QTextCharFormat()
    string.setForeground(QBrush(Qt.darkRed))

    comment = QTextCharFormat()
    comment.setFontItalic(True)
    comment.setForeground(QBrush(Qt.darkGray))
    
    delimiter = QTextCharFormat()
    delimiter.setFontWeight(QFont.Bold)

    special = QTextCharFormat()
    special.setFontWeight(QFont.Bold)
    special.setForeground(QBrush(Qt.red))
    
    return locals()
    

class LilyPondHighlighter(QSyntaxHighlighter):
    
    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)
        self.formats = formats()
    
    def state(self, block):
        """ Returns a State instance for block, if any. """
        if block.isValid():
            state = block.userData()
            if isinstance(state, State):
                return state
    
    def highlightBlock(self, text):
        text = unicode(text)
        tokenizer = ly.tokenize.Tokenizer()
        pos = 0
        
        prev = self.state(self.currentBlock().previous())
        cur = self.state(self.currentBlock())
        if prev:
            tokenizer.thaw(prev.frozenState)
            if prev.incomplete:
                pos = tokenizer.endOfIncompleteToken(prev.incomplete, text)
                if issubclass(prev.incomplete, tokenizer.Comment):
                    format = 'comment'
                else:
                    format = 'string' # there are no other incomplete types
                if pos == -1:
                    # whole text
                    self.setFormat(0, len(text), self.formats[format])
                else:
                    self.setFormat(0, pos, self.formats[format])
        if pos != -1:
            token = None # in case this loop does not run at all
            for token in tokenizer.tokens(text, pos):
                setFormat = (lambda format:
                    self.setFormat(token.pos, len(token), self.formats[format]))
                if isinstance(token, tokenizer.Command):
                    setFormat('command')
                elif isinstance(token, tokenizer.String):
                    setFormat('string')
                elif token in ('{', '}', '<<', '>>', '#{', '#}', '<', '>'):
                    setFormat('delimiter')
                elif isinstance(token, tokenizer.Comment):
                    setFormat('comment')
            state = State(tokenizer.freeze(), token)
        else:
            state = prev.copy()
        if not state.matches(cur):
            self.setCurrentBlockUserData(state)
            # avoid delete by python
            #sip.transferto(state, None)
            # trigger redraw
            self.setCurrentBlockState(1 - abs(self.currentBlockState()))


class State(QTextBlockUserData):
    def __init__(self, frozenState, lastToken = None):
        QTextBlockUserData.__init__(self)
        self.frozenState = frozenState
        if isinstance(lastToken, ly.tokenize.Tokenizer.Incomplete):
            self.incomplete = lastToken.__class__
        else:
            self.incomplete = None

    def copy(self):
        copy = State(self.frozenState)
        copy.incomplete = self.incomplete
        return copy
        
    def matches(self, other):
        if not isinstance(other, State):
            return False
        if self.frozenState != other.frozenState:
            return False
        return self.incomplete is other.incomplete


