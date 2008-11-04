# This file is part of LilyKDE, http://lilykde.googlecode.com/
#
# Copyright (c) 2008  Wilbert Berendsen
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Interface with Kate (via Pate), easily exchangable with interface code
for a different editor.

Mainly code dealing with the editor buffer, selection, etc.
"""

import kate

from lilykde.widgets import sorry

# Translate the messages
from lilykde.i18n import _

def text():
    """The document text."""
    return kate.document().text

def setText(text):
    """Set the document text."""
    # Just setting d.text does work, but triggers a bug in the
    # Katepart syntax highlighting: the first part of the document
    # looses its highlighting when a user undoes the conversion
    # with Ctrl+Z
    d = kate.document()
    d.editingSequence.begin()
    for i in range(d.numberOfLines):
        d.removeLine(0)
    kate.document().text = text
    d.editingSequence.end()

def insertLine(lineNum, text):
    """Insert text at the given line number."""
    kate.document().insertLine(lineNum, text)

def append(text):
    """Append text to document (starting in a new line)."""
    d = kate.document()
    d.insertLine(d.numberOfLines, text)

def clear():
    """Clear the current editor buffer."""
    # kate.document().clear() is broken in Pate 0.5.1
    d = kate.document()
    for i in range(d.numberOfLines):
        d.removeLine(0)

def currentLine():
    """The text on the current line."""
    return kate.view().currentLine

def line(lineNum):
    """The text on the given line number."""
    return kate.document().line(lineNum)

def search(text, start, caseSensitive=True, searchBackwards=False):
    """
    Search through the document.
    Returns match, (line, column), length
    """
    return kate.document().search(text, start, caseSensitive, searchBackwards)

def fragment(start, end):
    """Returns the text from start (line, col) to end (line, col)..."""
    return kate.document().fragment(start, end)

def pos():
    """The cursor position."""
    return kate.view().cursor.position

def setPos(linepos, col = None):
    """Set the cursor position to line, col or (line, col)."""
    if col is None:
        kate.view().cursor.position = linepos
    else:
        kate.view().cursor.position = (linepos, col)

def focus():
    """Give keyboard focus to the text editor widget."""
    kate.mainWidget().setFocus()

def topLevelWidget():
    """The toplevel window of the editing widget."""
    return kate.mainWidget().topLevelWidget()

def mainWidget():
    """The main text editing widget."""
    return kate.mainWidget()

def editBegin():
    """Start an editing sequence."""
    kate.document().editingSequence.begin()

def editEnd():
    """End an editing sequence."""
    kate.document().editingSequence.end()

def insertText(text):
    kate.view().insertText(text)

def selectedText():
    """
    Returns the currenty selected text or an empty string.
    """
    if kate.view().selection.exists:
        return kate.view().selection.text
    else:
        return ''

def hasSelection():
    """True if there is a selection"""
    return kate.view().selection.exists

def replaceSelectionWith(text, keepSelection = False):
    """
    Replaces the selection in the current view with text,
    and reselects the newly inserted text if keepSelection == True
    """
    d, v, s = kate.document(), kate.view(), kate.view().selection
    if s.exists:
        line, col = s.region[0]
    else:
        line, col = v.cursor.position
    lines = text.split('\n')
    endline, endcol = line + len(lines) - 1, len(lines[-1])
    if len(lines) < 2:
        endcol += col
    d.editingSequence.begin()
    if s.exists:
        s.removeSelectedText()
    v.insertText(text)
    d.editingSequence.end()
    if keepSelection:
        s.region = ((line, col), (endline, endcol))

def runOnSelection(func):
    """
    A decorator that makes a function run on the selection,
    and replaces the selection with its output if not None
    """
    def selFunc():
        text = selectedText()
        if text:
            repl = func(text)
            if repl is not None:
                replaceSelectionWith(repl)
        else:
            sorry(_("Please select some text first."))
    return selFunc

