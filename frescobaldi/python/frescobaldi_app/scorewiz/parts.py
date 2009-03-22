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
Part types for the Score Wizard (scorewiz/__init__.py).
In separate file to ease maintenance.
"""

from PyQt4.QtCore import QObject, SIGNAL
from PyQt4.QtGui import (
    QCheckBox, QComboBox, QGroupBox, QLabel, QRadioButton, QSpinBox,
    QVBoxLayout)
from PyKDE4.kdecore import i18n, ki18n
from PyKDE4.kdeui import KHBox, KVBox

import ly
from ly.dom import *
import frescobaldi_app.scorewiz

I18N_NOOP = lambda s: s

# Base classes for the part types in this file.
# (For the real part type classes see below.)


class Part(frescobaldi_app.scorewiz.PartBase):
    """
    The base class for our part types.
    Adds some convenience methods for often used tasks.
    """
    def assign(self, node, stub, nameref=None):
        """
        Creates an assignment for the stub under the given name.
        Adds an identifier to the given node.
        nameref can be a string name or a Reference object.

        If the nameref is empty or None, the identifier() will be used,
        with the first letter lowered.
        """
        if not nameref:
            nameref = Reference(self.identifier())
        elif not isinstance(nameref, Reference):
            nameref = Reference(nameref)
        # handle multiple references to the same assignment
        for a in self.assignments:
            if a.name.name == nameref.name:
                nameref = a.name
                break
        else:
            a = Assignment(nameref)
            a.append(stub)
            self.assignments.append(a)
        Identifier(nameref, node)

    def assignMusic(self, node, octave, transpose=None, name=None):
        """
        Creates a \\relative stub and an assignment for it.
        Returns the contents of the stub for other possible manipulations.
        """
        stub = Relative()
        Pitch(octave, 0, 0, stub)
        s = Seq(stub)
        Identifier('global', s).after = 1
        if transpose is not None:
            toct, tnote, talter = transpose
            Pitch(toct, tnote, Rational(talter, 2), Transposition(s))
        LineComment(i18n("Music follows here."), s)
        BlankLine(s)
        self.assign(node, stub, name)
        return s


class SingleVoicePart(Part):
    """
    The abstract base class for single voice part types.
    The build function just creates one staff with one voice,
    and uses the .clef, .transpose, .midiInstrument and .instrumentNames
    class (or instance) attributes.
    """

    # A subclass could set a clef for the staff (e.g. "bass")
    clef = None

    # The octave for the \relative command
    octave = 1

    # A subclass could set a transposition here.
    transpose = None

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
        staff = Staff()
        builder.setInstrumentNames(staff, self.instrumentNames, self.num)
        builder.setMidiInstrument(staff, self.midiInstrument)
        s1 = braces and Seq(staff) or Seqr(staff)
        if self.clef:
            Clef(self.clef, s1)
        stub = self.assignMusic(s1, self.octave, self.transpose)
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
            QObject.connect(self.staffType, SIGNAL("activated(int)"),
                self.slotTabEnable)
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

    def build(self, builder):
        t = self.staffType.currentIndex()
        if t == 0:
            # normal staff only
            return super(TablaturePart, self).build(builder)

        # make a tabstaff
        tab = TabStaff()
        if self.tabFormat:
            tab.getWith()['tablatureFormat'] = Scheme(self.tabFormat)
        self.setTunings(tab)
        s = Seqr(tab)
        ref = Reference(self.identifier())
        self.assignMusic(s, self.octave, self.transpose, name=ref)
        if t == 1:  # only a TabStaff
            builder.setMidiInstrument(tab, self.midiInstrument)
            p = tab
        else:       # both TabStaff and normal staff
            p = StaffGroup()
            s = Sim(p)
            m = Seqr(Staff(parent=s))
            s.append(tab)
            builder.setMidiInstrument(m.parent(), self.midiInstrument)
            if self.clef:
                Clef(self.clef, m)
            Identifier(ref, m)
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

    def assignLyrics(self, node, name, verse = 0):
        l = LyricMode()
        if verse:
            name = name + ly.nums(verse)
            Line('\\set stanza = "%d."' % verse, l)
        LineComment(i18n("Lyrics follow here."), l)
        BlankLine(l)
        self.assign(node, l, name)

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
        Add stanzas in self.stanzas.value() to the (Voice) node
        using \\addlyrics.
        """
        if self.stanzas.value() == 1:
            self.assignLyrics(AddLyrics(node), 'verse')
        else:
            for i in range(self.stanzas.value()):
                self.assignLyrics(AddLyrics(node), 'verse', i + 1)


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
            self.assignMusic(c, octave, name=name)
        else:
            c = Sim(c)
            for i in range(1, numVoices):
                self.assignMusic(c, octave, name=name + ly.nums(i))
                VoiceSeparator(c)
            self.assignMusic(c, octave, name=name + ly.nums(numVoices))
        return staff

    def build(self, builder):
        """ setup structure for a 2-staff PianoStaff. """
        p = PianoStaff()
        builder.setInstrumentNames(p, self.instrumentNames, self.num)
        s = Sim(p)
        # add two staves, with a respective number of voices.
        self.buildStaff(builder, 'right', 1, self.rightVoices.value(), s)
        self.buildStaff(builder, 'left', 0, self.leftVoices.value(), s, "bass")
        self.nodes.append(p)

    def widgets(self, layout):
        l = QLabel('%s <i>(%s)</i>' % (
            i18n("Adjust how many separate voices you want on each staff."),
            i18n("This is primarily useful when you write polyphonic music "
            "like a fuge.")))
        l.setWordWrap(True)
        layout.addWidget(l)
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Right hand:"), h)
        self.rightVoices = QSpinBox(h)
        self.rightVoices.setRange(1, 4)
        l.setBuddy(self.rightVoices)
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Left hand:"), h)
        self.leftVoices = QSpinBox(h)
        self.leftVoices.setRange(1, 4)
        l.setBuddy(self.leftVoices)


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
        s = ChordMode()
        name = Reference('chordNames')
        Identifier('global', s).after = 1
        i = self.chordStyle.currentIndex()
        if i > 0:
            Line('\\%sChords' %
                ('german', 'semiGerman', 'italian', 'french')[i-1], s)
        LineComment(i18n("Chords follow here."), s)
        BlankLine(s)
        self.assign(p, s, name)
        self.nodes.append(p)
        if self.guitarFrets.isChecked():
            f = FretBoards()
            Identifier(name, f)
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
        p = FiguredBass()
        s = FigureMode()
        Identifier('global', s)
        LineComment(i18n("Figures follow here."), s)
        BlankLine(s)
        self.assign(p, s, 'figBass')
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
        self.assignMusic(s, self.octave, self.transpose, 'bcMusic')
        b = FigureMode()
        Identifier('global', b)
        Line("\\override Staff.BassFigureAlignmentPositioning "
             "#'direction = #DOWN", b)
        LineComment(i18n("Figures follow here."), b)
        BlankLine(b)
        self.assign(s, b, 'bcFigures')
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
                '(four-string-banjo %s)' %
                    self.tunings[self.tuningSel.currentIndex()][1])


class ClassicalGuitar(TablaturePart):
    _name = ki18n("Classical guitar")
    instrumentNames = I18N_NOOP("Guitar|Gt.")
    midiInstrument = 'acoustic guitar (nylon)'
    clef = "treble_8"
    tunings = (
        (ki18n("Guitar tuning"), 'guitar-tuning'),
        (ki18n("Open G-tuning"), 'guitar-open-g-tuning'),
    )


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
        """ setup structure for 2 staves. """
        p = PianoStaff()
        builder.setInstrumentNames(p, self.instrumentNames, self.num)
        s = Sim(p)
        # add two staves, with one voice each.
        self.buildStaff(builder, 'upper', 1, 1, s)
        self.buildStaff(builder, 'lower', 0, 1, s, "bass")
        self.nodes.append(p)

    def widgets(self, layout):
        """ don't display the voice widgets of the KeyboardPart """
        super(KeyboardPart, self).widgets(layout)


class Flute(WoodWindPart):
    _name = ki18n("Flute")
    instrumentNames = I18N_NOOP("Flute|Fl.")
    midiInstrument = 'flute'


class Piccolo(WoodWindPart):
    _name = ki18n("Piccolo")
    instrumentNames = I18N_NOOP("Piccolo|Pic.")
    midiInstrument = 'piccolo'
    transpose = (1, 0, 0)


class BassFlute(WoodWindPart):
    _name = ki18n("Bass flute")
    instrumentNames = I18N_NOOP("Bass flute|Bfl.")
    midiInstrument = 'flute'
    transpose = (-1, 4, 0)


class Oboe(WoodWindPart):
    _name = ki18n("Oboe")
    instrumentNames = I18N_NOOP("Oboe|Ob.")
    midiInstrument = 'oboe'


class OboeDAmore(WoodWindPart):
    _name = ki18n("Oboe d'Amore")
    instrumentNames = I18N_NOOP("Oboe d'amore|Ob.d'am.")
    midiInstrument = 'oboe'
    transpose = (-1, 5, 0)


class EnglishHorn(WoodWindPart):
    _name = ki18n("English Horn")
    instrumentNames = I18N_NOOP("English horn|Eng.h.")
    midiInstrument = 'english horn'
    transpose = (-1, 3, 0)


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
    transpose = (-1, 0, 0)
    clef = 'bass'
    octave = -1


class Clarinet(WoodWindPart):
    _name = ki18n("Clarinet")
    instrumentNames = I18N_NOOP("Clarinet|Cl.")
    midiInstrument = 'clarinet'
    transpose = (-1, 6, -1)


class SopraninoSax(WoodWindPart):
    _name = ki18n("Sopranino Sax")
    instrumentNames = I18N_NOOP("Sopranino Sax|SiSx.")
    midiInstrument = 'soprano sax'
    transpose = (0, 2, -1)    # es'


class SopranoSax(WoodWindPart):
    _name = ki18n("Soprano Sax")
    instrumentNames = I18N_NOOP("Soprano Sax|SoSx.")
    midiInstrument = 'soprano sax'
    transpose = (-1, 6, -1)   # bes


class AltoSax(WoodWindPart):
    _name = ki18n("Alto Sax")
    instrumentNames = I18N_NOOP("Alto Sax|ASx.")
    midiInstrument = 'alto sax'
    transpose = (-1, 2, -1)   # es


class TenorSax(WoodWindPart):
    _name = ki18n("Tenor Sax")
    instrumentNames = I18N_NOOP("Tenor Sax|TSx.")
    midiInstrument = 'tenor sax'
    transpose = (-2, 6, -1)   # bes,


class BaritoneSax(WoodWindPart):
    _name = ki18n("Baritone Sax")
    instrumentNames = I18N_NOOP("Baritone Sax|BSx.")
    midiInstrument = 'baritone sax'
    transpose = (-2, 2, -1)   # es,


class BassSax(WoodWindPart):
    _name = ki18n("Bass Sax")
    instrumentNames = I18N_NOOP("Bass Sax|BsSx.")
    midiInstrument = 'baritone sax'
    transpose = (-3, 6, -1)   # bes,,


class SopranoRecorder(WoodWindPart):
    _name = ki18n("Soprano recorder")
    instrumentNames = I18N_NOOP("Soprano recorder|S.rec.")
    midiInstrument = 'recorder'
    transpose = (1, 0, 0)


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
    transpose = (-1, 3, 0)


class TrumpetC(BrassPart):
    _name = ki18n("Trumpet in C")
    instrumentNames = I18N_NOOP("Trumpet in C|Tr.C")
    midiInstrument = 'trumpet'


class TrumpetBb(TrumpetC):
    _name = ki18n("Trumpet in Bb")
    instrumentNames = I18N_NOOP("Trumpet in Bb|Tr.Bb")
    transpose = (-1, 6, -1)


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
    transpose = (-2, 6, -1)


class BassTuba(BrassPart):
    _name = ki18n("Bass Tuba")
    instrumentNames = I18N_NOOP("Bass Tuba|B.Tb.")
    midiInstrument = 'tuba'
    transpose = (-2, 0, 0)
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
            Line('\\voiceOne', s1)
            self.assignMusic(s1, 1, name='melody')
            s2 = Seq(Voice(parent=mel))
            Line('\\voiceTwo', s2)
            self.assignMusic(s2, 0, name='accRight')
            acc = Seq(Staff(parent=s))
            Clef('bass', acc)
            self.assignMusic(acc, -1, name='accLeft')
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
                    self.assignLyrics(LyricsTo(v1.cid, l), 'verse')
                else:
                    for i in range(count):
                        l = Lyrics()
                        s.insert(acc.parent(), l)
                        self.assignLyrics(LyricsTo(v1.cid, l), 'verse', i + 1)
            else:
                self.addStanzas(v1)
        else:
            p = Staff()
            self.assignMusic(Seq(p), 1, name='melody')
            self.addStanzas(p)
            if self.ambitus.isChecked():
                Line('\\consists "Ambitus_engraver"', p.getWith())
        self.nodes.append(p)

    def widgets(self, layout):
        l = QLabel('<i>%s</i>' % i18n(
            "The Lead Sheet provides a staff with chord names above "
            "and lyrics below it. A second staff is optional."))
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
        l = QLabel('<p>%s</p><p><i>(%s)</i></p>' % (
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
        self.voicing.addItems((
            'SA-TB', 'S-A-T-B',
            'SA', 'S-A', 'SS-A', 'S-S-A',
            'TB', 'T-B', 'TT-B', 'T-T-B',
            'SS-A-T-B', 'S-A-TT-B', 'SS-A-TT-B',
            'S-S-A-T-T-B', 'S-S-A-A-T-T-B-B',
            ))
        g = QGroupBox(i18n("Lyrics"))
        layout.addWidget(g)
        group = QVBoxLayout()
        g.setLayout(group)
        self.lyrAllSame = QRadioButton(i18n("All voices same lyrics"))
        self.lyrAllSame.setChecked(True)
        self.lyrAllSame.setToolTip(i18n(
            "One set of the same lyrics is placed between all staves."))
        group.addWidget(self.lyrAllSame)
        self.lyrEachSame = QRadioButton(i18n("Every voice same lyrics"))
        self.lyrEachSame.setToolTip(i18n(
            "Every voice gets its own lyrics, using the same text as the "
            "other voices."))
        group.addWidget(self.lyrEachSame)
        self.lyrEachDiff = QRadioButton(i18n("Every voice different lyrics"))
        self.lyrEachDiff.setToolTip(i18n(
            "Every voice gets a different set of lyrics."))
        group.addWidget(self.lyrEachDiff)
        self.stanzaWidget(group)
        self.ambitusWidget(layout)

    partInfo = {
        'S': ('soprano', 1, SopranoVoice.instrumentNames),
        'A': ('alto', 0, AltoVoice.instrumentNames),
        'T': ('tenor', 0, TenorVoice.instrumentNames),
        'B': ('bass', -1, BassVoice.instrumentNames),
    }

    def build(self, builder):
        # normalize voicing
        staves = unicode(self.voicing.currentText()).upper()
        # remove unwanted characters
        staves = re.sub(r'[^SATB-]+', '', staves)
        # remove double hyphens, and from begin and end
        staves = re.sub('-+', '-', staves).strip('-')
        splitStaves = staves.split('-')
        p = ChoirStaff()
        choir = Sim(p)
        # print main instrumentName if there are more choirs, and we
        # have more than one staff.
        if len(splitStaves) > 1 and self.num:
            builder.setInstrumentNames(p, I18N_NOOP("Choir|Ch."), self.num)
        count = dict.fromkeys('SATB', 0)  # dict with count of parts.
        toGo = len(splitStaves)
        maxLen = max(map(len, splitStaves))
        lyr, staffNames = [], []
        for staff in splitStaves:
            toGo -= 1
            # sort the letters in order SATB
            staff = ''.join(i * staff.count(i) for i in 'SATB')
            # Create the staff for the voices
            s = Staff(parent=choir)
            builder.setMidiInstrument(s, self.midiInstrument)
            # Build lists of the voices and their instrument names
            instrNames, voices = [], []
            for part in staff:
                if staves.count(part) > 1:
                    count[part] += 1
                name, octave, instrName = self.partInfo[part]
                instrNames.append((instrName, count[part]))
                voices.append((name, count[part], octave))
            if len(staff) == 1:
                # There is only one voice in the staff. Just set the instrument
                # name directly in the staff.
                name, num = instrNames[0]
                builder.setInstrumentNames(s, name, num)
                # if *all* staves have only one voice, addlyrics is used.
                # In that case, don't remove the braces.
                mus = maxLen == 1 and Seq(s) or Seqr(s)
            else:
                # There are more instrument names for the staff, stack them in
                # a markup column.
                def mkup(names):
                    n = Markup()
                    if builder.lilypondVersion >= (2, 11, 57):
                        col = 'center-column'
                    else:
                        col = 'center-align'
                    col = MarkupEnclosed(col, n)
                    for name in names:
                        QuotedString(name, col)
                    return n
                builder.setInstrumentNames(s, map(mkup, zip(
                    *[builder.getInstrumentNames(name, num)
                        for name, num in instrNames])))
                mus = Simr(s)
            # Set the clef for this staff:
            if 'B' in staff:
                Clef('bass', mus)
            elif 'T' in staff:
                Clef('treble_8', mus)

            stanzas = self.stanzas.value()
            stanzas = stanzas == 1 and [0] or range(1, stanzas + 1)

            # Add the voices
            if len(staff) == 1:
                name, num, octave = voices[0]
                mname = name + (num and ly.nums(num) or '')
                if self.lyrEachDiff.isChecked():
                    lyrName = mname + 'Verse'
                else:
                    lyrName = 'verse'
                if maxLen == 1:
                    # if all staves have only one voice, use \addlyrics...
                    self.assignMusic(mus, octave, name=mname)
                    if not (self.lyrAllSame.isChecked() and not toGo):
                        for verse in stanzas:
                            lyr.append((AddLyrics(s), lyrName, verse))
                else:
                    # otherwise create explicit Voice and Lyrics contexts.
                    vname = name + str(num or '')
                    v = Seqr(Voice(vname, parent=mus))
                    self.assignMusic(v, octave, name=mname)
                    if not (self.lyrAllSame.isChecked() and not toGo):
                        for verse in stanzas:
                            lyr.append((LyricsTo(vname, Lyrics(parent=choir)),
                                lyrName, verse))

                if self.ambitus.isChecked():
                    Line('\\consists "Ambitus_engraver"', s.getWith())
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
                staffName, snum = staff, 1
                # if a name (like 's' or 'sa') is already in use in this part,
                # just add a number ('ss2' or 'sa2', etc.)
                while staffName in staffNames:
                    snum += 1
                    staffName = staff + str(snum)
                staffNames.append(staffName)
                # We want the staff name (actually context-id) in lower case.
                staffName = staffName.lower()
                # Create the voices and their lyrics.
                for (name, num, octave), vnum in zip(voices, order):
                    mname = name + (num and ly.nums(num) or '')
                    vname = name + str(num or '')
                    v = Voice(vname, parent=mus)
                    # Add ambitus to voice, move to the right if necessary
                    if self.ambitus.isChecked():
                        Line('\\consists "Ambitus_engraver"', v.getWith())
                        if vnum > 1:
                            Line("\\override Ambitus #'X-offset = #%s" %
                                 ((vnum - 1) * 2.0), v.getWith())
                    v = Seq(v)
                    Text('\\voice' + ly.nums(vnum), v)
                    self.assignMusic(v, octave, name=mname)
                    if self.lyrAllSame.isChecked() and toGo and vnum == 1:
                        lyrName = 'verse'
                        above = False
                    elif self.lyrEachSame.isChecked():
                        lyrName = 'verse'
                        above = vnum & 1
                    elif self.lyrEachDiff.isChecked():
                        lyrName = mname + 'Verse'
                        above = vnum & 1
                    else:
                        continue
                    # Create the lyrics. If they should be above the staff,
                    # give the staff a suitable name, and use alignAboveContext
                    # to align the Lyrics above the staff.
                    if above:
                        s.cid = Reference(staffName)
                    for verse in stanzas:
                        l = Lyrics(parent=choir)
                        if above:
                            l.getWith()['alignAboveContext'] = s.cid
                        lyr.append((LyricsTo(vname, l), lyrName, verse))

        # Assign the lyrics, so their definitions come after the note defs.
        for node, name, verse in lyr:
            self.assignLyrics(node, name, verse)
        self.nodes.append(p)


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
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Pedal:"), h)
        self.pedalVoices = QSpinBox(h)
        self.pedalVoices.setMinimum(0)
        self.pedalVoices.setMaximum(4)
        l.setBuddy(self.pedalVoices)
        self.pedalVoices.setValue(1)
        self.pedalVoices.setToolTip(i18n(
            "Set to 0 to disable the pedal altogether."))

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

    def assignDrums(self, node, name):
        s = DrumMode()
        Identifier('global', s)
        LineComment(i18n("Drums follow here."), s)
        BlankLine(s)
        self.assign(node, s, name)

    def build(self, builder):
        p = DrumStaff()
        s = Simr(p)
        if self.drumVoices.value() > 1:
            for i in range(1, self.drumVoices.value()+1):
                q = Seq(DrumVoice(parent=s))
                Text('\\voice%s' % ly.nums(i), q)
                self.assignDrums(q, 'drum%s' % ly.nums(i))
        else:
            self.assignDrums(s, 'drum')
        builder.setInstrumentNames(p, self.instrumentNames, self.num)
        i = self.drumStyle.currentIndex()
        if i > 0:
            v = ('drums', 'timbales', 'congas', 'bongos', 'percussion')[i]
            p.getWith()['drumStyleTable'] = Scheme('%s-style' % v)
            v = (5, 2, 2, 2, 1)[i]
            Line("\\override StaffSymbol #'line-count = #%i" % v, p.getWith())
        if self.drumStems.isChecked():
            Line("\\override Stem #'stencil = ##f", p.getWith())
            Line("\\override Stem #'length = #3  %% %s"
                % i18n("keep some distance."), p.getWith())
        self.nodes.append(p)

    def widgets(self, layout):
        h = KHBox()
        layout.addWidget(h)
        l = QLabel(i18n("Voices:"), h)
        self.drumVoices = QSpinBox(h)
        self.drumVoices.setMinimum(1)
        self.drumVoices.setMaximum(4)
        l.setBuddy(self.drumVoices)
        h.setToolTip(i18n("How many drum voices to put in this staff."))
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
