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
class Parsed(unicode):
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

class SchemeItem(Parsed):
    """
    A piece of Scheme input. If level in state is zero, terminates the
    (Scheme) state after this string.
    """
    def __init__(self, matchObj, state):
        if state[-1].level == 0:
            state.pop()

# real types of lilypond input
class Unparsed(unicode):
    """
    Represents an unparsed piece of LilyPond text.
    Needs to be given a value and a position (where the string was found)
    """
    def __new__(cls, value, pos):
        obj = unicode.__new__(cls, value)
        obj.pos = pos
        return obj

class Command(Parsed):
    rx = r"\\[A-Za-z]+(-[A-Za-z]+)*"

class String(Parsed):
    rx = r'"(\\[\\"]|[^"])*"'

class Comment(Parsed):
    rx = r'%{.*?%}|%[^\n]*'

class Word(Parsed):
    rx = r"[^\W\d]+"

class Space(Parsed):
    rx = r"\s+"

class OpenDelimiter(Parsed):
    rx = r"<<|\{"
    
class CloseDelimiter(Parsed):
    rx = r">>|\}"

class OpenChord(Parsed):
    rx = "<"
    
class CloseChord(Parsed):
    rx = ">"

class Articulation(Parsed):
    rx = "[-_^][_.>|+^-]"
    
class Dynamic(Parsed):
    rx = r"\[<>!]"

class VoiceSeparator(Parsed):
    rx = r"\\"

class Digit(Parsed):
    rx = r"\d+"
    
class EndSchemeLily(Parsed):
    rx = "#}"
    def __init__(self, matchObj, state):
        if len(state) > 1:
            state.pop()
            
class Scheme(Parsed):
    rx = "#"
    def __init__(self, matchObj, state):
        state.append(SchemeState())

class SchemeOpenParenthesis(Parsed):
    rx = r"\("
    def __init__(self, matchObj, state):
        state[-1].level += 1

class SchemeCloseParenthesis(Parsed):
    rx = r"\)"
    def __init__(self, matchObj, state):
        if state[-1].level > 1:
            state[-1].level -= 1
        else:
            state.pop()

class SchemeString(String, SchemeItem):
    pass

class SchemeSpace(Space):
    pass

class SchemeChar(SchemeItem):
    rx = r'#\\([a-z]+|.)'

class SchemeLily(Parsed):
    rx = "#{"
    def __init__(self, matchObj, state):
        state.append(LilyState())
        
class SchemeWord(SchemeItem):
    rx = r'[^()"{}\s]+'

#States:
class State(object):
    def __init__(self):
        self.level = 0

class LilyState(State):
    rx = make_re(
        Command,
        String,
        Comment,
        Articulation,
        Dynamic,
        VoiceSeparator,
        OpenDelimiter, CloseDelimiter,
        OpenChord, CloseChord,
        EndSchemeLily,
        Scheme,
        Digit,
        Word,
        Space,
        )

class SchemeState(State):
    rx = make_re(
        SchemeString,
        SchemeChar,
        SchemeLily,
        SchemeWord,
        SchemeOpenParenthesis, SchemeCloseParenthesis,
        SchemeSpace,
        )


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
                yield Unparsed(text[pos:], pos)
            return
        else:
            if pos < m.start():
                yield Unparsed(text[pos:m.start()], pos)
            yield eval(m.lastgroup)(m, state)
            pos = m.end()

