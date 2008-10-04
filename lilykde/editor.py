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

