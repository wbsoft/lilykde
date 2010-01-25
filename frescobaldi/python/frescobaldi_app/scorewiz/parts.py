# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
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

from __future__ import unicode_literals

"""
Part types for the Score Wizard (scorewiz/__init__.py).
In separate file to ease maintenance.
"""

from fractions import Fraction
from collections import defaultdict

from PyQt4.QtCore import QRegExp, Qt
from PyQt4.QtGui import (
    QCheckBox, QComboBox, QGroupBox, QLabel, QRadioButton, QRegExpValidator,
    QSpinBox, QVBoxLayout)
from PyKDE4.kdecore import i18n, ki18n
from PyKDE4.kdeui import KHBox, KVBox

import ly
from ly.dom import *
import frescobaldi_app.scorewiz

I18N_NOOP = lambda s: s


# Widgets used by different part types

def voicesWidget(
    layout, title=None, minValue=1, maxValue=4, default=1, tooltip=None):
    """
    Creates a widget for setting the number of voices.
    Adds a HBox to the layout and returns the created QSpinBox.
    """
    h = KHBox()
    l = QLabel(title or i18n("Voices:"), h)
    sb = QSpinBox(h)
    sb.setRange(minValue, maxValue)
    sb.setValue(default)
    l.setBuddy(sb)
    sb.setToolTip(tooltip or i18n("How many voices to put in this staff."))
    layout.addWidget(h)
    return sb


# Base classes for the part types in this file.
# (For the real part type classes see below.)

class Part(frescobaldi_app.scorewiz.PartBase):
    """
    The base class for our part types.
    Adds some convenience methods for often used tasks.
    """
    def assign(self, name=None):
        """
        Creates an assignment. name is a string name, if not given
        the class name is used with the first letter lowered.
        returns the assignment and the reference for the name.
        """
        ref = Reference(name or self.identifier())
        a = Assignment(ref)
        self.assignments.append(a)
        return a, ref
    
    def assignMusic(self, name=None, octave=0, transposition=None):
        """
        Creates a \\relative stub and an assignment for it.
        Returns the contents of the stub for other possible manipulations,
        and the Reference object.
        """
        a, ref = self.assign(name)
        stub = Relative(a)
        Pitch(octave, 0, 0, stub)
        s = Seq(stub)
        Identifier('global', s).after = 1
        if transposition is not None:
            toct, tnote, talter = transposition
            Pitch(toct, tnote, Fraction(talter, 2), Transposition(s))
        LineComment(i18n("Music follows here."), s)
        BlankLine(s)
        return s, ref


class SingleVoicePart(Part):
    """
    The abstract base class for single voice part types.
    The build function just creates one staff with one voice,
    and uses the .clef, .transposition, .midiInstrument and .instrumentNames
    class (or instance) attributes.
    """

    # A subclass could set a clef for the staff (e.g. "bass")
    clef = None

    # The octave for the \relative command
    octave = 1

    # A subclass could set a transposition here.
    transposition = None

    # The MIDI instrument to use: see
    # http://lilypond.org/doc/latest/Documentation/user/lilypond/MIDI-instrument-names
    midiInstrument = None

    # The instrument names, both long and short, combined with a pipe symbol, to
    # ease the translation (otherwise the short names would be incomprehensible.)
    instrumentNames = "longname|shortname"

    def build(self, builder, braces=False):
        """
        Build a single staff, with instrument name, midi instrument, octave and
        possible transposition.  Returns the staff and the stub for other
        possible manipulations.
        """
        stub, ref = self.assignMusic(None, self.octave, self.transposition)
        staff = Staff()
        builder.setInstrumentNames(staff, self.instrumentNames, self.num)
        builder.setMidiInstrument(staff, self.midiInstrument)
        s = braces and Seq(staff) or Seqr(staff)
        if self.clef:
            Clef(self.clef, s)
        Identifier(ref, s)
        self.nodes.append(staff)
        return staff, stub


class StringPart(SingleVoicePart):
    """
    All string instruments
    """
    pass


class TablaturePart(SingleVoicePart):
    """
    A class for instruments that support TabStaffs.
    Can easily support multi-voice staves.
    """
    octave = 0
    tunings = ()    # may contain a list of tunings.
    tabFormat = ''  # can contain a tablatureFormat value.

    def widgets(self, layout):
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Staff type:"), h)
        self.staffType = QComboBox(h)
        l.setBuddy(self.staffType)
        self.staffType.addItems((
            i18n("Normal staff"),
            i18n("Tablature"),
            i18n("Both")))
        if self.tunings:
            self.staffType.activated.connect(self.slotTabEnable)
            self.widgetsTuning(layout)
            self.slotTabEnable(0)

    def widgetsTuning(self, layout):
        """ Implement widgets related to tuning """
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Tuning:"), h)
        self.tuningSel = QComboBox(h)
        l.setBuddy(self.tuningSel)
        self.tuningSel.addItem(i18n("Default"))
        self.tuningSel.addItems([name.toString() for name, t in self.tunings])
        self.tuningSel.setCurrentIndex(1)

    def slotTabEnable(self, enable):
        """
        Called when the user changes the staff type.
        Non-zero if the user wants a TabStaff.
        """
        self.tuningSel.setEnabled(bool(enable))
    
    def voiceCount(self):
        """
        Returns the number of voices. Can be made user-settable in subclasses.
        """
        return 1
        
    def build(self, builder):
        # First make assignments for the voices we want to create
        numVoices = self.voiceCount()
        if numVoices == 1:
            voices = (self.identifier(),)
        elif numVoices == 2:
            order = 1, 2
            voices = 'upper', 'lower'
        elif numVoices == 3:
            order = 1, 3, 2
            voices = 'upper', 'middle', 'lower'
        else:
            order = 1, 2, 3, 4
            voices = [self.identifier() + ly.nums(i) for i in order]
        
        refs = [self.assignMusic(name, self.octave, self.transposition)[1]
                    for name in voices]
        
        staffType = self.staffType.currentIndex()
        if staffType in (0, 2):
            # create a normal staff
            staff = Staff()
            seq = Seqr(staff)
            if self.clef:
                Clef(self.clef, seq)
            mus = Simr(seq)
            for ref in refs[:-1]:
                Identifier(ref, mus)
                VoiceSeparator(mus)
            Identifier(refs[-1], mus)
            builder.setMidiInstrument(staff, self.midiInstrument)
        
        if staffType in (1, 2):
            # create a tab staff
            tabstaff = TabStaff()
            if self.tabFormat:
                tabstaff.getWith()['tablatureFormat'] = Scheme(self.tabFormat)
            self.setTunings(tabstaff)
            sim = Simr(tabstaff)
            if numVoices == 1:
                Identifier(refs[0], sim)
            else:
                for num, ref in zip(order, refs):
                    s = Seq(TabVoice(parent=sim))
                    Text('\\voice' + ly.nums(num), s)
                    Identifier(ref, s)
        
        if staffType == 0:
            # only a normal staff
            p = staff
        elif staffType == 1:
            # only a TabStaff
            builder.setMidiInstrument(tabstaff, self.midiInstrument)
            p = tabstaff
        else:
            # both TabStaff and normal staff
            p = StaffGroup()
            s = Sim(p)
            s.append(staff)
            s.append(tabstaff)
        
        builder.setInstrumentNames(p, self.instrumentNames, self.num)
        self.nodes.append(p)

    def setTunings(self, tab):
        if self.tunings and self.tuningSel.currentIndex() > 0:
            tuning = self.tunings[self.tuningSel.currentIndex() - 1][1]
            tab.getWith()['stringTunings'] = Scheme(tuning)


class WoodWindPart(SingleVoicePart):
    """
    All woodwind instruments
    """
    pass


class BrassPart(SingleVoicePart):
    """
    All brass instruments.
    """
    pass


class VocalPart(Part):
    """
    Base class for vocal stuff.
    """
    midiInstrument = 'choir aahs'
    
    def assignLyrics(self, name, verse=0):
        """
        Creates an empty assignment for lyrics.
        Returns the reference for the name.
        """
        l = LyricMode()
        if verse:
            name = name + ly.nums(verse)
            Line('\\set stanza = "{0}."'.format(verse), l)
        a, ref = self.assign(name)
        a.append(l)
        LineComment(i18n("Lyrics follow here."), l)
        BlankLine(l)
        return ref
        
    def widgets(self, layout):
        self.stanzaWidget(layout)
        self.ambitusWidget(layout)

    def stanzaWidget(self, layout):
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Stanzas:"), h)
        self.stanzas = QSpinBox(h)
        self.stanzas.setRange(1, 99)
        l.setBuddy(self.stanzas)
        h.setToolTip(i18n("The number of stanzas."))

    def ambitusWidget(self, layout):
        self.ambitus = QCheckBox(i18n("Ambitus"))
        layout.addWidget(self.ambitus)
        self.ambitus.setToolTip(i18n(
            "Show the pitch range of the voice at the beginning of the staff."))

    def addStanzas(self, node):
        """
        Add stanzas in self.stanzas.value() to the given (Voice) node
        using \\addlyrics.
        """
        if self.stanzas.value() == 1:
            Identifier(self.assignLyrics('verse'), AddLyrics(node))
        else:
            for i in range(self.stanzas.value()):
                Identifier(self.assignLyrics('verse', i + 1), AddLyrics(node))


class VocalSoloPart(VocalPart, SingleVoicePart):
    """
    Base class for solo voices
    """
    def build(self, builder):
        staff, stub = SingleVoicePart.build(self, builder, braces=True)
        stub.insert(1, Line('\\dynamicUp')) # just after the \global
        self.addStanzas(staff)
        if self.ambitus.isChecked():
            Line('\\consists "Ambitus_engraver"', staff.getWith())


class KeyboardPart(Part):
    """
    Base class for keyboard instruments.
    """
    def buildStaff(self, builder, name, octave, numVoices=1, node=None, clef=None):
        """
        Build a staff with the given number of voices and name.
        """
        staff = Staff(name, parent=node)
        builder.setMidiInstrument(staff, self.midiInstrument)
        c = Seqr(staff)
        if clef:
            Clef(clef, c)
        if numVoices == 1:
            stub, ref = self.assignMusic(name, octave)
            Identifier(ref, c)
        else:
            c = Sim(c)
            for i in range(1, numVoices):
                stub, ref = self.assignMusic(name + ly.nums(i), octave)
                Identifier(ref, c)
                VoiceSeparator(c)
            stub, ref = self.assignMusic(name + ly.nums(numVoices), octave)
            Identifier(ref, c)
        return staff

    def build(self, builder):
        """ setup structure for a 2-staff PianoStaff. """
        p = PianoStaff()
        builder.setInstrumentNames(p, self.instrumentNames, self.num)
        s = Sim(p)
        # add two staves, with a respective number of voices.
        self.buildStaff(builder, 'right', 1, self.upperVoices.value(), s)
        self.buildStaff(builder, 'left', 0, self.lowerVoices.value(), s, "bass")
        self.nodes.append(p)

    def widgets(self, layout):
        l = QLabel('{0} <i>({1})</i>'.format(
            i18n("Adjust how many separate voices you want on each staff."),
            i18n("This is primarily useful when you write polyphonic music "
            "like a fuge.")))
        l.setWordWrap(True)
        layout.addWidget(l)
        self.upperVoices = voicesWidget(layout, i18n("Right hand:"))
        self.lowerVoices = voicesWidget(layout, i18n("Left hand:"))


class PitchedPercussionPart(SingleVoicePart):
    """
    All pitched percussion instruments.
    """
    pass


#############################################################################
#                                                                           #
# Below the part types are defined. You may add new instruments/part types. #
# The categories() function below returns all parts, neatly categorized.    #
# Of course you should also put your part in there, in a sensible group.    #
#                                                                           #
#############################################################################

class Chords(Part):
    _name = ki18n("Chord names")

    def build(self, builder):
        p = ChordNames()
        a, ref = self.assign('chordNames')
        Identifier(ref, p)
        s = ChordMode(a)
        Identifier('global', s).after = 1
        i = self.chordStyle.currentIndex()
        if i > 0:
            Line('\\{0}Chords'.format(
                ('german', 'semiGerman', 'italian', 'french')[i-1]), s)
        LineComment(i18n("Chords follow here."), s)
        BlankLine(s)
        self.nodes.append(p)
        if self.guitarFrets.isChecked():
            f = FretBoards()
            Identifier(ref, f)
            self.nodes.append(f)
            builder.include("predefined-guitar-fretboards.ly")

    def widgets(self, layout):
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Chord style:"), h)
        self.chordStyle = QComboBox(h)
        l.setBuddy(self.chordStyle)
        self.chordStyle.addItems((
            i18n("Default"),
            i18n("German"),
            i18n("Semi-German"),
            i18n("Italian"),
            i18n("French")))
        self.guitarFrets = QCheckBox(i18n("Guitar fret diagrams"))
        self.guitarFrets.setToolTip(i18n(
            "Show predefined guitar fret diagrams below the chord names "
            "(LilyPond 2.12 and above)."))
        layout.addWidget(self.guitarFrets)
        

class BassFigures(Part):
    _name = ki18n("Figured Bass")

    def build(self, builder):
        a, ref = self.assign('figBass')
        s = FigureMode(a)
        p = FiguredBass()
        Identifier(ref, p)
        Identifier('global', s)
        LineComment(i18n("Figures follow here."), s)
        BlankLine(s)
        if self.useExtenderLines.isChecked():
            p.getWith()['useBassFigureExtenders'] = Scheme('#t')
        self.nodes.append(p)

    def widgets(self, layout):
        self.useExtenderLines = QCheckBox(i18n("Use extender lines"))
        layout.addWidget(self.useExtenderLines)


class Violin(StringPart):
    _name = ki18n("Violin")
    instrumentNames = I18N_NOOP("Violin|Vl.")
    midiInstrument = 'violin'


class Viola(StringPart):
    _name = ki18n("Viola")
    instrumentNames = I18N_NOOP("Viola|Vla.")
    midiInstrument = 'viola'
    clef = 'alto'
    octave = 0


class Cello(StringPart):
    _name = ki18n("Cello")
    instrumentNames = I18N_NOOP("Cello|Cl.")
    midiInstrument = 'cello'
    clef = 'bass'
    octave = -1


class Contrabass(StringPart):
    _name = ki18n("Contrabass")
    instrumentNames = I18N_NOOP("Contrabass|Cb.")
    midiInstrument = 'contrabass'
    clef = 'bass'
    octave = -1


class BassoContinuo(Cello):
    _name = ki18n("Basso continuo")
    instrumentNames = I18N_NOOP("Basso Continuo|B.c.")

    def build(self, builder):
        p = Staff()
        builder.setInstrumentNames(p, self.instrumentNames, self.num)
        builder.setMidiInstrument(p, self.midiInstrument)
        s = Sim(p)
        Clef("bass", s)
        stub, ref = self.assignMusic('bcMusic', self.octave, self.transposition)
        Identifier(ref, s)
        a, ref = self.assign('bcFigures')
        b = FigureMode(a)
        Identifier(ref, s)
        Identifier('global', b)
        Line("\\override Staff.BassFigureAlignmentPositioning "
             "#'direction = #DOWN", b)
        LineComment(i18n("Figures follow here."), b)
        BlankLine(b)
        self.nodes.append(p)


class Mandolin(TablaturePart):
    _name = ki18n("Mandolin")
    instrumentNames = I18N_NOOP("Mandolin|Mdl.")
    midiInstrument = 'acoustic guitar (steel)'
    tunings = (
        (ki18n("Mandolin tuning"), 'mandolin-tuning'),
    )


class Banjo(TablaturePart):
    _name = ki18n("Banjo")
    instrumentNames = I18N_NOOP("Banjo|Bj.")
    midiInstrument = 'banjo'
    tabFormat = 'fret-number-tablature-format-banjo'
    tunings = (
        (ki18n("Open G-tuning (aDGBD)"), 'banjo-open-g-tuning'),
        (ki18n("C-tuning (gCGBD)"), 'banjo-c-tuning'),
        (ki18n("Modal tuning (gDGCD)"), 'banjo-modal-tuning'),
        (ki18n("Open D-tuning (aDF#AD)"), 'banjo-open-d-tuning'),
        (ki18n("Open Dm-tuning (aDFAD)"), 'banjo-open-dm-tuning'),
    )
    def widgetsTuning(self, layout):
        super(Banjo, self).widgetsTuning(layout)
        self.fourStrings = QCheckBox(i18n("Four strings (instead of five)"))
        layout.addWidget(self.fourStrings)

    def slotTabEnable(self, enable):
        super(Banjo, self).slotTabEnable(enable)
        self.fourStrings.setEnabled(bool(enable))

    def setTunings(self, tab):
        if not self.fourStrings.isChecked():
            super(Banjo, self).setTunings(tab)
        else:
            tab.getWith()['stringTunings'] = Scheme(
                '(four-string-banjo {0})'.format(
                    self.tunings[self.tuningSel.currentIndex()][1]))


class ClassicalGuitar(TablaturePart):
    _name = ki18n("Classical guitar")
    instrumentNames = I18N_NOOP("Guitar|Gt.")
    midiInstrument = 'acoustic guitar (nylon)'
    clef = "treble_8"
    tunings = (
        (ki18n("Guitar tuning"), 'guitar-tuning'),
        (ki18n("Open G-tuning"), 'guitar-open-g-tuning'),
    )

    def widgets(self, layout):
        super(ClassicalGuitar, self).widgets(layout)
        self.numVoices = voicesWidget(layout)
        
    def voiceCount(self):
        return self.numVoices.value()


class JazzGuitar(ClassicalGuitar):
    _name = ki18n("Jazz guitar")
    instrumentNames = I18N_NOOP("Jazz guitar|J.Gt.")
    midiInstrument = 'electric guitar (jazz)'


class Bass(TablaturePart):
    _name = ki18n("Bass")
    instrumentNames = I18N_NOOP("Bass|Bs.")  #FIXME
    midiInstrument = 'acoustic bass'
    clef = 'bass_8'
    octave = -2
    tunings = (
        (ki18n("Bass tuning"), 'bass-tuning'),
    )


class ElectricBass(Bass):
    _name = ki18n("Electric bass")
    instrumentNames = I18N_NOOP("Electric bass|E.Bs.")
    midiInstrument = 'electric bass (finger)'


class Harp(KeyboardPart):
    _name = ki18n("Harp")
    instrumentNames = I18N_NOOP("Harp|Hp.")
    midiInstrument = 'harp'

    def build(self, builder):
        """ setup structure for a 2-staff PianoStaff. """
        p = PianoStaff()
        builder.setInstrumentNames(p, self.instrumentNames, self.num)
        s = Sim(p)
        # add two staves, with a respective number of voices.
        self.buildStaff(builder, 'upper', 1, self.upperVoices.value(), s)
        self.buildStaff(builder, 'lower', 0, self.lowerVoices.value(), s, "bass")
        self.nodes.append(p)

    def widgets(self, layout):
        super(Harp, self).widgets(layout)
        self.upperVoices.parent().findChild(QLabel).setText(i18n("Upper staff:"))
        self.lowerVoices.parent().findChild(QLabel).setText(i18n("Lower staff:"))


class Flute(WoodWindPart):
    _name = ki18n("Flute")
    instrumentNames = I18N_NOOP("Flute|Fl.")
    midiInstrument = 'flute'


class Piccolo(WoodWindPart):
    _name = ki18n("Piccolo")
    instrumentNames = I18N_NOOP("Piccolo|Pic.")
    midiInstrument = 'piccolo'
    transposition = (1, 0, 0)


class BassFlute(WoodWindPart):
    _name = ki18n("Bass flute")
    instrumentNames = I18N_NOOP("Bass flute|Bfl.")
    midiInstrument = 'flute'
    transposition = (-1, 4, 0)


class Oboe(WoodWindPart):
    _name = ki18n("Oboe")
    instrumentNames = I18N_NOOP("Oboe|Ob.")
    midiInstrument = 'oboe'


class OboeDAmore(WoodWindPart):
    _name = ki18n("Oboe d'Amore")
    instrumentNames = I18N_NOOP("Oboe d'amore|Ob.d'am.")
    midiInstrument = 'oboe'
    transposition = (-1, 5, 0)


class EnglishHorn(WoodWindPart):
    _name = ki18n("English Horn")
    instrumentNames = I18N_NOOP("English horn|Eng.h.")
    midiInstrument = 'english horn'
    transposition = (-1, 3, 0)


class Bassoon(WoodWindPart):
    _name = ki18n("Bassoon")
    instrumentNames = I18N_NOOP("Bassoon|Bn.")
    midiInstrument = 'bassoon'
    clef = 'bass'
    octave = -1


class ContraBassoon(WoodWindPart):
    _name = ki18n("Contrabassoon")
    instrumentNames = I18N_NOOP("Contrabassoon|C.Bn.")
    midiInstrument = 'bassoon'
    transposition = (-1, 0, 0)
    clef = 'bass'
    octave = -1


class Clarinet(WoodWindPart):
    _name = ki18n("Clarinet")
    instrumentNames = I18N_NOOP("Clarinet|Cl.")
    midiInstrument = 'clarinet'
    transposition = (-1, 6, -1)


class SopraninoSax(WoodWindPart):
    _name = ki18n("Sopranino Sax")
    instrumentNames = I18N_NOOP("Sopranino Sax|SiSx.")
    midiInstrument = 'soprano sax'
    transposition = (0, 2, -1)    # es'


class SopranoSax(WoodWindPart):
    _name = ki18n("Soprano Sax")
    instrumentNames = I18N_NOOP("Soprano Sax|SoSx.")
    midiInstrument = 'soprano sax'
    transposition = (-1, 6, -1)   # bes


class AltoSax(WoodWindPart):
    _name = ki18n("Alto Sax")
    instrumentNames = I18N_NOOP("Alto Sax|ASx.")
    midiInstrument = 'alto sax'
    transposition = (-1, 2, -1)   # es


class TenorSax(WoodWindPart):
    _name = ki18n("Tenor Sax")
    instrumentNames = I18N_NOOP("Tenor Sax|TSx.")
    midiInstrument = 'tenor sax'
    transposition = (-2, 6, -1)   # bes,


class BaritoneSax(WoodWindPart):
    _name = ki18n("Baritone Sax")
    instrumentNames = I18N_NOOP("Baritone Sax|BSx.")
    midiInstrument = 'baritone sax'
    transposition = (-2, 2, -1)   # es,


class BassSax(WoodWindPart):
    _name = ki18n("Bass Sax")
    instrumentNames = I18N_NOOP("Bass Sax|BsSx.")
    midiInstrument = 'baritone sax'
    transposition = (-3, 6, -1)   # bes,,


class SopranoRecorder(WoodWindPart):
    _name = ki18n("Soprano recorder")
    instrumentNames = I18N_NOOP("Soprano recorder|S.rec.")
    midiInstrument = 'recorder'
    transposition = (1, 0, 0)


class AltoRecorder(WoodWindPart):
    _name = ki18n("Alto recorder")
    instrumentNames = I18N_NOOP("Alto recorder|A.rec.")
    midiInstrument = 'recorder'


class TenorRecorder(WoodWindPart):
    _name = ki18n("Tenor recorder")
    instrumentNames = I18N_NOOP("Tenor recorder|T.rec.")
    midiInstrument = 'recorder'


class BassRecorder(WoodWindPart):
    _name = ki18n("Bass recorder")
    instrumentNames = I18N_NOOP("Bass recorder|B.rec.")
    midiInstrument = 'recorder'
    clef = 'bass'
    octave = -1


class HornF(BrassPart):
    _name = ki18n("Horn in F")
    instrumentNames = I18N_NOOP("Horn in F|Hn.F.")
    midiInstrument = 'french horn'
    transposition = (-1, 3, 0)


class TrumpetC(BrassPart):
    _name = ki18n("Trumpet in C")
    instrumentNames = I18N_NOOP("Trumpet in C|Tr.C")
    midiInstrument = 'trumpet'


class TrumpetBb(TrumpetC):
    _name = ki18n("Trumpet in Bb")
    instrumentNames = I18N_NOOP("Trumpet in Bb|Tr.Bb")
    transposition = (-1, 6, -1)


class Trombone(BrassPart):
    _name = ki18n("Trombone")
    instrumentNames = I18N_NOOP("Trombone|Trb.")
    midiInstrument = 'trombone'
    clef = 'bass'
    octave = -1


class Tuba(BrassPart):
    _name = ki18n("Tuba")
    instrumentNames = I18N_NOOP("Tuba|Tb.")
    midiInstrument = 'tuba'
    transposition = (-2, 6, -1)


class BassTuba(BrassPart):
    _name = ki18n("Bass Tuba")
    instrumentNames = I18N_NOOP("Bass Tuba|B.Tb.")
    midiInstrument = 'tuba'
    transposition = (-2, 0, 0)
    clef = 'bass'
    octave = -1


class SopranoVoice(VocalSoloPart):
    _name = ki18n("Soprano")
    instrumentNames = I18N_NOOP("Soprano|S.")


class MezzoSopranoVoice(VocalSoloPart):
    _name = ki18n("Mezzo soprano")
    instrumentNames = I18N_NOOP("Mezzo-soprano|Ms.")


class AltoVoice(VocalSoloPart):
    _name = ki18n("Alto")
    instrumentNames = I18N_NOOP("Alto|A.")
    octave = 0


class TenorVoice(VocalSoloPart):
    _name = ki18n("Tenor")
    instrumentNames = I18N_NOOP("Tenor|T.")
    octave = 0
    clef = 'treble_8'


class BassVoice(VocalSoloPart):
    _name = ki18n("Bass")
    instrumentNames = I18N_NOOP("Bass|B.")
    octave = -1
    clef = 'bass'


class LeadSheet(VocalPart, Chords):
    _name = ki18n("Lead sheet")

    def build(self, builder):
        """
        Create chord names, song and lyrics.
        Optional a second staff with a piano accompaniment.
        """
        if self.chords.isChecked():
            Chords.build(self, builder)
        if self.accomp.isChecked():
            p = ChoirStaff()
            #TODO: instrument names ?
            #TODO: different midi instrument for voice and accompaniment ?
            s = Sim(p)
            mel = Sim(Staff(parent=s))
            v1 = Voice(parent=mel)
            s1 = Seq(v1)
            Text('\\voiceOne', s1)
            stub, ref = self.assignMusic('melody', 1)
            Identifier(ref, s1)
            s2 = Seq(Voice(parent=mel))
            Text('\\voiceTwo', s2)
            stub, ref = self.assignMusic('accRight', 0)
            Identifier(ref, s2)
            acc = Seq(Staff(parent=s))
            Clef('bass', acc)
            stub, ref = self.assignMusic('accLeft', -1)
            Identifier(ref, acc)
            if self.ambitus.isChecked():
                # We can't use \addlyrics when the voice has a \with {}
                # section, because it creates a nested Voice context.
                # So if the ambitus engraver should be added to the Voice,
                # we don't use \addlyrics but create a new Lyrics context.
                # So in that case we don't use addStanzas, but insert the
                # Lyrics contexts manually inside our ChoirStaff.
                v1.cid = Reference('melody')
                Line('\\consists "Ambitus_engraver"', v1.getWith())
                count = self.stanzas.value() # number of stanzas
                if count == 1:
                    l = Lyrics()
                    s.insert(acc.parent(), l)
                    ref = self.assignLyrics('verse')
                    Identifier(ref, LyricsTo(v1.cid, l))
                else:
                    for i in range(count):
                        l = Lyrics()
                        s.insert(acc.parent(), l)
                        ref = self.assignLyrics('verse', i + 1)
                        Identifier(ref, LyricsTo(v1.cid, l))
            else:
                self.addStanzas(v1)
        else:
            stub, ref = self.assignMusic('melody', 1)
            p = Staff()
            Identifier(ref, Seq(p))
            self.addStanzas(p)
            if self.ambitus.isChecked():
                Line('\\consists "Ambitus_engraver"', p.getWith())
        self.nodes.append(p)

    def widgets(self, layout):
        l = QLabel('<i>{0}</i>'.format(i18n(
            "The Lead Sheet provides a staff with chord names above "
            "and lyrics below it. A second staff is optional.")))
        l.setWordWrap(True)
        layout.addWidget(l)
        self.chords = QGroupBox(i18n("Chord names"))
        self.chords.setCheckable(True)
        self.chords.setChecked(True)
        layout.addWidget(self.chords)
        l = QVBoxLayout()
        self.chords.setLayout(l)
        Chords.widgets(self, l)
        self.accomp = QCheckBox(i18n("Add accompaniment staff"))
        self.accomp.setToolTip(i18n(
            "Adds an accompaniment staff and also puts an accompaniment "
            "voice in the upper staff."))
        layout.addWidget(self.accomp)
        VocalPart.widgets(self, layout)


class Choir(VocalPart):
    _name = ki18n("Choir")

    def widgets(self, layout):
        l = QLabel('<p>{0} <i>({1})</i></p>'.format(
            i18n("Please select the voices for the choir. "
            "Use the letters S, A, T, or B. A hyphen denotes a new staff."),
            i18n("Hint: For a double choir you can use two choir parts.")))
        l.setWordWrap(True)
        layout.addWidget(l)
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Voicing:"), h)
        self.voicing = QComboBox(h)
        l.setBuddy(self.voicing)
        self.voicing.setEditable(True)
        self.voicing.setCompleter(None)
        self.voicing.setValidator(QRegExpValidator(
            QRegExp("[SATB]+(-[SATB]+)*", Qt.CaseInsensitive), self.voicing))
        self.voicing.addItems((
            'SA-TB', 'S-A-T-B',
            'SA', 'S-A', 'SS-A', 'S-S-A',
            'TB', 'T-B', 'TT-B', 'T-T-B',
            'SS-A-T-B', 'S-A-TT-B', 'SS-A-TT-B',
            'S-S-A-T-T-B', 'S-S-A-A-T-T-B-B',
            ))
        self.stanzaWidget(layout)
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Lyrics:"), h)
        self.lyrics = QComboBox(h)
        l.setBuddy(self.lyrics)
        for index, (text, tooltip) in enumerate((
         (i18n("All voices same lyrics"),
          i18n("One set of the same lyrics is placed between all staves.")),
         (i18n("Every voice same lyrics"),
          i18n("Every voice gets its own lyrics, using the same text as the"
               " other voices.")),
         (i18n("Every voice different lyrics"),
          i18n("Every voice gets a different set of lyrics.")),
         (i18n("Distribute stanzas"),
          i18n("All voices share the same lyrics, but the stanzas are "
               "distributed across the staves.\nThis is useful if you want to "
               "engrave e.g. four-part songs with many stanzas.")))):
            self.lyrics.addItem(text)
            self.lyrics.setItemData(index, tooltip, Qt.ToolTipRole)
        self.lyrics.setCurrentIndex(0)
        self.ambitusWidget(layout)
        self.pianoReduction = QCheckBox(i18n("Piano reduction"))
        self.pianoReduction.setToolTip(i18n(
            "Adds an automatically generated piano reduction."))
        layout.addWidget(self.pianoReduction)
        self.rehearsalMidi = QCheckBox(i18n("Rehearsal MIDI files"))
        self.rehearsalMidi.setToolTip(i18n(
            "Creates a rehearsal MIDI file for every voice, "
            "even if no MIDI output is generated for the main score."))
        layout.addWidget(self.rehearsalMidi)

    identifiers = {
        'S': 'soprano',
        'A': 'alto',
        'T': 'tenor',
        'B': 'bass',
    }
    
    octaves = {
        'S': SopranoVoice.octave,
        'A': AltoVoice.octave,
        'T': TenorVoice.octave,
        'B': BassVoice.octave,
    }
    
    instrumentNames = {
        'S': SopranoVoice.instrumentNames,
        'A': AltoVoice.instrumentNames,
        'T': TenorVoice.instrumentNames,
        'B': BassVoice.instrumentNames,
    }
            
    def build(self, builder):
        # normalize voicing
        staves = self.voicing.currentText().upper()
        # remove unwanted characters
        staves = re.sub(r'[^SATB-]+', '', staves)
        # remove double hyphens, and from begin and end
        staves = re.sub('-+', '-', staves).strip('-')
        if not staves:
            return
        splitStaves = staves.split('-')
        p = ChoirStaff()
        choir = Sim(p)
        self.nodes.append(p)
        # print main instrumentName if there are more choirs, and we
        # have more than one staff.
        if len(splitStaves) > 1 and self.num:
            builder.setInstrumentNames(p, I18N_NOOP("Choir|Ch."), self.num)
        
        count = defaultdict(int)  # dict with count of voices.
        maxLen = max(map(len, splitStaves))
        toGo = max(2, len(splitStaves)) # nr staves with same lyrics below + 1
        staffNames = defaultdict(int)
        if self.stanzas.value() == 1:
            stanzas = [0]
        else:
            stanzas = list(range(1, self.stanzas.value() + 1))
        
        # group lyric assignments by stanza number
        lyr = dict((k, []) for k in stanzas)
        
        lyrAllSame, lyrEachSame, lyrEachDiff, lyrSpread = (
            self.lyrics.currentIndex() == i for i in range(4))
        
        pianoReduction = defaultdict(list)
        rehearsalMidis = []

        for staff in splitStaves:
            toGo -= 1
            # sort the letters in order SATB
            staff = ''.join(i * staff.count(i) for i in 'SATB')
            # Create the staff for the voices
            s = Staff(parent=choir)
            builder.setMidiInstrument(s, self.midiInstrument)
            
            # Build a list of the voices in this staff. Each entry is a
            # tuple(name, num).
            # name is one of 'S', 'A', 'T', or 'B'
            # num is an integer: 0 when a voice occurs only once, or >= 1 when
            # there are more voices of the same type (e.g. Soprano I and II)
            voices = []
            for voice in staff:
                if staves.count(voice) > 1:
                    count[voice] += 1
                voices.append((voice, count[voice]))
            
            # Add the instrument names to the staff:
            if len(staff) == 1:
                # There is only one voice in the staff. Just set the instrument
                # name directly in the staff.
                voice, num = voices[0]
                builder.setInstrumentNames(s, self.instrumentNames[voice], num)
                # if *all* staves have only one voice, addlyrics is used.
                # In that case, don't remove the braces.
                mus = Seq(s) if maxLen == 1 else Seqr(s)
            else:
                # There are more instrument names for the staff, stack them in
                # a markup column.
                def mkup(names):
                    n = Markup()
                    if builder.lilyPondVersion >= (2, 11, 57):
                        col = MarkupEnclosed('center-column', n)
                    else:
                        col = MarkupEnclosed('center-align', n)
                    for name in names:
                        QuotedString(name, col)
                    return n
                builder.setInstrumentNames(s, map(mkup, zip(*[
                  builder.getInstrumentNames(self.instrumentNames[voice], num)
                  for voice, num in voices])))
                mus = Simr(s)
            
            # Set the clef for this staff:
            if 'B' in staff:
                Clef('bass', mus)
            elif 'T' in staff:
                Clef('treble_8', mus)

            # Add the voices:
            if len(staff) == 1:
                voice, num = voices[0]
                name = self.identifiers[voice]
                if num:
                    name += ly.nums(num)
                stub, ref = self.assignMusic(name, self.octaves[voice])
                lyrName = name + 'Verse' if lyrEachDiff else 'verse'
                if maxLen == 1:
                    # if all staves have only one voice, use \addlyrics...
                    Identifier(ref, mus)
                    if toGo or not lyrAllSame:
                        for verse in stanzas:
                            lyr[verse].append((AddLyrics(s), lyrName))
                else:
                    # otherwise create explicit Voice and Lyrics contexts.
                    voiceName = self.identifiers[voice] + str(num or '')
                    v = Seqr(Voice(voiceName, parent=mus))
                    Identifier(ref, v)
                    if toGo or not lyrAllSame:
                        for verse in stanzas:
                            lyr[verse].append((LyricsTo(voiceName,
                                    Lyrics(parent=choir)), lyrName))
                if self.ambitus.isChecked():
                    Line('\\consists "Ambitus_engraver"', s.getWith())
                
                pianoReduction[voice].append(ref)
                rehearsalMidis.append((voice, num, ref, lyrName))
                
            else:
                # There is more than one voice in the staff.
                # Determine their order (\voiceOne, \voiceTwo etc.)
                if len(staff) == 2:
                    order = 1, 2
                elif staff in ('SSA', 'TTB'):
                    order = 1, 3, 2
                elif staff in ('SAA', 'TBB'):
                    order = 1, 2, 4
                elif staff in ('SSAA', 'TTBB'):
                    order = 1, 3, 2, 4
                else:
                    order = range(1, len(staff) + 1)
                
                # What name would the staff get if we need to refer to it?
                # if a name (like 's' or 'sa') is already in use in this part,
                # just add a number ('ss2' or 'sa2', etc.)
                staffNames[staff] += 1
                if staffNames[staff] > 1:
                    staff += str(staffNames[staffName])
                # We want the staff name (actually context-id) in lower case.
                staffRef = Reference(staff.lower())
                
                # Create the voices and their lyrics.
                for (voice, num), voiceNum in zip(voices, order):
                    name = self.identifiers[voice]
                    if num:
                        name += ly.nums(num)
                    voiceName = self.identifiers[voice] + str(num or '')
                    v = Voice(voiceName, parent=mus)
                    # Add ambitus to voice, move to the right if necessary
                    if self.ambitus.isChecked():
                        Line('\\consists "Ambitus_engraver"', v.getWith())
                        if voiceNum > 1:
                            Line("\\override Ambitus #'X-offset = #{0}".format(
                                 (voiceNum - 1) * 2.0), v.getWith())
                    v = Seq(v)
                    Text('\\voice' + ly.nums(voiceNum), v)
                    stub, ref = self.assignMusic(name, self.octaves[voice])
                    Identifier(ref, v)
                    
                    if lyrAllSame:
                        lyrName = 'verse'
                        above = False
                    elif lyrEachSame:
                        lyrName = 'verse'
                        above = vnum & 1
                    else: #lyrEachDiff
                        lyrName = mname + 'Verse'
                        above = vnum & 1
                    
                    pianoReduction[voice].append(ref)
                    rehearsalMidis.append((voice, num, ref, lyrName))
                    
                    if not lyrAllSame or (toGo and voiceNum == 1):
                        # Create the lyrics. If they should be above the staff,
                        # give the staff a suitable name, and use alignAbove-
                        # Context to align the Lyrics above the staff.
                        if above and s.cid is None:
                            s.cid = staffRef
                        for verse in stanzas:
                            l = Lyrics(parent=choir)
                            if above:
                                l.getWith()['alignAboveContext'] = s.cid
                                if builder.lilyPondVersion >= (2, 13, 4):
                                    Line("\\override VerticalAxisGroup "
                                      "#'staff-affinity = #DOWN", l.getWith())
                            lyr[verse].append((LyricsTo(voiceName, l), lyrName))

        # Assign the lyrics, so their definitions come after the note defs.
        # (These refs are used again below in the midi rehearsal routine.)
        refs = {}
        for verse in stanzas:
            for node, name in lyr[verse]:
                if (name, verse) not in refs:
                    refs[(name, verse)] = self.assignLyrics(name, verse)
                Identifier(refs[(name, verse)], node)

        # Create the piano reduction if desired
        if self.pianoReduction.isChecked():
            a, ref = self.assign('pianoReduction')
            self.nodes.append(Identifier(ref))
            piano = PianoStaff(parent=a)
            
            sim = Sim(piano)
            rightStaff = Staff(parent=sim)
            leftStaff = Staff(parent=sim)
            right = Seq(rightStaff)
            left = Seq(leftStaff)
            
            # Determine the ordering of voices in the staves
            upper = pianoReduction['S'] + pianoReduction['A']
            lower = pianoReduction['T'] + pianoReduction['B']
            
            preferUpper = 1
            if not upper:
                # Male choir
                upper = pianoReduction['T']
                lower = pianoReduction['B']
                Clef("treble_8", right)
                Clef("bass", left)
                preferUpper = 0
            elif not lower:
                # Female choir
                upper = pianoReduction['S']
                lower = pianoReduction['A']
            else:
                Clef("bass", left)

            # Otherwise accidentals can be confusing
            Line("#(set-accidental-style 'piano)", right)
            Line("#(set-accidental-style 'piano)", left)
            
            # Move voices if unevenly spread
            if abs(len(upper) - len(lower)) > 1:
                voices = upper + lower
                half = (len(voices) + preferUpper) / 2
                upper = voices[:half]
                lower = voices[half:]
            
            for staff, voices in (Simr(right), upper), (Simr(left), lower):
                if voices:
                    for v in voices[:-1]:
                        Identifier(v, staff)
                        VoiceSeparator(staff).after = 1
                    Identifier(voices[-1], staff)

            # Make the piano part somewhat smaller
            Line("fontSize = #-1", piano.getWith())
            Line("\\override StaffSymbol #'staff-space = #(magstep -1)",
                piano.getWith())
            
            # Nice to add Mark engravers
            Line('\\consists "Mark_engraver"', rightStaff.getWith())
            Line('\\consists "Metronome_mark_engraver"', rightStaff.getWith())
            
            # Keep piano reduction out of the MIDI output
            if builder.midi:
                Line('\\remove "Staff_performer"', rightStaff.getWith())
                Line('\\remove "Staff_performer"', leftStaff.getWith())
        
        # Create MIDI files if desired
        if self.rehearsalMidi.isChecked():
            builder.book = True # force \book { } block

            a, rehearsalMidi = self.assign('rehearsalMidi')
            
            func = SchemeList(a)
            func.pre = '#(' # hack
            Text('define-music-function', func)
            Line('(parser location name midiInstrument lyrics) '
                 '(string? string? ly:music?)', func)
            choir = Sim(Command('unfoldRepeats', SchemeLily(func)))
            
            self.aftermath.append(Comment(i18n("Rehearsal MIDI files:")))
            
            for voice, num, ref, lyrName in rehearsalMidis:
                # Append voice to the rehearsalMidi function
                name = self.identifiers[voice] + str(num or '')
                seq = Seq(Voice(name, parent=Staff(name, parent=choir)))
                Text('s1*0\\f', seq) # add one dynamic
                Identifier(ref, seq) # add the reference to the voice
                
                # Append score to the aftermath (stuff put below the main score)
                if self.num:
                    suffix = "choir{0}-{1}".format(self.num, name)
                else:
                    suffix = name
                self.aftermath.append(
                    Line('#(define output-suffix "{0}")'.format(suffix)))
                book = Book()
                self.aftermath.append(book)
                self.aftermath.append(BlankLine())
                score = Score(book)
                
                # TODO: make configurable
                if voice in ('SA'):
                    midiInstrument = "soprano sax"
                else:
                    midiInstrument = "tenor sax"

                cmd = Command(rehearsalMidi, score)
                QuotedString(name, cmd)
                QuotedString(midiInstrument, cmd)
                Identifier(refs[(lyrName, stanzas[0])], cmd)
                Midi(score)
            
            Text("\\context Staff = $name", choir)
            seq = Seq(choir)
            Line("\\set Score.midiMinimumVolume = #0.5", seq)
            Line("\\set Score.midiMaximumVolume = #0.5", seq)
            Line("\\set Score.tempoWholesPerMinute = #" + builder.getMidiTempo(), seq)
            Line("\\set Staff.midiMinimumVolume = #0.8", seq)
            Line("\\set Staff.midiMaximumVolume = #1.0", seq)
            Line("\\set Staff.midiInstrument = $midiInstrument", seq)
            lyr = Lyrics(parent=choir)
            lyr.getWith()['alignBelowContext'] = Text('$name')
            Text("\\lyricsto $name $lyrics", lyr)


class Piano(KeyboardPart):
    _name = ki18n("Piano")
    instrumentNames = I18N_NOOP("Piano|Pno.")
    midiInstrument = 'acoustic grand'


class Harpsichord(KeyboardPart):
    _name = ki18n("Harpsichord")
    instrumentNames = I18N_NOOP("Harpsichord|Hs.")
    midiInstrument = 'harpsichord'


class Clavichord(KeyboardPart):
    _name = ki18n("Clavichord")
    instrumentNames = I18N_NOOP("Clavichord|Clv.")
    midiInstrument = 'clav'


class Organ(KeyboardPart):
    _name = ki18n("Organ")
    instrumentNames = I18N_NOOP("Organ|Org.")
    midiInstrument = 'church organ'

    def widgets(self, layout):
        super(Organ, self).widgets(layout)
        self.pedalVoices = voicesWidget(layout, i18n("Pedal:"), 0,
            tooltip=i18n("Set to 0 to disable the pedal altogether."))

    def build(self, builder):
        super(Organ, self).build(builder)
        if self.pedalVoices.value():
            self.nodes.append(self.buildStaff(builder,
                'pedal', -1, self.pedalVoices.value(), clef="bass"))


class Celesta(KeyboardPart):
    _name = ki18n("Celesta")
    instrumentNames = I18N_NOOP("Celesta|Cel.")
    midiInstrument = 'celesta'


class Timpani(PitchedPercussionPart):
    _name = ki18n("Timpani")
    instrumentNames = I18N_NOOP("Timpani|Tmp.")
    midiInstrument = 'timpani'
    clef = 'bass'
    octave = -1


class Xylophone(PitchedPercussionPart):
    _name = ki18n("Xylophone")
    instrumentNames = I18N_NOOP("Xylophone|Xyl.")
    midiInstrument = 'xylophone'


class Marimba(PitchedPercussionPart):
    _name = ki18n("Marimba")
    instrumentNames = I18N_NOOP("Marimba|Mar.")
    midiInstrument = 'marimba'


class Vibraphone(PitchedPercussionPart):
    _name = ki18n("Vibraphone")
    instrumentNames = I18N_NOOP("Vibraphone|Vib.")
    midiInstrument = 'vibraphone'


class TubularBells(PitchedPercussionPart):
    _name = ki18n("Tubular bells")
    instrumentNames = I18N_NOOP("Tubular bells|Tub.")
    midiInstrument = 'tubular bells'


class Glockenspiel(PitchedPercussionPart):
    _name = ki18n("Glockenspiel")
    instrumentNames = I18N_NOOP("Glockenspiel|Gls.")
    midiInstrument = 'glockenspiel'


class Drums(Part):
    _name = ki18n("Drums")
    instrumentNames = I18N_NOOP("Drums|Dr.")

    def assignDrums(self, name = None):
        """
        Creates an empty name = \drummode assignment and returns
        the reference for the name.
        """
        a, ref = self.assign(name)
        s = DrumMode(a)
        Identifier('global', s)
        LineComment(i18n("Drums follow here."), s)
        BlankLine(s)
        return ref

    def build(self, builder):
        p = DrumStaff()
        s = Simr(p)
        if self.drumVoices.value() > 1:
            for i in range(1, self.drumVoices.value()+1):
                q = Seq(DrumVoice(parent=s))
                Text('\\voice' + ly.nums(i), q)
                ref = self.assignDrums('drum' + ly.nums(i))
                Identifier(ref, q)
        else:
            ref = self.assignDrums('drum')
            Identifier(ref, s)
        builder.setInstrumentNames(p, self.instrumentNames, self.num)
        i = self.drumStyle.currentIndex()
        if i > 0:
            v = ('drums', 'timbales', 'congas', 'bongos', 'percussion')[i]
            p.getWith()['drumStyleTable'] = Scheme(v + '-style')
            v = (5, 2, 2, 2, 1)[i]
            Line("\\override StaffSymbol #'line-count = #{0}".format(v), p.getWith())
        if self.drumStems.isChecked():
            Line("\\override Stem #'stencil = ##f", p.getWith())
            Line("\\override Stem #'length = #3  % " + i18n("keep some distance."),
                p.getWith())
        self.nodes.append(p)

    def widgets(self, layout):
        self.drumVoices = voicesWidget(layout)
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Style:"), h)
        self.drumStyle = QComboBox(h)
        l.setBuddy(self.drumStyle)
        self.drumStyle.addItems((
            i18n("Drums (5 lines, default)"),
            i18n("Timbales-style (2 lines)"),
            i18n("Congas-style (2 lines)"),
            i18n("Bongos-style (2 lines)"),
            i18n("Percussion-style (1 line)")))
        self.drumStems = QCheckBox(i18n("Remove stems"))
        self.drumStems.setToolTip(i18n("Remove the stems from the drum notes."))
        layout.addWidget(self.drumStems)




# The structure of the overview
def categories():
    return (
        (i18n("Strings"), (
                Violin,
                Viola,
                Cello,
                Contrabass,
                BassoContinuo,
            )),
        (i18n("Plucked strings"), (
                Mandolin,
                Banjo,
                ClassicalGuitar,
                JazzGuitar,
                Bass,
                ElectricBass,
                Harp,
            )),
        (i18n("Woodwinds"), (
                Flute,
                Piccolo,
                BassFlute,
                Oboe,
                OboeDAmore,
                EnglishHorn,
                Bassoon,
                ContraBassoon,
                Clarinet,
                SopraninoSax,
                SopranoSax,
                AltoSax,
                TenorSax,
                BaritoneSax,
                BassSax,
                SopranoRecorder,
                AltoRecorder,
                TenorRecorder,
                BassRecorder,
            )),
        (i18n("Brass"), (
                HornF,
                TrumpetC,
                TrumpetBb,
                Trombone,
                Tuba,
                BassTuba,
            )),
        (i18n("Vocal"), (
                LeadSheet,
                SopranoVoice,
                MezzoSopranoVoice,
                AltoVoice,
                TenorVoice,
                BassVoice,
                Choir,
            )),
        (i18n("Keyboard instruments"), (
                Piano,
                Harpsichord,
                Clavichord,
                Organ,
                Celesta,
            )),
        (i18n("Percussion"), (
                Timpani,
                Xylophone,
                Marimba,
                Vibraphone,
                TubularBells,
                Glockenspiel,
                Drums,
            )),
        (i18n("Special"), (
                Chords,
                BassFigures,
            )),
    )
