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
    r"|(?P<blockcomment>%\{.*?%\})"
    r"|(?P<longcomment>%%[^\n]*)"
    r"|(?P<comment>%[^\n]*)"
    )

class lily:
    rx = re.compile(lily_re, re.S)

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

class scheme:
    rx = re.compile(scheme_re, re.S)
    depth = 0

schemelily_re = lily_re + r"|(?P<backtoscheme>#\})"

class schemelily:
    rx = re.compile(schemelily_re, re.S)

    
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
    
    mode = [lily()]       # the mode to parse
    pos = 0             # position in text
    output = []         # list of output lines
    line = []           # list to build the output, per line
    indent = [start]    # stack with indent history
    curindent = -1      # current indent in count of spaces, -1 : not yet set
    
    if usetabs:
        makeindent = lambda i: '\t' * int(i / tabwidth) + ' ' * (i % tabwidth)
    else:
        makeindent = lambda i: ' ' * i
    
    m = mode[-1].rx.search(text, pos)
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
            token = m.group()
            if m.lastgroup == 'indent':
                indent.append(indent[-1] + indentwidth)
            elif m.lastgroup == 'dedent' and len(indent) > 1:
                indent.pop()
            elif m.lastgroup == 'blockcomment' and '\n' in token:
                # keep the indent inside block comments.
                bcindent = curindent - min(len(n.group(1).expandtabs())
                    for n in re.finditer(r'\n([^\S\n]*)', token))
                fixindent = lambda match: ('\n' +
                    makeindent(len(match.group(1).expandtabs()) + bcindent))
                token = re.sub(r'\n([^\S\n]*)', fixindent, token)
                
            line.append(token)
            
        pos = m.end()
        m = mode[-1].rx.search(text, pos)
    if pos < len(text):
        line.append(text[pos:])
    if line:
        if curindent == -1:
            curindent = indent[-1]
        output.append( (curindent, ''.join(line)) )
    else:
        output.append( (start, '') )
    # return formatted output
    return '\n'.join(makeindent(indent) + line for indent, line in output)

    