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


class Tokenizer(object):
    """
    This class defines an environment to parse LilyPond text input.
    
    There are two types of nested classes (accessible as class attributes, but
    also via a Tokenizer instance):
    
    - Subclasses of Parsed (or Unparsed): tokens of LilyPond input.
    - Subclasses of Parser: container with regex to parse LilyPond input.
    """
    def __init__(self, parserClass = None):
        self.reset(parserClass)
        
    def reset(self, parserClass = None):
        """
        Reset the tokenizer instance (forget state), so that it can be used
        again.
        """
        if parserClass is None:
            parserClass = self.ToplevelParser
        self.state = [parserClass()]

    def parser(self, depth = -1):
        """ Return the current (or given) parser instance. """
        return self.state[depth]
        
    def enter(self, parserClass, token, argcount = None):
        """ (Internal) Enter a new parser. """
        self.state.append(parserClass())
        self.state[-1].token = token
        if argcount is not None:
            self.state[-1].argcount = argcount

    def leave(self):
        """ (Internal) Leave the current parser and pop back to the previous. """
        if len(self.state) > 1:
            self.state.pop()
        
    def endArgument(self):
        """
        (Internal) End an argument. Decrease argcount and leave the parser
        if it would reach 0.
        """
        while len(self.state) > 1 and self.state[-1].level == 0:
            if self.state[-1].argcount > 1:
                self.state[-1].argcount -= 1
                return
            elif self.state[-1].argcount == 0:
                return
            self.state.pop()
            
    def inc(self):
        """
        (Internal) Up the level of the current parser. Indicates nesting
        while staying in the same parser.
        """
        self.state[-1].level += 1
        
    def dec(self):
        """
        (Internal) Down the level of the current parser. If it has reached zero,
        leave the current parser. Otherwise decrease argcount and leave if that
        would reach zero.
        """
        while self.state[-1].level == 0 and len(self.state) > 1:
            self.state.pop()
        if self.state[-1].level > 0:
            self.state[-1].level -= 1
            self.endArgument()
            
    def depth(self):
        """
        Return a two-tuple representing the depth of the current state.
        This is useful to quickly check when a part of LilyPond input ends.
        """
        return len(self.state), self.state[-1].level

    def tokens(self, text, pos = 0):
        """
        Iterate over the LilyPond tokens in the string.
        All returned tokens are a subclass of unicode.
        When they are reassembled, the original string is restored (i.e. no
        data is lost).
        The tokenizer does its best to parse LilyPond input and return
        meaningful strings. It recognizes being in a Scheme context, and also
        "LilyPond in Scheme" (the #{ and #} constructs).
        """
        while True:
            m = self.state[-1].rx.search(text, pos)
            if not m:
                if pos < len(text):
                    yield self.Unparsed(text[pos:], pos)
                return
            else:
                if pos < m.start():
                    yield self.Unparsed(text[pos:m.start()], pos)
                yield getattr(self, m.lastgroup)(m, self)
                pos = m.end()
    
    
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
        def __init__(self, matchObj, tokenizer):
            tokenizer.endArgument()

    class Incomplete(Item):
        """
        Represents an unfinished item, e.g. string or block comment.
        """
        pass

    class Increaser(Parsed):
        def __init__(self, matchObj, tokenizer):
            tokenizer.inc()
            
    class Decreaser(Parsed):
        def __init__(self, matchObj, tokenizer):
            tokenizer.dec()

    class Leaver(Parsed):
        def __init__(self, matchObj, tokenizer):
            tokenizer.leave()


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

    class IncompleteString(Incomplete):
        rx = r'"(\\[\\"]|[^"])*$'
        
    class PitchWord(Item):
        rx = r'[a-z]+'
        
    class Scheme(Parsed):
        rx = "#"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.SchemeParser, self)

    class Comment(Parsed):
        rx = r'%{.*?%}|%[^\n]*'

    class Space(Parsed):
        rx = r"\s+"

    class Markup(Command):
        rx = r"\\markup\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.MarkupParser, self)

    class MarkupLines(Command):
        rx = r"\\markuplines\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.MarkupParser, self)
    
    class Include(Command):
        rx = r"\\include\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.IncludeParser, self)
    
    class IncludeFile(String):
        pass
        
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
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.ToplevelParser, self)

    class OpenBracket(Increaser):
        rx = r"\{"

    class CloseBracket(Decreaser):
        rx = r"\}"

    class MarkupScore(Command):
        rx = r"\\score\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.ToplevelParser, self, 1)
            
    class MarkupCommand(Command):
        def __init__(self, matchObj, tokenizer):
            if matchObj.group() == "\\combine":
                argcount = 2
            else:
                argcount = 1
            tokenizer.enter(tokenizer.MarkupParser, self, argcount)

    class MarkupWord(Item):
        rx = r'[^{}"\\\s]+'

    class LyricMode(Command):
        rx = r'\\(lyricmode|((old)?add)?lyrics|lyricsto)\b'
        def __init__(self, matchObj, tokenizer):
            if matchObj.group() == "\\lyricsto":
                argcount = 2
            else:
                argcount = 1
            tokenizer.enter(tokenizer.LyricModeParser, self, argcount)
            
    class ChordMode(Command):
        rx = r'\\(chords|chordmode)\b'
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.ChordModeParser, self)

    class FigureMode(Command):
        rx = r'\\(figures|figuremode)\b'
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.FigureModeParser, self)

    class NoteMode(Command):
        rx = r'\\(notes|notemode)\b'
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.NoteModeParser, self)

    class LyricWord(Item):
        rx = r'[^\W\d]+'
        
    class Section(Command):
        """Introduce a section with no music, like \\layout, etc."""
        rx = r'\\(with|layout|midi|paper|header)\b'
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.SectionParser, self)

    class Context(Command):
        """ Introduce a \context section within layout, midi. """
        rx = r'\\context\b'
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.ContextParser, self)
            

    ### Parsers
    class Parser(object):
        argcount = 0
        level = 0
        token = None


    # tuple with base stuff to parse in LilyPond input
    _lilybase = (
        Comment,
        String,
        IncompleteString,
        EndSchemeLily,
        Scheme,
        Section,
        LyricMode, ChordMode, FigureMode, NoteMode,
        Markup,
        MarkupLines,
        Include,
        Command,
        Space,
        )


    class ToplevelParser(Parser):
        pass
    ToplevelParser.rx = make_re((
            OpenDelimiter, CloseDelimiter,
            PitchWord,
        ) + _lilybase)


    class SchemeParser(Parser):
        argcount = 1
    SchemeParser.rx = make_re((
            String,
            IncompleteString,
            SchemeChar,
            SchemeComment,
            SchemeOpenParenthesis, SchemeCloseParenthesis,
            SchemeLily,
            SchemeWord,
            Space,
        ))
                

    class MarkupParser(Parser):
        argcount = 1
    MarkupParser.rx = make_re((
            MarkupScore,
            MarkupCommand,
            OpenBracket, CloseBracket,
            MarkupWord,
        ) + _lilybase)
        

    class InputModeParser(Parser):
        """
        Abstract base class for input modes such as \lyricmode, \figuremode,
        \chordmode etc.
        """
        argcount = 1


    class LyricModeParser(InputModeParser):
        pass
    LyricModeParser.rx = make_re((
            OpenBracket, CloseBracket,
            LyricWord,
        ) + _lilybase)


    class ChordModeParser(ToplevelParser, InputModeParser):
        argcount = 1
        

    class FigureModeParser(ToplevelParser, InputModeParser):
        argcount = 1
        

    class NoteModeParser(ToplevelParser, InputModeParser):
        argcount = 1
        

    class SectionParser(Parser):
        argcount = 1
    SectionParser.rx = make_re((
            OpenBracket, CloseBracket,
            Context,
        ) + _lilybase)


    class ContextParser(Parser):
        argcount = 1
    ContextParser.rx = make_re((
            OpenBracket, CloseBracket,
        ) + _lilybase)
        

    class IncludeParser(Parser):
        argcount = 1
    IncludeParser.rx = make_re((
            IncludeFile,
        ) + _lilybase)



class LineColumnTokenizer(Tokenizer):
    def tokens(self, text, pos = 0):
        """
        Iterate over the tokens returned by Tokenizer.tokens(),
        adding line and column information to every token.
        """
        cursor = Cursor()
        if pos:
            cursor.walk(text[:pos])
        for token in Tokenizer.tokens(self, text, pos):
            token.line = cursor.line
            token.column = cursor.column
            yield token
            cursor.walk(token)


class Cursor(object):
    def __init__(self):
        self.line = 0
        self.column = 0
    
    def walk(self, text):
        lines = text.count('\n')
        if lines:
            self.line += lines
            self.column = len(text) - text.rfind('\n') - 1
        else:
            self.column += len(text)
        
