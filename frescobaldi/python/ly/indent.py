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
Indent LilyPond input.

Recoqnizes common LilyPond mode and Scheme mode.

This module is not dependent on any other module,
besides the Python standard re module.

"""

import re

lily_re = (
    r"(?P<indent>\{|<<?)"
    r"|(?P<dedent>>>?|\})"
    r'|(?P<string>"(\\[\\"]|[^"])*")'
    r"|(?P<newline>\n[^\S\n]*)"
    r"|(?P<space>[^\S\n]+)"
    r"|(?P<scheme>#)"
    r"|(?P<longcomment>%%[^\n]*)"
    r"|(?P<blockcomment>%{.*?%})"
    r"|(?P<comment>%[^\n]*)"
    )

lily = re.compile(lily_re, re.M)

scheme_re = (
    r"(?P<indent>\()"
    r"|(?P<dedent>\))"
    r'|(?P<string>"(\\[\\"]|[^"])*")'
    r"|(?P<newline>\n[^\S\n]*)"
    r"|(?P<space>[^\S\n]+)"
    r"|(?P<lilypond>#\{)"
    r"|(?P<longcomment>;;[^\n]*)"
    r"|(?P<blockcomment>#!.*?!#)"
    r"|(?P<comment>;[^\n]*)"
    )

scheme = re.compile(scheme_re, re.M)

schemelily_re = lily_re + r"|(?P<backtoscheme>#\})"

schemelily = re.compile(schemelily_re, re.M)

    
def indent(text,
        start = None,
        indentwidth = 2,
        tabwidth = 8,
        usetabs = None,
        ):
    """
    Properly indents the LilyPond input in text.
    
    If start is an integer value, use that value as the indentwidth to start
    with, disregarding the current indent of the first line.
    If it is None, use the indent of the first line.
    
    indentwidth: how many positions to indent (default 2)
    tabwidth: width of a tab character
    usetabs: whether to use tab characters in the indent:
        - None = determine from document
        - True = use tabs for the parts of the indent that exceed the tab width
        = False = don't use tabs.
    """
    if start is None:
        start = len(re.match(r'[^\S\n]*', text).group().expandtabs(tabwidth))
    if usetabs is None:
        usetabs = '\t' in text
    if start:
        text = re.sub(r'^[^\S\n]*', '', text)
    
    mode = [lily]       # the mode to parse
    pos = 0             # position in text
    output = []         # list of output lines
    line = []           # list to build the output, per line
    indent = [start]    # stack with indent history
    curindent = -1      # current indent in count of spaces, -1 : not yet set
    
    
    m = mode[-1].search(text, pos)
    while m:
        if pos < m.start():
            line.append(text[pos:m.start()])
        if curindent == -1:
            if m.lastgroup == 'longcomment':
                curindent = 0
            elif m.lastgroup not in ('dedent', 'space'):
                curindent = indent[-1]
        if m.lastgroup == 'newline':
            output.append( (curindent, ''.join(line)) )
            line = []
            curindent = -1
        else:
            line.append(m.group())
            if m.lastgroup == 'indent':
                indent.append(indent[-1] + indentwidth)
            elif m.lastgroup == 'dedent' and len(indent) > 1:
                indent.pop()
        
        pos = m.end()
        m = mode[-1].search(text, pos)
    if pos < len(text):
        line.append(text[pos:])
    if line:
        if curindent == -1:
            curindent = indent[-1]
        output.append( (curindent, ''.join(line)) )
    else:
        output.append( (start, '') )
    # format the output:
    if usetabs:
        result = '\n'.join(
            ('\t' * int(indent / tabwidth) + ' ' * (indent % tabwidth)) + line
            for indent, line in output)
    else:
        result = '\n'.join(
            (' ' * indent) + line
            for indent, line in output)
    
    return result

    