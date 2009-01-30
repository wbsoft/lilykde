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

""" Functions to parse and tokenize LilyPond text """

import re

def make_re(*classes):
    """
    Expects an argument list of classes representing LilyPond
    input atoms. Returns compiled regular expression with named groups,
    to match input of the listed types. Reads the rx class attribute of the
    given classes.
    """
    return re.compile(
        "|".join("(?P<%s>%s)" % (cls.__name__, cls.rx) for cls in classes),
        re.DOTALL)

# Classes that represent pieces of lilypond text:
# base classes:
class parsed(unicode):
    """
    Represents a parsed piece of LilyPond text, the subclass determines
    the type.
    The matchObj delivers the string and the position.
    The state can be manipulated on instantiation.
    """
    def __new__(cls, matchObj, state):
        obj = unicode.__new__(cls, matchObj.group())
        obj.pos = matchObj.pos
        return obj

class schemeitem(parsed):
    """
    A piece of Scheme input. If level in state is zero, terminates the
    (Scheme) state after this string.
    """
    def __init__(self, matchObj, state):
        if state[-1].level == 0:
            state.pop()

# real types of lilypond input
class unparsed(unicode):
    """
    Represents an unparsed piece of LilyPond text.
    Needs to be given a value and a position (where the string was found)
    """
    def __new__(cls, value, pos):
        obj = unicode.__new__(cls, value)
        obj.pos = pos
        return obj

class command(parsed):
    rx = r"\\[A-Za-z]+(-[A-Za-z]+)*"

class string(parsed):
    rx = r'"(\\[\\"]|[^"])*"'

class comment(parsed):
    rx = r'%{.*?%}|%[^\n]*'

class word(parsed):
    rx = r"[^\W\d]+"

class space(parsed):
    rx = r"\s+"

class opendelimiter(parsed):
    rx = r"<<|\{"
    
class closedelimiter(parsed):
    rx = r">>|\}"

class openchord(parsed):
    rx = "<"
    
class closechord(parsed):
    rx = ">"

class articulation(parsed):
    rx = "[-_^][_.>|+^-]"
    
class dynamic(parsed):
    rx = r"\[<>!]"

class voiceseparator(parsed):
    rx = r"\\"

class digit(parsed):
    rx = r"\d+"
    
class endschemelily(parsed):
    rx = "#}"
    def __init__(self, matchObj, state):
        if len(state) > 1:
            state.pop()
            
class scheme(parsed):
    rx = "#"
    def __init__(self, matchObj, state):
        state.append(SchemeState())

class schemeopenparenthesis(parsed):
    rx = r"\("
    def __init__(self, matchObj, state):
        state[-1].level += 1

class schemecloseparenthesis(parsed):
    rx = r"\)"
    def __init__(self, matchObj, state):
        if state[-1].level > 1:
            state[-1].level -= 1
        else:
            state.pop()

class schemestring(string, schemeitem):
    pass

class schemespace(space, schemeitem):
    pass

class schemechar(schemeitem):
    rx = r'#\\([a-z]+|.)'

class schemelily(parsed):
    rx = "#{"
    def __init__(self, matchObj, state):
        state.append(LilyState())
        
class schemeword(schemeitem):
    rx = r'[^()"{}\s]+'

#States:
class LilyState:
    rx = make_re(
        command,
        string,
        comment,
        articulation,
        dynamic,
        voiceseparator,
        opendelimiter, closedelimiter,
        openchord, closechord,
        endschemelily,
        scheme,
        digit,
        word,
        space,
        )

class SchemeState:
    rx = make_re(
        schemestring,
        schemechar,
        schemelily,
        schemeword,
        schemeopenparenthesis, schemecloseparenthesis,
        schemespace,
        )
    def __init__(self):
        self.level = 0


def tokenize(text, pos = 0, state = None):
    """
    Iterate over the LilyPond tokens in the string.
    All returned tokens are a subclass of unicode.
    When they are reassembled, the original string is restored (i.e. no
    data is lost).
    The tokenizer does its best to parse LilyPond input and return
    meaningful strings. It recognizes being in a Scheme context, and also
    "LilyPond in Scheme (the #{ and #} constructs).
    """
    if state is None:
        state = [LilyState()]
    
    while True:
        m = state[-1].rx.search(text, pos)
        if not m:
            if pos < len(text):
                yield unparsed(text[pos:], pos)
            return
        else:
            if pos < m.start():
                yield unparsed(text[pos:m.start()], pos)
            yield eval(m.lastgroup)(m, state)
            pos = m.end()

