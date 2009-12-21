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

from __future__ import unicode_literals

"""
Basic LilyPond syntax highlighter for QTextEdit.
"""

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QBrush, QFont, QTextCharFormat, QSyntaxHighlighter

import ly.tokenize, ly.words

_keywords = (
    ly.words.keywords + ly.words.musiccommands + ly.words.markupcommands +
    ly.words.markuplistcommands + ly.words.modes)

def formats():
    command = QTextCharFormat()
    command.setForeground(QBrush(Qt.darkBlue))
    
    keyword = QTextCharFormat(command)
    keyword.setFontWeight(QFont.Bold)

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
    
    scheme = QTextCharFormat()
    scheme.setForeground(QBrush(Qt.darkGreen))
    
    return locals()
    

class LilyPondHighlighter(QSyntaxHighlighter):
    
    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)
        self.formats = formats()
        self.state = []

    def highlightBlock(self, text):
        tokenizer = ly.tokenize.Tokenizer()
        previous = self.previousBlockState()
        if 0 <= previous < len(self.state):
            tokenizer.thaw(self.state[previous])
        for token in tokenizer.tokens(text):
            if isinstance(token, tokenizer.Command):
                format = token[1:] in _keywords and 'keyword' or 'command'
            elif isinstance(token, tokenizer.String):
                format = 'string'
            elif token in ('{', '}', '<<', '>>', '#{', '#}', '<', '>'):
                format = 'delimiter'
            elif isinstance(token, tokenizer.Comment):
                format = 'comment'
            elif isinstance(token, tokenizer.SchemeToken):
                format = 'scheme'
            else:
                continue
            self.setFormat(token.pos, len(token), self.formats[format])
        state = tokenizer.freeze()
        try:
            self.setCurrentBlockState(self.state.index(state))
        except ValueError:
            self.setCurrentBlockState(len(self.state))
            self.state.append(state)

