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

import os, re

from PyKDE4.kdecore import KGlobal
from PyKDE4.ktexteditor import KTextEditor

import ly, ly.font, ly.tokenize, ly.version, ly.words

def lilypondCommand():
    return unicode(
        KGlobal.config().group("commands").readEntry("lilypond", "lilypond"))
        
@ly.lazy
def musicglyph_names():
    datadir = ly.version.datadir(lilypondCommand())
    if datadir:
        font = ly.font.emmentaler20(datadir)
        if font:
            return tuple(font.glyphs())
    return ()

@ly.lazy
def lilypondVersion():
    ver = ly.version.LilyPondVersion(lilypondCommand()).versionString
    return ver and ('version "%s"' % ver,) or ()
    
def findMatches(view, word, invocationType):
    """
    Return the list of matches that are useful in the current context.
    """
    doc = view.document()
    line, col = word.start().line(), word.start().column()
    textLine = unicode(doc.line(line))
    textCur = textLine[:col]
    
    # determine what the user tries to type
    # very specific situations:
    if re.search(r'\\(consists|remove)\s*"?$', textCur):
        return ly.words.engravers
    if re.search(r'\bmidiInstrument\s*=\s*#?"$', textCur):
        return ly.words.midi_instruments
    if re.search(r'\\musicglyph\s*#"$', textCur):
        return musicglyph_names()
    if re.search(r'\\key\s+[a-z]+\s*\\$', textCur):
        return ly.words.modes
    if re.search(r'\\(un)?set\b\s*$', textCur):
        return ly.words.contexts + ly.words.contextproperties
    if ly.words.set_context_re.search(textCur):
        return ly.words.contextproperties
    if ly.words.context_re.search(textCur):
        return ly.words.grobs
    if textCur.endswith("#'"):
        m = ly.words.grob_re.search(textCur[:-2])
        if m:
            return ly.words.schemeprops(m.group(1))
        if re.search(r"\\tweak\b\s*$", textCur[:-2]):
            return ly.words.schemeprops()
    if re.search(r"\\(override|revert)\s+$", textCur):
        return ly.words.contexts + ly.words.grobs
    if re.search(r'\\repeat\s+"?$', textCur):
        return ly.words.repeat_types
    if re.search(r'\\clef\s*"$', textCur):
        return ly.words.clefs
    if re.search(r"\\clef\s+$", textCur):
        return ly.words.clefs_plain
    
    # parse to get current context
    fragment = unicode(doc.text(KTextEditor.Range(
        KTextEditor.Cursor(0, 0), word.start())))
    state = ly.tokenize.State()
    token = None # in case the next loop does not run at all
    for token in ly.tokenize.tokenize(fragment, state=state):
        pass
    # don't bother if we are inside a string or comment
    if isinstance(token, (ly.tokenize.Incomplete, ly.tokenize.Comment)):
        return
    
    if textCur.endswith("\\"):
        if isinstance(state.parser(), ly.tokenize.MarkupParser):
            return ly.words.markupcommands
        elif state.parser().token == "\\context":
            return ly.words.contexts + ly.words.keywords + ly.words.musiccommands + lilypondVersion()
        else:
            return ly.words.keywords + ly.words.musiccommands + lilypondVersion()

    if isinstance(state.parser(), ly.tokenize.SchemeParser):
        # is the last token the scheme-introducing '#' ?
        if token is state.parser().token:
            return ('UP', 'DOWN', 'CENTER', 'LEFT', 'RIGHT')
        else:
            if textCur.endswith("#("):
                if state.parser(-2).token == "\\paper":
                    return ('set-paper-size',)
            elif textCur.endswith("#:"):
                return ly.words.markupcommands
            return ly.words.schemefuncs
        
    if state.parser().token == "\\header":
        return ly.words.headervars
    if state.parser().token == "\\paper":    
        return ly.words.papervars
    if state.parser().token == "\\layout":
        return ly.words.layoutvars
    if state.parser().token in ("\\context", "\\with"):
        return ly.words.contextproperties
    
        
        