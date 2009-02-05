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

def make_re(classes):
    """
    Expects a list of classes representing LilyPond input atoms. Returns
    compiled regular expression with named groups, to match input of the listed
    types. Reads the rx class attribute of the given classes.
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

class Item(Parsed):
    """
    Represents a token that decreases the argument count of its calling
    command.
    """
    def __init__(self, matchObj, state):
        state.endArgument()

class Increaser(Parsed):
    def __init__(self, matchObj, state):
        state.inc()
        
class Decreaser(Parsed):
    def __init__(self, matchObj, state):
        state.dec()

class Leaver(Parsed):
    def __init__(self, matchObj, state):
        state.leave()


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

class Command(Item):
    rx = r"\\[A-Za-z]+(-[A-Za-z]+)*"

class String(Item):
    rx = r'"(\\[\\"]|[^"])*"'

class PitchWord(Item):
    rx = r'[a-z]+'
    
class Scheme(Parsed):
    rx = "#"
    def __init__(self, matchObj, state):
        state.enter(SchemeParser)

class Comment(Parsed):
    rx = r'%{.*?%}|%[^\n]*'

class Space(Parsed):
    rx = r"\s+"

class Markup(Item):
    rx = r"\\markup\b"
    def __init__(self, matchObj, state):
        state.enter(MarkupParser)

class OpenDelimiter(Increaser):
    rx = r"<<|\{"
    
class CloseDelimiter(Decreaser):
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
    
class EndSchemeLily(Leaver):
    rx = "#\}"

class SchemeOpenParenthesis(Increaser):
    rx = r"\("

class SchemeCloseParenthesis(Decreaser):
    rx = r"\)"

class SchemeChar(Item):
    rx = r'#\\([a-z]+|.)'

class SchemeWord(Item):
    rx = r'[^()"{}\s]+'

class SchemeComment(Parsed):
    rx = r";[^\n]*|#!.*?!#"
    
class SchemeLily(Parsed):
    rx = "#\{"
    def __init__(self, matchObj, state):
        state.enter(ToplevelParser)


class OpenBracket(Increaser):
    rx = r"\{"

class CloseBracket(Decreaser):
    rx = r"\}"

class MarkupScore(Command):
    rx = r"\\score\b"
    def __init__(self, matchObj, state):
        state.enter(ToplevelParser, 1)
        
class MarkupCommand(Command):
    def __init__(self, matchObj, state):
        if matchObj.group() == "\\combine":
            argcount = 2
        else:
            argcount = 1
        state.enter(MarkupParser, argcount)

class MarkupWord(Item):
    rx = r'[^{}"\\\s]+'

class LyricMode(Command):
    rx = r'\\(lyricmode|((old)?add)?lyrics|lyricsto)\b'
    def __init__(self, matchObj, state):
        if matchObj.group() == "\\lyricsto":
            argcount = 2
        else:
            argcount = 1
        state.enter(LyricParser)
        
class LyricWord(Item):
    rx = r'[^\W\d]+'
    
class Section(Command):
    """Introduce a section with no music, like \\layout, etc."""
    rx = r'\\(with|layout|midi|paper|header)\b'
    def __init__(self, matchObj, state):
        state.enter(SectionParser)
        

class State(object):
    """
    Manages state for the parsers.
    """
    def __init__(self, parserClass = None):
        if parserClass is None:
            parserClass = ToplevelParser
        self.state = [parserClass()]

    def parser(self):
        return self.state[-1]
        
    def parse(self, text, pos):
        return self.state[-1].rx.search(text, pos)
        
    def enter(self, parserClass, argcount = None):
        self.state.append(parserClass())
        if argcount is not None:
            self.state[-1].argcount = argcount

    def leave(self):
        if len(self.state) > 1:
            self.state.pop()
        
    def endArgument(self):
        while len(self.state) > 1 and self.state[-1].level == 0:
            if self.state[-1].argcount > 1:
                self.state[-1].argcount -= 1
                return
            elif self.state[-1].argcount == 0:
                return
            self.state.pop()
            
    def inc(self):
        self.state[-1].level += 1
        
    def dec(self):
        if self.state[-1].level > 0:
            self.state[-1].level -= 1
            self.endArgument()
            

class Parser(object):
    argcount = 0
    level = 0


# tuple with base stuff to parse in LilyPond input
_lilybase = (
    Comment,
    String,
    EndSchemeLily,
    Scheme,
    Section,
    LyricMode,
    Markup,
    Command,
    Space,
    )


class ToplevelParser(Parser):
    rx = make_re((
        OpenDelimiter, CloseDelimiter,
        PitchWord,
    ) + _lilybase)


class SchemeParser(Parser):
    argcount = 1
    rx = make_re((
        String,
        SchemeChar,
        SchemeComment,
        SchemeOpenParenthesis, SchemeCloseParenthesis,
        SchemeLily,
        SchemeWord,
        Space,
    ))
            

class MarkupParser(Parser):
    argcount = 1
    rx = make_re((
        MarkupScore,
        MarkupCommand,
        OpenBracket, CloseBracket,
        MarkupWord,
    ) + _lilybase)
    

class LyricParser(Parser):
    argcount = 1
    rx = make_re((
        OpenBracket, CloseBracket,
        LyricWord,
    ) + _lilybase)


class SectionParser(Parser):
    argcount = 1
    rx = make_re((
        OpenBracket, CloseBracket,
    ) + _lilybase)


def tokenize(text, pos = 0, state = None):
    """
    Iterate over the LilyPond tokens in the string.
    All returned tokens are a subclass of unicode.
    When they are reassembled, the original string is restored (i.e. no
    data is lost).
    The tokenizer does its best to parse LilyPond input and return
    meaningful strings. It recognizes being in a Scheme context, and also
    "LilyPond in Scheme" (the #{ and #} constructs).
    """
    if state is None:
        state = State()
    
    while True:
        m = state.parse(text, pos)
        if not m:
            if pos < len(text):
                yield Unparsed(text[pos:], pos)
            return
        else:
            if pos < m.start():
                yield Unparsed(text[pos:m.start()], pos)
            yield eval(m.lastgroup)(m, state)
            pos = m.end()

