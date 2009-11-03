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
This module defines a Tokenizer class to parse and tokenize LilyPond text.

Usage:

>>> from ly.tokenizer import Tokenizer
>>> tokenizer = Tokenizer()
>>> lilypond = r"\relative c' { c d-\markup { Hi There } }"
>>> for token in tokenizer.tokens(lilypond):
...  print token.__class__.__name__, repr(token)
...
Command u'\\relative'
Space u' '
PitchWord u'c'
Unparsed u"'"
Space u' '
OpenDelimiter u'{'
Space u' '
PitchWord u'c'
Space u' '
PitchWord u'd'
Unparsed u'-'
Markup u'\\markup'
Space u' '
OpenBracket u'{'
Space u' '
MarkupWord u'Hi'
Space u' '
MarkupWord u'There'
Space u' '
CloseBracket u'}'
Space u' '
CloseDelimiter u'}'
>>>

Some LilyPond construct enter a different parsing mode, you can get the current
Tokenizer.Parser instance with parser().

The tokens returned by the iterator returned by tokens() are all instances
of subclasses of unicode. They are either instances of a subclass of
Tokenizer.Token (if they were parsed) or Tokenizer.Unparsed (if the piece of
text was not understood).

The Unparsed class and all Token subclasses are attributes of the Tokenizer
class (so they are nested classes). You can subclass Tokenizer to add your own
token classes. Each token class defines the regular expression pattern it
matches in its rx class attribute.

There are also Parser subclasses, defined as Tokenizer class attributes.
Those are instantiated to look for specific tokens in LilyPond input text.
The items() static method of the Parser subclasses should return a tuple of
token classes (found as attributes of the Tokenizer (sub)class).

Upon class construction of the/a Tokenizer (sub)class, a regular expression is
automatically created for each Parser subclass to parse a piece of LilyPond input
text for the list of tokens returned by its items() method. You can also easily
subclass the Parser classes.
"""

import re


def _make_re(classes):
    """
    Expects a list of classes representing LilyPond input atoms. Returns
    compiled regular expression with named groups, to match input of the listed
    types. Reads the rx class attribute of the given classes.
    """
    return re.compile(
        "|".join("(?P<%s>%s)" % (cls.__name__, cls.rx) for cls in classes),
        re.DOTALL)


class _tokenizer_meta(type):
    """
    This metaclass makes sure that the regex patterns of Parser subclasses
    inside a subclassed Tokenizer are always correct.
    
    It checks the items() method of all Parser subclasses and creates a
    pattern attribute. If that's different, a new copy (subclass) of the Parser
    subclass is created with the correct pattern.
    """
    def __init__(cls, className, bases, attrd):
        for name in dir(cls):
            attr = getattr(cls, name)
            if (isinstance(attr, type) and issubclass(attr, cls.Parser)
                    and attr is not cls.Parser):
                # We have a Parser subclass. If it has already a pattern
                # that's different from the one created from the items()
                # method output, copy the class. (The pattern is a compiled
                # regex pattern.)
                pattern = _make_re(attr.items(cls))
                if 'pattern' not in attr.__dict__:
                    attr.pattern = pattern
                elif attr.pattern.pattern != pattern.pattern:
                    setattr(cls, name, type(name, (attr,), {'pattern': pattern}))


class Tokenizer(object):
    """
    This class defines an environment to parse LilyPond text input.
    
    There are two types of nested classes (accessible as class attributes, but
    also via a Tokenizer instance):
    
    - Subclasses of Token (or Unparsed): tokens of LilyPond input.
    - Subclasses of Parser: container with regex to parse LilyPond input.
    """
    __metaclass__ = _tokenizer_meta
    
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
        
    def enter(self, parserClass, token = None, argcount = None):
        """ (Internal) Enter a new parser. """
        self.state.append(parserClass(token, argcount))

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
            m = self.state[-1].pattern.search(text, pos)
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
    class Token(unicode):
        """
        Represents a parsed piece of LilyPond text, the subclass determines
        the type.
        The matchObj delivers the string and the position.
        The state can be manipulated on instantiation.
        """
        def __new__(cls, matchObj, tokenizer):
            obj = unicode.__new__(cls, matchObj.group())
            obj.pos = matchObj.pos
            return obj

    class Item(Token):
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

    class Increaser(Token):
        def __init__(self, matchObj, tokenizer):
            tokenizer.inc()
            
    class Decreaser(Token):
        def __init__(self, matchObj, tokenizer):
            tokenizer.dec()

    class Leaver(Token):
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
        
    class Scheme(Token):
        rx = "#"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.SchemeParser, self)

    class Comment(Token):
        rx = r'%{.*?%}|%[^\n]*'

    class Space(Token):
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

    class OpenChord(Token):
        rx = "<"
        
    class CloseChord(Token):
        rx = ">"

    class Articulation(Token):
        rx = "[-_^][_.>|+^-]"
        
    class Dynamic(Token):
        rx = r"\\[<>!]"

    class VoiceSeparator(Token):
        rx = r"\\\\"

    class Digit(Token):
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

    class SchemeComment(Token):
        rx = r";[^\n]*|#!.*?!#"
        
    class SchemeLily(Token):
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
        """
        This is the base class for parsers.  The Tokenizer's meta class 
        looks for descendants of this class and creates parsing patterns.
        """
        pattern = None  # This is filled in by the Tokenizer's meta class.
        items = staticmethod(lambda cls: ())
        argcount = 0
        
        def __init__(self, token = None, argcount = None):
            self.level = 0
            self.token = token
            if argcount is not None:
                self.argcount = argcount

    
    # base stuff to parse in LilyPond input
    lilybaseItems = classmethod(lambda cls: (
        cls.Comment,
        cls.String,
        cls.IncompleteString,
        cls.EndSchemeLily,
        cls.Scheme,
        cls.Section,
        cls.LyricMode,
        cls.ChordMode,
        cls.FigureMode,
        cls.NoteMode,
        cls.Markup,
        cls.MarkupLines,
        cls.Include,
        cls.Command,
        cls.Space,
    ))
    
    class ToplevelParser(Parser):
        items = staticmethod(lambda cls: (
            cls.OpenDelimiter,
            cls.CloseDelimiter,
            cls.PitchWord,
        ) + cls.lilybaseItems())
    
    class SchemeParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.String,
            cls.IncompleteString,
            cls.SchemeChar,
            cls.SchemeComment,
            cls.SchemeOpenParenthesis,
            cls.SchemeCloseParenthesis,
            cls.SchemeLily,
            cls.SchemeWord,
            cls.Space,
        ))
    
    class MarkupParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.MarkupScore,
            cls.MarkupCommand,
            cls.OpenBracket,
            cls.CloseBracket,
            cls.MarkupWord,
        ) + cls.lilybaseItems())
        
    class InputModeParser(Parser):
        """
        Abstract base class for input modes such as \lyricmode, \figuremode,
        \chordmode etc.
        """
        argcount = 1

    class LyricModeParser(InputModeParser):
        items = staticmethod(lambda cls: (
            cls.OpenBracket,
            cls.CloseBracket,
            cls.LyricWord,
        ) + cls.lilybaseItems())

    class ChordModeParser(ToplevelParser, InputModeParser):
        argcount = 1

    class FigureModeParser(ToplevelParser, InputModeParser):
        argcount = 1

    class NoteModeParser(ToplevelParser, InputModeParser):
        argcount = 1

    class SectionParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.OpenBracket,
            cls.CloseBracket,
            cls.Context,
        ) + cls.lilybaseItems())
    
    class ContextParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.OpenBracket,
            cls.CloseBracket,
        ) + cls.lilybaseItems())

    class IncludeParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.IncludeFile,
        ) + cls.lilybaseItems())


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
    """
    A Cursor instance can walk() over any piece of plain text,
    maintaining line and column positions by looking at newlines in the text.
    """
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
        
