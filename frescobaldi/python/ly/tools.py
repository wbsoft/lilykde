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
All kinds of tools needed to manipulate strings with LilyPond input.
"""

import ly.pitch
import ly.tokenize        

class Tokenizer(ly.tokenize.LangReaderMixin, ly.tokenize.MusicTokenizer):
    pass


class Pitch(ly.pitch.Pitch):
    @classmethod
    def fromToken(cls, token, tokenizer):
        result = tokenizer.readStep(token)
        if result:
            p = cls()
            p.note, p.alter = result
            p.octave = ly.pitch.octaveToNum(token.octave)
            p.cautionary = token.cautionary
            if token.octcheck:
                p.octaveCheck = ly.pitch.octaveToNum(token.octcheck)
            return p
    

def relativeToAbsolute(text, start = 0, changes = None):
    """
    Convert \relative { }  music to absolute pitches.
    Returns a ChangeList instance that contains the changes.
    """
    tokenizer = Tokenizer()
    tokens = tokenizer.tokens(text)
    
    # Walk through not-selected text, to track the state and the 
    # current pitch language (the LangReader instance does this).
    if start:
        for token in tokens:
            if token.end >= start:
                break
    
    if changes is None:
        changes = ly.tokenize.ChangeList(text)
    
    def newPitch(token, pitch, lastPitch):
        """
        Writes a new pitch with all parts except the octave taken from the
        token. The octave is set using lastPitch.
        """
        pitch.absolute(lastPitch)
        changes.replaceToken(token, '%s%s%s' % (
            token.step,
            token.cautionary,
            ly.pitch.octaveToString(pitch.octave)))
        
    class gen(object):
        """
        Advanced generator of tokens, discarding whitespace and comments,
        and automatically detecting \relative blocks and places where a new
        LilyPond parsing context is started, like \score inside \markup.
        """
        def __iter__(self):
            return self
            
        def next(self):
            token = tokens.next()
            while isinstance(token, (tokenizer.Space, tokenizer.Comment)):
                token = tokens.next()
            if token == "\\relative":
                relative(token.pos)
                token = tokens.next()
            elif isinstance(token, tokenizer.MarkupScore):
                absolute()
                token = tokens.next()
            return token
    
    source = gen()
    
    def consume():
        """ Consume tokens till the level drops (we exit a construct). """
        depth = tokenizer.depth()
        for token in source:
            yield token
            if tokenizer.depth() < depth:
                return
    
    def absolute():
        """ Consume tokens while not doing anything. """
        for token in consume():
            pass
    
    def relative(start):
        """
        Called when a \\relative command is encountered.
        start is the position of the \\relative token, to remove it later.
        """
        # find the pitch after the relative command
        lastPitch = None
        for token in source:
            if not lastPitch and isinstance(token, tokenizer.Pitch):
                lastPitch = Pitch.fromToken(token, tokenizer)
                continue
            else:
                if not lastPitch:
                    lastPitch = Pitch.c1()
                # remove the \relative <pitch> tokens
                changes.remove(start, token.pos)
                # eat stuff like \new Staff == "bla" \new Voice \notes etc.
                while True:
                    if token in ('\\new', '\\context'):
                        source.next() # skip context type
                        token = source.next()
                        if token == '=':
                            source.next() # skip context name
                            token = source.next()
                    elif isinstance(token, (tokenizer.ChordMode, tokenizer.NoteMode)):
                        token = source.next()
                    else:
                        break
                if isinstance(token, tokenizer.OpenDelimiter):
                    # Handle full music expression { ... } or << ... >>
                    for token in consume():
                        # skip commands with pitches that do not count
                        if token in ('\\key', '\\transposition'):
                            source.next()
                        elif token == '\\transpose':
                            source.next()
                            source.next()
                        elif token == '\\octaveCheck':
                            start = token.pos
                            token = source.next()
                            if isinstance(token, tokenizer.Pitch):
                                p = Pitch.fromToken(token, tokenizer)
                                if p:
                                    lastPitch = p
                                    changes.remove(start, token.end)
                        elif isinstance(token, tokenizer.OpenChord):
                            # handle chord
                            chord = [lastPitch]
                            for token in source:
                                if isinstance(token, tokenizer.CloseChord):
                                    lastPitch = chord[:2][-1] # same or first
                                    break
                                elif isinstance(token, tokenizer.Pitch):
                                    p = Pitch.fromToken(token, tokenizer)
                                    if p:
                                        newPitch(token, p, chord[-1])
                                        chord.append(p)
                        elif isinstance(token, tokenizer.Pitch):
                            p = Pitch.fromToken(token, tokenizer)
                            if p:
                                newPitch(token, p, lastPitch)
                                lastPitch = p
                elif isinstance(token, tokenizer.OpenChord):
                    # Handle just one chord
                    for token in source:
                        if isinstance(token, tokenizer.CloseChord):
                            break
                        elif isinstance(token, tokenizer.Pitch):
                            p = Pitch.fromToken(token, tokenizer)
                            if p:
                                newPitch(token, p, lastPitch)
                                lastPitch = p
                elif isinstance(token, tokenizer.Pitch):
                    # Handle just one pitch
                    p = Pitch.fromToken(token, tokenizer)
                    if p:
                        newPitch(token, p, lastPitch)
                return
    
    # Do it!
    for token in source:
        pass
    return changes

def absoluteToRelative(text, start = 0, changes = None):
    """
    Converts the selected music expression or all toplevel expressions to \relative ones.
    """
    tokenizer = Tokenizer()
    tokens = tokenizer.tokens(text)
    
    # Walk through not-selected text, to track the state and the 
    # current pitch language (the LangReader instance does this).
    if start:
        for token in tokens:
            if token.end >= start:
                break
    
    if changes is None:
        changes = ly.tokenize.ChangeList(text)
    
    def newPitch(token, pitch):
        """
        Writes a new pitch with all parts except the octave taken from the
        token.
        """
        changes.replaceToken(token, '%s%s%s' % (
            token.step,
            token.cautionary,
            ly.pitch.octaveToString(pitch.octave)))
        
    class gen(object):
        """
        Advanced generator of tokens, discarding whitespace and comments,
        and automatically detecting \relative blocks and places where a new
        LilyPond parsing context is started, like \score inside \markup.
        """
        def __iter__(self):
            return self
            
        def next(self):
            token = tokens.next()
            while isinstance(token, (tokenizer.Space, tokenizer.Comment)):
                token = tokens.next()
            if token == "\\relative":
                relative()
                token = tokens.next()
            elif isinstance(token, tokenizer.ChordMode):
                absolute() # do not change chords
            elif isinstance(token, tokenizer.MarkupScore):
                absolute()
                token = tokens.next()
            return token
    
    source = gen()
    
    def consume():
        """ Consume tokens till the level drops (we exit a construct). """
        depth = tokenizer.depth()
        for token in source:
            yield token
            if tokenizer.depth() < depth:
                return
    
    def absolute():
        """ Consume tokens while not doing anything. """
        for token in consume():
            pass
    
    def relative():
        """ Consume the whole \relative expression without doing anything. """
        # skip pitch argument
        token = source.next()
        if isinstance(token, tokenizer.Pitch):
            token = source.next()
        if isinstance(token, tokenizer.OpenDelimiter):
            for token in consume():
                pass
        elif isinstance(token, tokenizer.OpenChord):
            while not isinstance(token, tokenizer.CloseChord):
                token = source.next()
    
    # Do it!
    startToken = None
    for token in source:
        if isinstance(token, tokenizer.OpenDelimiter):
            # Ok, parse current expression.
            startToken = token # before which to insert the \relative command
            lastPitch = None
            chord = None
            try:
                for token in consume():
                    # skip commands with pitches that do not count
                    if token in ('\\key', '\\transposition'):
                        source.next()
                    elif token == '\\transpose':
                        source.next()
                        source.next()
                    elif isinstance(token, tokenizer.OpenChord):
                        # Handle chord
                        chord = []
                    elif isinstance(token, tokenizer.CloseChord):
                        if chord:
                            lastPitch = chord[0]
                        chord = None
                    elif isinstance(token, tokenizer.Pitch):
                        # Handle pitch
                        p = Pitch.fromToken(token, tokenizer)
                        if p:
                            if lastPitch is None:
                                lastPitch = Pitch.c1()
                                lastPitch.octave = p.octave
                                if p.note > 3:
                                    lastPitch.octave += 1
                                changes.insert(startToken.pos,
                                    "\\relative %s " %
                                    lastPitch.output(tokenizer.language))
                            newPitch(token, p.relative(lastPitch))
                            lastPitch = p
                            # remember the first pitch of a chord
                            chord == [] and chord.append(p)
            except StopIteration:
                pass # because of the source.next() statements
    if startToken is None:  # no single expression converted?
        raise ly.NoExpressionFound
    return changes

def languageAndKey(text):
    """
    Return language and key signature pitch (as Pitch) of text.
    """
    tokenizer = Tokenizer()
    tokens = iter(tokenizer.tokens(text))
    keyPitch = Pitch.c1()

    for token in tokens:
        if token == "\\key":
            for token in tokens:
                if not isinstance(token, (tokenizer.Space, tokenizer.Comment)):
                    break
            if isinstance(token, tokenizer.Pitch):
                p = Pitch.fromToken(token, tokenizer)
                if p:
                    keyPitch = p
                    keyPitch.octave = 1
    return tokenizer.language, keyPitch

def transpose(text, transposer, start = 0, changes = None):
    """
    Transpose all or selected pitches.
    Raises ly.QuarterToneAlterationNotAvailable if quarter tones are
    requested but not available in the current language.
    """
    tokenizer = Tokenizer()
    tokens = tokenizer.tokens(text)
    
    if changes is None:
        changes = ly.tokenize.ChangeList(text)
    
    class gen(object):
        """
        Advanced generator of tokens, discarding whitespace and comments,
        and automatically detecting \relative blocks and places where a new
        LilyPond parsing context is started, like \score inside \markup.
        
        It also handles transposition tasks that are the same in relative
        and absolute environments.
        """
        def __init__(self):
            self.inSelection = not start
            
        def __iter__(self):
            return self
            
        def next(self):
            while True:
                token = tokens.next()
                if isinstance(token, (tokenizer.Space, tokenizer.Comment)):
                    continue
                elif not self.inSelection and token.pos >= start:
                    self.inSelection = True
                # Handle stuff that's the same in relative and absolute here
                if token == "\\relative":
                    relative()
                elif isinstance(token, tokenizer.MarkupScore):
                    absolute(consume())
                elif isinstance(token, tokenizer.ChordMode):
                    chordmode()
                elif token == "\\transposition":
                    source.next() # skip pitch
                elif token == "\\transpose":
                    if self.inSelection:
                        for token in source.next(), source.next():
                            if isinstance(token, tokenizer.Pitch):
                                transpose(token)
                    else:
                        source.next(), source.next()
                elif token == "\\key":
                    token = source.next()
                    if self.inSelection and isinstance(token, tokenizer.Pitch):
                        transpose(token, 0)
                else:
                    return token
    
    source = gen()
    
    def consume():
        """ Consume tokens till the level drops (we exit a construct). """
        depth = tokenizer.depth()
        for token in source:
            yield token
            if tokenizer.depth() < depth:
                return
    
    def transpose(token, resetOctave = None):
        """ Transpose absolute pitch in token, must be tokenizer.Pitch """
        p = Pitch.fromToken(token, tokenizer)
        if p:
            transposer.transpose(p)
            if resetOctave is not None:
                p.octave = resetOctave
            changes.replaceToken(token, p.output(tokenizer.language))
    
    def relative():
        """ Called when \\relative is encountered. """
        
        def transposeRelative(token, tokenizer, lastPitch):
            """
            Make a new relative pitch from token, if possible.
            Return the last pitch used (untransposed).
            """
            p = Pitch.fromToken(token, tokenizer)
            if p:
                # absolute pitch determined from untransposed pitch of lastPitch
                octaveCheck = p.octaveCheck is not None
                p.absolute(lastPitch)
                if source.inSelection:
                    # we may change this pitch. Make it relative against the
                    # transposed lastPitch.
                    try:
                        last = lastPitch.transposed
                    except AttributeError:
                        last = lastPitch
                    # transpose a copy and store that in the transposed
                    # attribute of lastPitch. Next time that is used for
                    # making the next pitch relative correctly.
                    copy = p.copy()
                    transposer.transpose(copy)
                    p.transposed = copy # store transposed copy in new lastPitch
                    new = copy.relative(last)
                    if octaveCheck:
                        new.octaveCheck = copy.octave
                    if relPitchToken:
                        # we are allowed to change the pitch after the
                        # \relative command. lastPitch contains this pitch.
                        lastPitch.octave += new.octave
                        new.octave = 0
                        changes.replaceToken(relPitchToken[0], lastPitch.output(tokenizer.language))
                        del relPitchToken[:]
                    changes.replaceToken(token, new.output(tokenizer.language))
                return p
            return lastPitch
        
        lastPitch = None
        relPitchToken = [] # we use a list so it can be changed from inside functions

        for token in source:
            if not lastPitch and isinstance(token, tokenizer.Pitch):
                lastPitch = Pitch.fromToken(token, tokenizer)
                if lastPitch and source.inSelection:
                    relPitchToken.append(token)
                continue
            else:
                if not lastPitch:
                    lastPitch = Pitch.c1()
                # eat stuff like \new Staff == "bla" \new Voice \notes etc.
                while True:
                    if token in ('\\new', '\\context'):
                        source.next() # skip context type
                        token = source.next()
                        if token == '=':
                            source.next() # skip context name
                            token = source.next()
                    elif isinstance(token, tokenizer.NoteMode):
                        token = source.next()
                    else:
                        break
                if isinstance(token, tokenizer.OpenDelimiter):
                    # Handle full music expression { ... } or << ... >>
                    for token in consume():
                        if token == '\\octaveCheck':
                            token = source.next()
                            if isinstance(token, tokenizer.Pitch):
                                p = Pitch.fromToken(token, tokenizer)
                                if p:
                                    if source.inSelection:
                                        copy = p.copy()
                                        transposer.transpose(copy)
                                        p.transposed = copy
                                        changes.replaceToken(token,
                                            copy.output(tokenizer.language))    
                                    lastPitch = p
                                    del relPitchToken[:]
                        elif isinstance(token, tokenizer.OpenChord):
                            chord = [lastPitch]
                            for token in source:
                                if isinstance(token, tokenizer.CloseChord):
                                    lastPitch = chord[:2][-1] # same or first
                                    break
                                elif isinstance(token, tokenizer.Pitch):
                                    chord.append(transposeRelative(token, tokenizer, chord[-1]))
                        elif isinstance(token, tokenizer.Pitch):
                            lastPitch = transposeRelative(token, tokenizer, lastPitch)
                elif isinstance(token, tokenizer.OpenChord):
                    # Handle just one chord
                    for token in source:
                        if isinstance(token, tokenizer.CloseChord):
                            break
                        elif isinstance(token, tokenizer.Pitch):
                            lastPitch = transposeRelative(token, tokenizer, lastPitch)
                elif isinstance(token, tokenizer.Pitch):
                    # Handle just one pitch
                    transposeRelative(token, tokenizer, lastPitch)
                return
        
    def chordmode():
        """ Called inside \\chordmode or \\chords. """
        for token in consume():
            if source.inSelection and isinstance(token, tokenizer.Pitch):
                transpose(token, 0)
            
    def absolute(tokens):
        """ Called when outside a possible \\relative environment. """
        for token in tokens:
            print token, token.__class__.__name__
            if source.inSelection and isinstance(token, tokenizer.Pitch):
                transpose(token)
    
    # Do it!
    absolute(source)
    return changes

def translate(text, lang, start = 0, changes = None):
    """
    Change the LilyPond pitch name language in our document to lang.
    Raises ly.QuarterToneAlterationNotAvailable if quarter tones are
    requested but not available in the target language.
    """
    writer = ly.pitch.pitchWriter[lang]
    reader = ly.pitch.pitchReader["nederlands"]
    tokenizer = ly.tokenize.Tokenizer()
    tokens = tokenizer.tokens(text)
    
    # Walk through not-selected text, to track the state and the 
    # current pitch language.
    if start:
        for token in tokens:
            if isinstance(token, tokenizer.IncludeFile):
                langName = token[1:-4]
                if langName in ly.pitch.pitchInfo:
                    reader = ly.pitch.pitchReader[langName]
            if token.end >= start:
                break
    
    if changes is None:
        changes = ly.tokenize.ChangeList(text)

    # Now walk through the part that needs to be translated.
    includeCommandChanged = False
    for token in tokens:
        if isinstance(token, tokenizer.IncludeFile):
            langName = token[1:-4]
            if langName in ly.pitch.pitchInfo:
                reader = ly.pitch.pitchReader[langName]
                changes.replaceToken(token, '"%s.ly"' % lang)
                includeCommandChanged = True
        elif isinstance(token, tokenizer.PitchWord):
            result = reader(token)
            if result:
                note, alter = result
                # Write out the translated pitch.
                changes.replaceToken(token, writer(note, alter))
    return changes, includeCommandChanged


