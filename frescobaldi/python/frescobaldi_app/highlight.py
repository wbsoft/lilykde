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
Basic LilyPond syntax highlighter for QTextEdit.
"""

from PyQt4.QtCore import QObject, Qt, SIGNAL
from PyQt4.QtGui import QBrush, QFont, QTextCharFormat, QSyntaxHighlighter

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
        self.state = {}
        self.counter = 0
        QObject.connect(document, SIGNAL("blockCountChanged(int)"),
            self.slotBlockCountChanged)
    
    def slotBlockCountChanged(self, count):
        """ Delete state for removed lines. """
        states = set(self.document().findBlockByNumber(b).userState()
            for b in range(count))
        for key in set(self.state.keys()) - states:
            del self.state[key]
        
    def highlightBlock(self, text):
        text = unicode(text)
        tokenizer = ly.tokenize.Tokenizer()
        previous = self.state.get(self.previousBlockState())
        if previous:
            tokenizer.thaw(previous)
        for token in tokenizer.tokens(text):
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
        state = tokenizer.freeze()
        current = self.state.get(self.currentBlockState())
        if state is not current:
            if current:
                del self.state[self.currentBlockState()]
            self.state[self.counter] = state
            self.setCurrentBlockState(self.counter)
            self.counter += 1


