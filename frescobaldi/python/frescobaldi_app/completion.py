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
LilyPond auto completion
"""

from PyQt4.QtCore import QModelIndex, QVariant, Qt

from PyKDE4.ktexteditor import KTextEditor



class CompletionModel(KTextEditor.CodeCompletionModel):
    def __init__(self, parent):
        KTextEditor.CodeCompletionModel.__init__(self, parent)
        #self.setHasGroups(False)
        
        #FIXME, temp
        self.matches = ['aaaaaaaaaaaaaaa','abbbbbbbbbbbbbbbb','acccccccccccccccc']
        
    def data(self, index, role):
        if index.column() != KTextEditor.CodeCompletionModel.Name:
            return QVariant()
        if role == Qt.DisplayRole:
            return QVariant(self.matches[index.row()])
        elif role == KTextEditor.CodeCompletionModel.CompletionRole:
            return QVariant(
                KTextEditor.CodeCompletionModel.FirstProperty |
                KTextEditor.CodeCompletionModel.Public |
                KTextEditor.CodeCompletionModel.LastProperty )
        elif role == KTextEditor.CodeCompletionModel.ScopeIndex:
            return QVariant(0)
        elif role == KTextEditor.CodeCompletionModel.MatchQuality:
            return QVariant(10)
        elif role == KTextEditor.CodeCompletionModel.HighlightingMethod:
            return QVariant(QVariant.Invalid)
        elif role == KTextEditor.CodeCompletionModel.InheritanceDepth:
            return QVariant(0)
        else:
            return QVariant()
            
    def rowCount(self, parent):
        if parent.isValid():
            return 0 # Do not make the model look hierarchical
        else:
            return len(self.matches)
            
    def completionInvoked(self, view, word, invocationType):
        pass
    
    def index(self, row, column, parent):
        if (row < 0 or row >= len(self.matches) or
            column < 0 or column >= KTextEditor.CodeCompletionModel.ColumnCount or
            parent.isValid()):
            return QModelIndex()
        return self.createIndex(row, column, 0)

