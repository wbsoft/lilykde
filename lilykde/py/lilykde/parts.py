# This file is part of LilyKDE, http://lilykde.googlecode.com/
#
# Copyright (c) 2008  Wilbert Berendsen
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Part types for the Score Wizard (scorewiz.py).

In separate file to ease maintenance.
"""

from qt import *

# Translate titles, etc.
from lilykde.i18n import _
from lilykde.util import romanize
from lilykde.scorewiz import part, nums
from lilykde.lilydom import *


class _SingleVoice(part):
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

    # Should contain a tuple with translated and standard italian
    # instrument names, both long and short, combined with a pipe symbol,
    # to ease the translation (otherwise the short names are not understood.)
    instrumentNames = None

    def build(self, braces = False):
        """
        Returns both the stub for the music voice, and the newly created
        staff object.

        if braces == True the music identifier will be put inside braces
        (needed for addlyrics).
        """
        s = self.newStaff()
        self.addPart(s)
        self.setInstrumentNames(s, *self.instrumentNames)
        s1 = braces and Seq(s) or Seqr(s)
        if self.clef:
            Clef(s1, self.clef)
        return self.assignMusic('', s1), s

    def assignMusic(self, name, node):
        """ automatically handles transposing instruments """
        return super(_SingleVoice, self).assignMusic(
            name, node, self.octave, self.transpose)


class _KeyboardBase(part):
    """
    Base class for keyboard instruments.
    """
    def buildStaff(self, name, clef, octave, pdoc, numVoices):
        """
        Build a staff with the given number of voices and name.
        """
        staff = self.newStaff(pdoc, name)
        c = Seqr(staff)
        if clef:
            Clef(c, clef)
        if numVoices == 1:
            self.assignMusic(name, c, octave)
        else:
            c = Sim(c)
            for i in range(1, numVoices):
                self.assignMusic(name + nums(i), c, octave)
                VoiceSeparator(c)
            self.assignMusic(name + nums(numVoices), c, octave)
        return staff

    def build(self):
        """ setup structure for 2 manuals. """
        p = PianoStaff(self.doc)
        self.addPart(p)
        self.setInstrumentNames(p, *self.instrumentNames)
        s = Sim(p, multiline=True)
        # add two staves, with a respective number of voices.
        self.buildStaff('right', '', 1, s, self.rightVoices.value())
        self.buildStaff('left', 'bass', 0, s, self.leftVoices.value())

    def widgets(self, p):
        QLabel('<p>%s <i>(%s)</i></p>' % (
            _("Adjust how many separate voices you want on each staff."),
            _("This is primarily useful when you write polyphonic music "
            "like a fuge.")), p)
        h = QHBox(p)
        l = QLabel(_("Right hand:"), h)
        self.rightVoices = QSpinBox(1, 4, 1, h)
        l.setBuddy(self.rightVoices)
        h = QHBox(p)
        l = QLabel(_("Left hand:"), h)
        self.leftVoices = QSpinBox(1, 4, 1, h)
        l.setBuddy(self.leftVoices)


class Organ(_KeyboardBase):
    name = _("Organ")
    instrumentNames = _("Organ|Org."), "Organo|Org."
    midiInstrument = 'church organ'

    def widgets(self, p):
        super(Organ, self).widgets(p)
        h = QHBox(p)
        l = QLabel(_("Pedal:"), h)
        self.pedalVoices = QSpinBox(0, 4, 1, h)
        l.setBuddy(self.pedalVoices)
        self.pedalVoices.setValue(1)
        QToolTip.add(self.pedalVoices, _(
            "Set to 0 to disable the pedal altogether."))

    def build(self):
        super(Organ, self).build()
        if self.pedalVoices.value():
            self.addPart(self.buildStaff('pedal', 'bass', -1, self.doc,
                self.pedalVoices.value()))


class Piano(_KeyboardBase):
    name = _("Piano")
    instrumentNames = _("Piano|Pno."), "Pianoforte|Pf."
    midiInstrument = 'acoustic grand'


class Harpsichord(_KeyboardBase):
    name = _("Harpsichord")
    instrumentNames = _("Harpsichord|Hs."), "Cembalo|Cemb."
    midiInstrument = 'harpsichord'


class Clavichord(_KeyboardBase):
    name = _("Clavichord")
    instrumentNames = _("Clavichord|Clv."), "Clavichord|Clv."
    midiInstrument = 'clav'


class Celesta(_KeyboardBase):
    name = _("Celesta")
    instrumentNames = _("Celesta|Cel."), "Celesta|Cel."
    midiInstrument = 'celesta'


class _SaxBase(_SingleVoice):
    """
    All saxophone types.
    """
    pass


class SopraninoSax(_SaxBase):
    name = _("Sopranino Sax")
    instrumentNames = _("Sopranino Sax|SiSx."), "Sopranino-Sax|Si-Sx."
    midiInstrument = 'soprano sax'
    transpose = (0, 2, -1)    # es'


class SopranoSax(_SaxBase):
    name = _("Soprano Sax")
    instrumentNames = _("Soprano Sax|SoSx."), "Soprano-Sax|So-Sx."
    midiInstrument = 'soprano sax'
    transpose = (-1, 6, -1)   # bes


class AltoSax(_SaxBase):
    name = _("Alto Sax")
    instrumentNames = _("Alto Sax|ASx."), "Alto-Sax|A-Sx."
    midiInstrument = 'alto sax'
    transpose = (-1, 2, -1)   # es


class TenorSax(_SaxBase):
    name = _("Tenor Sax")
    instrumentNames = _("Tenor Sax|TSx."), "Tenor-Sax|T-Sx."
    midiInstrument = 'tenor sax'
    transpose = (-2, 6, -1)   # bes,


class BaritoneSax(_SaxBase):
    name = _("Baritone Sax")
    instrumentNames = _("Baritone Sax|BSx."), "Bariton-Sax|B-Sx."
    midiInstrument = 'baritone sax'
    transpose = (-2, 2, -1)   # es,


class BassSax(_SaxBase):
    name = _("Bass Sax")
    instrumentNames = _("Bass Sax|BsSx."), "Basso-Sax|Bs-Sx."
    midiInstrument = 'baritone sax'
    transpose = (-3, 6, -1)   # bes,,


class _StringBase(_SingleVoice):
    """
    All string instruments
    """
    pass


class Violin(_StringBase):
    name = _("Violin")
    instrumentNames = _("Violin|Vl."), "Violino|Vl."
    midiInstrument = 'violin'


class Viola(_StringBase):
    name = _("Viola")
    instrumentNames = _("Viola|Vla."), "Viola|Vla."
    midiInstrument = 'viola'
    clef = 'alto'
    octave = 0


class Cello(_StringBase):
    name = _("Cello")
    instrumentNames = _("Cello|Cl."), "Violoncello|Vcl."
    midiInstrument = 'cello'
    clef = 'bass'
    octave = -1


class Contrabass(_StringBase):
    name = _("Contrabass")
    instrumentNames = _("Contrabass|Cb."), "Contrabasso|Cb."
    midiInstrument = 'contrabass'
    clef = 'bass'
    octave = -1


class BassoContinuo(Cello):
    name = _("Basso continuo")
    instrumentNames = _("Basso Continuo|B.c."), "Basso Continuo|B.c."
    def build(self):
        s = self.newStaff()
        self.addPart(s)
        self.setInstrumentNames(s, *self.instrumentNames)
        s = Sim(s)
        if self.clef:
            Clef(s, self.clef)
        self.assignMusic('bcMusic', s)
        b = FigureMode(self.doc)
        Identifier(b, 'global')
        Newline(b)
        Text(b,
            "\\override Staff.BassFigureAlignmentPositioning "
            "#'direction = #DOWN\n")
        Comment(b, ' ' + _("Figures follow here."))
        Newline(b)
        self.assignGeneric('bcFigures', s, b)


class _WoodWindBase(_SingleVoice):
    """ All woodwind instruments """
    pass


class Flute(_WoodWindBase):
    name = _("Flute")
    instrumentNames = _("Flute|Fl."), "Flauto|Fl."
    midiInstrument = 'flute'


class Piccolo(_WoodWindBase):
    name = _("Piccolo")
    instrumentNames = _("Piccolo|Pic."), "Flauto piccolo|Fl.pic."
    midiInstrument = 'piccolo'
    transpose = (1, 0, 0)


class BassFlute(_WoodWindBase):
    name = _("Bass flute")
    instrumentNames = _("Bass flute|Bfl."), "Flautone|Fln."
    midiInstrument = 'flute'
    transpose = (-1, 4, 0)


class Oboe(_WoodWindBase):
    name = _("Oboe")
    instrumentNames = _("Oboe|Ob."), "Oboe|Ob."
    midiInstrument = 'oboe'


class OboeDAmore(_WoodWindBase):
    name = _("Oboe d'Amore")
    instrumentNames = _("Oboe d'amore|Ob.d'am."), "Oboe d'amore|Ob.d'am."
    midiInstrument = 'oboe'
    transpose = (-1, 5, 0)


class EnglishHorn(_WoodWindBase):
    name = _("English Horn")
    instrumentNames = _("English horn|Eng.h."), "Corno Inglese|C.Ingl."
    midiInstrument = 'english horn'
    transpose = (-1, 3, 0)


class Bassoon(_WoodWindBase):
    name = _("Bassoon")
    instrumentNames = _("Bassoon|Bn."), "Fagotto|Fg."
    midiInstrument = 'bassoon'
    clef = 'bass'
    octave = -1


class ContraBassoon(_WoodWindBase):
    name = _("Contrabassoon")
    instrumentNames = _("Contrabassoon|C.Bn."), "Contra fagotto|C.Fg."
    midiInstrument = 'bassoon'
    transpose = (-1, 0, 0)
    clef = 'bass'
    octave = -1


class Clarinet(_WoodWindBase):
    name = _("Clarinet")
    instrumentNames = _("Clarinet|Cl."), "Clarinetto|Cl."
    midiInstrument = 'clarinet'
    transpose = (-1, 6, -1)


class SopranoRecorder(_WoodWindBase):
    name = _("Soprano recorder")
    instrumentNames = _("Soprano recorder|S.rec."), "Flauto dolce soprano|Fl.d.s."
    midiInstrument = 'recorder'
    transpose = (1, 0, 0)


class AltoRecorder(_WoodWindBase):
    name = _("Alto recorder")
    instrumentNames = _("Alto recorder|A.rec."), "Flauto dolce alto|Fl.d.a."
    midiInstrument = 'recorder'


class TenorRecorder(_WoodWindBase):
    name = _("Tenor recorder")
    instrumentNames = _("Tenor recorder|T.rec."), "Flauto dolce tenore|Fl.d.t."
    midiInstrument = 'recorder'


class BassRecorder(_WoodWindBase):
    name = _("Bass recorder")
    instrumentNames = _("Bass recorder|B.rec."), "Flauto dolce basso|Fl.d.b."
    midiInstrument = 'recorder'
    clef = 'bass'
    octave = -1


class _BrassBase(_SingleVoice):
    """
    All brass instruments.
    """
    pass


class HornF(_BrassBase):
    name = _("Horn in F")
    instrumentNames = _("Horn in F|Hn.F."), "Corno|Cor."
    midiInstrument = 'french horn'
    transpose = (-1, 3, 0)


class TrumpetC(_BrassBase):
    name = _("Trumpet in C")
    instrumentNames = _("Trumpet in C|Tr.C"), "Tromba Do|Tr.Do"
    midiInstrument = 'trumpet'


class TrumpetBb(TrumpetC):
    name = _("Trumpet in Bb")
    instrumentNames = _("Trumpet in Bb|Tr.Bb"), "Tromba Si-bemolle|Tr.Sib"
    transpose = (-1, 6, -1)


class Trombone(_BrassBase):
    name = _("Trombone")
    instrumentNames = _("Trombone|Trb."), "Trombone|Trb."
    midiInstrument = 'trombone'
    clef = 'bass'
    octave = -1


class Tuba(_BrassBase):
    name = _("Tuba")
    instrumentNames = _("Tuba|Tb."), "Tuba|Tb."
    midiInstrument = 'tuba'
    transpose = (-2, 6, -1)


class BassTuba(_BrassBase):
    name = _("Bass Tuba")
    instrumentNames = _("Bass Tuba|B.Tb."), "Tuba bassa|Tb.b."
    midiInstrument = 'tuba'
    transpose = (-2, 0, 0)
    clef = 'bass'
    octave = -1


class _TablatureBase(_SingleVoice):
    """
    A class for instruments that support TabStaffs.
    """
    octave = 0
    tunings = ()    # may contain a list of tunings.
    tabFormat = ''  # can contain a tablatureFormat value.

    def widgets(self, p):
        h = QHBox(p)
        l = QLabel(_("Staff type:"), h)
        self.staffType = QComboBox(False, h)
        l.setBuddy(self.staffType)
        for i in (
                _("Normal staff"),
                _("Tablature"),
                _("Both"),
            ):
            self.staffType.insertItem(i)
        if self.tunings:
            QObject.connect(self.staffType, SIGNAL("activated(int)"),
                self.slotTabEnable)
            self.widgetsTuning(p)
            self.slotTabEnable(0)

    def widgetsTuning(self, p):
        """ Implement widgets related to tuning """
        h = QHBox(p)
        l = QLabel(_("Tuning:"), h)
        self.tuningSel = QComboBox(False, h)
        l.setBuddy(self.tuningSel)
        self.tuningSel.insertItem(_("Default"))
        for t in self.tunings:
            self.tuningSel.insertItem(t[0])

    def slotTabEnable(self, enable):
        """
        Called when the user changes the staff type.
        Non-zero if the user wants a TabStaff.
        """
        self.tuningSel.setEnabled(bool(enable))

    def newTabStaff(self, node = None, name = None, midiInstrument = None):
        """
        Create a new TabStaff object and set it's MIDI instrument if desired.
        """
        s = TabStaff(node or self.doc, name)
        if self._midi:
            midi = midiInstrument or self.midiInstrument
            if midi:
                s.getWith()['midiInstrument'] = midi
        if self.tabFormat:
            Scheme(Assignment(s.getWith(), 'tablatureFormat'), self.tabFormat)
        return s

    def build(self):
        t = self.staffType.currentItem()
        if t == 0:
            # normal staff
            super(_TablatureBase, self).build()
            return

        # make a tabstaff
        tab = self.newTabStaff()
        s = Seqr(tab)
        self.assignMusic('', s)
        # Tunings?
        self.setTunings(tab)
        # both?
        p = tab
        if t == 2:
            s = StaffGroup(self.doc)
            if self._instr:
                Text(s.getWith(), '\\consists "Instrument_name_engraver"\n')
            s1 = Sim(s, multiline=True)
            s1.append(tab)
            p = s
            s = Seqr(self.newStaff(s1))
            if self.clef:
                Clef(s, self.clef)
            self.assignMusic('', s)
        self.setInstrumentNames(p, *self.instrumentNames)
        self.addPart(p)

    def setTunings(self, tab):
        """ set tunings """
        if self.tunings and self.tuningSel.currentItem() > 0:
            tuning = self.tunings[self.tuningSel.currentItem() - 1][1]
            Scheme(Assignment(tab.getWith(), 'stringTunings'), tuning)



class Mandolin(_TablatureBase):
    name = _("Mandolin")
    instrumentNames = _("Mandolin|Mdl."), "Mandolino|Mdl."
    midiInstrument = 'acoustic guitar (steel)'
    tunings = (
        (_("Mandolin tuning"), 'mandolin-tuning'),
    )


class Banjo(_TablatureBase):
    name = _("Banjo")
    instrumentNames = _("Banjo|Bj."), "Banjo|Bj."
    midiInstrument = 'banjo'
    tabFormat = 'fret-number-tablature-format-banjo'
    tunings = (
        (_("Open G-tuning (aDGBD)"), 'banjo-open-g-tuning'),
        (_("C-tuning (gCGBD)"), 'banjo-c-tuning'),
        (_("Modal tuning (gDGCD)"), 'banjo-modal-tuning'),
        (_("Open D-tuning (aDF#AD)"), 'banjo-open-d-tuning'),
        (_("Open Dm-tuning (aDFAD)"), 'banjo-open-dm-tuning'),
    )
    def widgetsTuning(self, p):
        super(Banjo, self).widgetsTuning(p)
        self.fourStrings = QCheckBox(_("Four strings (instead of five)"), p)

    def slotTabEnable(self, enable):
        super(Banjo, self).slotTabEnable(enable)
        self.fourStrings.setEnabled(bool(enable))

    def setTunings(self, tab):
        if not self.fourStrings.isChecked():
            super(Banjo, self).setTunings(tab)
        else:
            Scheme(Assignment(tab.getWith(), 'stringTunings'),
                '(four-string-banjo %s)' %
                self.tunings[self.tuningSel.currentItem()][1])


class ClassicalGuitar(_TablatureBase):
    name = _("Classical guitar")
    instrumentNames = _("Guitar|Gt."), "Chitarra|Chit."
    midiInstrument = 'acoustic guitar (nylon)'
    transpose = (-1, 0, 0)
    tunings = (
        (_("Guitar tuning"), 'guitar-tuning'),
        (_("Open G-tuning"), 'guitar-open-g-tuning'),
    )


class JazzGuitar(ClassicalGuitar):
    name = _("Jazz guitar")
    instrumentNames = _("Jazz guitar|J.Gt."), "Jazz Chitarra|J.Chit." #FIXME
    midiInstrument = 'electric guitar (jazz)'


class Bass(_TablatureBase):
    name = _("Bass")
    instrumentNames = _("Bass|Bs."), "Bass|B." #FIXME
    midiInstrument = 'acoustic bass'
    transpose = (-1, 0, 0)
    clef = 'bass'
    octave = -1
    tunings = (
        (_("Bass tuning"), 'bass-tuning'),
    )


class ElectricBass(Bass):
    name = _("Electric bass")
    instrumentNames = _("Electric bass|E.Bs."), "Electric bass|E.B." #FIXME
    midiInstrument = 'electric bass (finger)'


class Harp(_KeyboardBase):
    name = _("Harp")
    instrumentNames = _("Harp|Hp."), "Arpa|Ar."
    midiInstrument = 'harp'
    def build(self):
        """ setup structure for 2 manuals. """
        p = PianoStaff(self.doc)
        self.addPart(p)
        self.setInstrumentNames(p, *self.instrumentNames)
        s = Sim(p, multiline=True)
        # add two staves, with a respective number of voices.
        self.buildStaff('upper', '', 1, s, 1)
        self.buildStaff('lower', 'bass', 0, s, 1)

    def widgets(self, p):
        part.widgets(self, p)


class _PitchedPercussionBase(_SingleVoice):
    """
    All pitched percussion instruments.
    """
    pass


class Timpani(_PitchedPercussionBase):
    name = _("Timpani")
    instrumentNames = _("Timpani|Tmp."), "Timpani|Tmp."
    midiInstrument = 'timpani'
    clef = 'bass'
    octave = -1


class Xylophone(_PitchedPercussionBase):
    name = _("Xylophone")
    instrumentNames = _("Xylophone|Xyl."), "Silofono|Sil."
    midiInstrument = 'xylophone'


class Marimba(_PitchedPercussionBase):
    name = _("Marimba")
    instrumentNames = _("Marimba|Mar."), "Marimba|Mar."
    midiInstrument = 'marimba'


class Vibraphone(_PitchedPercussionBase):
    name = _("Vibraphone")
    instrumentNames = _("Vibraphone|Vib."), "Vibrafono|Vib."
    midiInstrument = 'vibraphone'


class TubularBells(_PitchedPercussionBase):
    name = _("Tubular bells")
    instrumentNames = _("Tubular bells|Tub."), "Campana tubolare|Cmp.t."
    midiInstrument = 'tubular bells'


class Glockenspiel(_PitchedPercussionBase):
    name = _("Glockenspiel")
    instrumentNames = _("Glockenspiel|Gls."), "Campanelli|Camp."
    midiInstrument = 'glockenspiel'


class Drums(part):
    name = _("Drums")
    instrumentNames = _("Drums|Dr."), "Tamburo|Tamb."

    def assignDrums(self, name, node):
        s = DrumMode(self.doc)
        Identifier(s, 'global')
        Newline(s)
        Comment(s, ' '+_("Drums follow here."))
        Newline(s)
        self.assignGeneric(name, node, s)

    def build(self):
        p = DrumStaff(self.doc)
        s = Simr(p, multiline = True)

        if self.drumVoices.value() > 1:
            for i in range(1, self.drumVoices.value()+1):
                q = Seq(DrumVoice(s))
                Text(q, '\\voice%s' % nums(i))
                self.assignDrums('drum%s' % nums(i), q)
        else:
            self.assignDrums('drum', s)
        self.addPart(p)
        self.setInstrumentNames(p, *self.instrumentNames)
        i = self.drumStyle.currentItem()
        if i > 0:
            v = ('drums', 'timbales', 'congas', 'bongos', 'percussion')[i]
            p.getWith()['drumStyleTable'] = Scheme(self.doc, '%s-style' % v)
            v = (5, 2, 2, 2, 1)[i]
            Text(p.getWith(), "\\override StaffSymbol #'line-count = #%i\n" % v)
        if self.drumStems.isChecked():
            Text(p.getWith(), "\\override Stem #'stencil = ##f\n")
            Text(p.getWith(), "\\override Stem #'length = #3  %% %s"
                % _("keep some distance."))

    def widgets(self, p):
        h = QHBox(p)
        l = QLabel(_("Voices:"), h)
        self.drumVoices = QSpinBox(1, 4, 1, h)
        l.setBuddy(self.drumVoices)
        QToolTip.add(h, _("How many drum voices to put in this staff."))
        h = QHBox(p)
        l = QLabel(_("Style:"), h)
        self.drumStyle = QComboBox(False, h)
        l.setBuddy(self.drumStyle)
        for i in (
                _("Drums (5 lines, default)"),
                _("Timbales-style (2 lines)"),
                _("Congas-style (2 lines)"),
                _("Bongos-style (2 lines)"),
                _("Percussion-style (1 line)"),
            ):
            self.drumStyle.insertItem(i)
        self.drumStems = QCheckBox(_("Remove stems"), p)
        QToolTip.add(self.drumStems, _("Remove the stems from the drum notes."))


class Chords(part):
    name = _("Chord names")
    def build(self):
        p = ChordNames(self.doc)
        s = ChordMode(self.doc)
        Identifier(s, 'global')
        Newline(s)
        i = self.chordStyle.currentItem()
        if i > 0:
            Identifier(s, '%sChords' %
                ('german', 'semiGerman', 'italian', 'french')[i-1])
            Newline(s)
        Comment(s, ' ' + _("Chords follow here."))
        Newline(s)
        self.assignGeneric('chordNames', p, s)
        self.addPart(p)

    def widgets(self, p):
        h = QHBox(p)
        l = QLabel(_("Chord style:"), h)
        self.chordStyle = QComboBox(False, h)
        l.setBuddy(self.chordStyle)
        for i in (
                _("Default"),
                _("German"),
                _("Semi-German"),
                _("Italian"),
                _("French"),
            ):
            self.chordStyle.insertItem(i)


class BassFigures(part):
    name = _("Figured Bass")
    def build(self):
        p = FiguredBass(self.doc)
        s = FigureMode(self.doc)
        Identifier(s, 'global')
        Newline(s)
        Comment(s, ' ' + _("Figures follow here."))
        Newline(s)
        self.assignGeneric('figBass', p, s)
        self.addPart(p)
        if self.useExtenderLines.isChecked():
            p.getWith()['useBassFigureExtenders'] = Scheme(self.doc, '#t')

    def widgets(self, p):
        self.useExtenderLines = QCheckBox(_("Use extender lines"), p)


class _VocalBase(part):
    """
    Base class for vocal stuff.
    """
    midiInstrument = 'choir aahs'

    def assignLyrics(self, name, node, verse = 0):
        l = LyricMode(self.doc)
        if verse:
            name = name + nums(verse)
            Text(l, '\\set stanza = "%d."\n' % verse)
        Comment(l, ' ' + _("Lyrics follow here."))
        Newline(l)
        self.assignGeneric(name, node, l)

    def widgets(self, p):
        self.stanzaWidget(p)
        self.ambitusWidget(p)

    def stanzaWidget(self, p):
        h = QHBox(p)
        l = QLabel(_("Stanzas:"), h)
        self.stanzas = QSpinBox(1, 10, 1, h)
        l.setBuddy(self.stanzas)
        QToolTip.add(h, _("The number of stanzas."))

    def ambitusWidget(self, p):
        self.ambitus = QCheckBox(_("Ambitus"), p)
        QToolTip.add(self.ambitus, _(
            "Show the pitch range of the voice at the beginning of the staff."))

    def addStanzas(self, node, name = '', count = 0):
        r"""
        Add stanzas in count (or self.stanzas.value()) to the (Voice) node
        using \addlyrics.
        """
        name = name or 'verse'
        count = count or self.stanzas.value()
        if count == 1:
            self.assignLyrics(name, AddLyrics(node))
        else:
            for i in range(count):
                Newline(node)
                self.assignLyrics(name, AddLyrics(node), i + 1)


class _VocalSolo(_VocalBase, _SingleVoice):
    """
    Base class for solo voices
    """
    def build(self):
        stub, staff = _SingleVoice.build(self, True)
        stub[1].insert(stub[1][-2], Text(self.doc, '\\dynamicUp\n'))
        self.addStanzas(staff)
        if self.ambitus.isChecked():
            Text(staff.getWith(), '\\consists "Ambitus_engraver"\n')

class SopranoVoice(_VocalSolo):
    name = _("Soprano")
    instrumentNames = _("Soprano|S."), "Soprano|S."


class MezzoSopranoVoice(_VocalSolo):
    name = _("Mezzo soprano")
    instrumentNames = _("Mezzo-soprano|Ms."), "Mezzosoprano|Ms."


class AltoVoice(_VocalSolo):
    name = _("Alto")
    instrumentNames = _("Alto|A."), "Alto|A."
    octave = 0


class TenorVoice(_VocalSolo):
    name = _("Tenor")
    instrumentNames = _("Tenor|T."), "Tenore|T."
    octave = 0
    clef = 'treble_8'


class BassVoice(_VocalSolo):
    name = _("Bass")
    instrumentNames = _("Bass|B."), "Basso|B."
    octave = -1
    clef = 'bass'


class LeadSheet(_VocalBase, Chords):
    name = _("Lead sheet")

    def build(self):
        """
        Create chord names, song and lyrics.
        Optional a second staff with a piano accompaniment.
        """
        Chords.build(self)
        if self.accomp.isChecked():
            p = ChoirStaff(self.doc)
            #TODO: instrument mames ?
            s = Sim(p, multiline = True)
            mel = Sim(Staff(s), multiline = True)
            v1 = Voice(mel)
            s1 = Seq(v1, multiline = True)
            Text(s1, '\\voiceOne\n')
            self.assignMusic('melody', s1, 1)
            s2 = Seq(Voice(mel), multiline = True)
            Text(s2, '\\voiceTwo\n')
            self.assignMusic('accRight', s2, 0)
            acc = Seqr(Staff(s))
            Clef(acc, 'bass')
            self.assignMusic('accLeft', acc, -1)
            if self.ambitus.isChecked():
                # We can't use \addlyrics when the voice has a \with {}
                # section, because it creates a nested Voice context.
                # So if the ambitus engraver should be added to the Voice,
                # we don't use \addlyrics but create a new Lyrics context.
                # So in that case we don't use addStanzas, but insert the
                # Lyrics contexts manually inside our ChoirStaff.
                v1.cid = 'melody'
                Text(v1.getWith(), '\\consists "Ambitus_engraver"\n')
                count = self.stanzas.value() # number of stanzas
                if count == 1:
                    l = Lyrics(self.doc)
                    s.insert(acc.parent, l)
                    self.assignLyrics('verse', LyricsTo(l, v1.cid))
                else:
                    for i in range(count):
                        l = Lyrics(self.doc)
                        s.insert(acc.parent, l)
                        self.assignLyrics('verse', LyricsTo(l, v1.cid), i + 1)
            else:
                self.addStanzas(v1)
        else:
            p = Staff(self.doc)
            self.assignMusic('melody', Seq(p), 1)
            self.addStanzas(p)
            if self.ambitus.isChecked():
                Text(p.getWith(), '\\consists "Ambitus_engraver"\n')
        self.addPart(p)

    def widgets(self, p):
        QLabel('<p><i>%s</i></p>' % _(
            "The Lead Sheet provides a staff with chord names above "
            "and lyrics below it. A second staff is optional."), p)
        self.accomp = QCheckBox(_("Add accompaniment staff"), p)
        QToolTip.add(self.accomp, _(
            "Adds an accompaniment staff and also puts an accompaniment "
            "voice in the upper staff."))
        Chords.widgets(self, p)
        _VocalBase.widgets(self, p)


class Choir(_VocalBase):
    name = _("Choir")

    def widgets(self, p):
        QLabel('<p>%s</p><p><i>(%s)</i></p>' % (
            _("Please select the voices for the choir. "
            "Use the letters S, A, T, or B. A hyphen denotes a new staff."),
            _("Tip: For a double choir you can use two choir parts.")), p)
        h = QHBox(p)
        l = QLabel(_("Voicing:"), h)
        self.voicing = QComboBox(True, h)
        l.setBuddy(self.voicing)
        for i in (
            'SA-TB', 'S-A-T-B',
            'SA', 'S-A', 'SS-A',
            'TB', 'T-B', 'TT-B',
            'SS-A-T-B', 'SS-A-TT-B',
            'S-S-A-T-T-B', 'S-S-A-A-T-T-B-B'
            ):
            self.voicing.insertItem(i)
        b = QVButtonGroup(_("Lyrics"), p)
        self.lyrAllSame = QRadioButton(_("All voices same lyrics"), b)
        self.lyrAllSame.setChecked(True)
        QToolTip.add(self.lyrAllSame, _(
            "One set of the same lyrics is placed between all staves."))
        self.lyrEachSame = QRadioButton(_("Every voice same lyrics"), b)
        QToolTip.add(self.lyrEachSame, _(
            "Every voice gets its own lyrics, using the same text as the "
            "other voices."))
        self.lyrEachDiff = QRadioButton(_("Every voice different lyrics"), b)
        QToolTip.add(self.lyrEachDiff, _(
            "Every voice gets a different set of lyrics."))
        self.stanzaWidget(b)
        self.ambitusWidget(p)

    partInfo = {
        'S': ('soprano', 1, SopranoVoice.instrumentNames),
        'A': ('alto', 0, AltoVoice.instrumentNames),
        'T': ('tenor', 0, TenorVoice.instrumentNames),
        'B': ('bass', -1, BassVoice.instrumentNames),
    }

    def build(self):
        # normalize voicing
        staffs = unicode(self.voicing.currentText()).upper()
        # remove unwanted characters
        staffs = re.sub(r'[^SATB-]+', '', staffs)
        # remove double hyphens, and from begin and end
        staffs = re.sub('-+', '-', staffs).strip('-')
        splitStaffs = staffs.split('-')
        p = ChoirStaff(self.doc)
        choir = Sim(p, multiline = True)
        self.addPart(p)
        # print main instrumentName if there are more choirs, and we
        # have more than one staff.
        if self._instr and '-' in staffs and self.num:
            self.setInstrumentNames(p, _("Choir|Ch."), "Coro|C.")
            Text(p.getWith(), '\\consists "Instrument_name_engraver"\n')

        count = dict.fromkeys('SATB', 0)  # dict with count of parts.
        toGo = len(splitStaffs)
        maxLen = max(map(len, splitStaffs))
        lyr, staffNames = [], []
        for staff in splitStaffs:
            toGo -= 1
            # sort the letters in order SATB
            staff = ''.join(i * staff.count(i) for i in 'SATB')
            # Create the staff for the voices
            s = self.newStaff(choir)
            # Build lists of the voices and their instrument names
            instrNames, voices = [], []
            for part in staff:
                if staffs.count(part) > 1:
                    count[part] += 1
                name, octave, (translated, italian) = self.partInfo[part]
                instrNames.append(
                    self.buildInstrumentNames(translated, italian, count[part]))
                voices.append((name, count[part], octave))
            if len(staff) == 1:
                # There is only one voice in the staff. Just set the instrument
                # name directly in the staff.
                s.instrName(*instrNames[0])
                # if *all* staves have only one voice, addlyrics is used.
                # In that case, don't remove the braces.
                mus = maxLen == 1 and Seq(s) or Seqr(s)
            else:
                # There are more instrument names for the staff, stack them in
                # a markup column.
                def mkup(names):
                    # return a markup object with names stacked vertically
                    if max(names):
                        n = Markup(self.doc)
                        # from 2.11.57 and above LilyPond uses center-column
                        from lilykde.version import version
                        if version and version >= (2, 11, 57):
                            m = MarkupEncl(n, 'center-column', multiline=True)
                        else:
                            m = MarkupEncl(n, 'center-align', multiline=True)
                        for i in names:
                            QuotedString(m, i)
                        return n
                s.instrName(*map(mkup, zip(*instrNames)))
                mus = Simr(s, multiline = True)
            # Set the clef for this staff:
            if 'B' in staff:
                Clef(mus, 'bass')
            elif 'T' in staff:
                Clef(mus, 'treble_8')

            stanzas = self.stanzas.value()
            stanzas = stanzas == 1 and [0] or range(1, stanzas + 1)

            # Add the voices
            if len(staff) == 1:
                name, num, octave = voices[0]
                mname = name + (num and nums(num) or '')
                if self.lyrEachDiff.isChecked():
                    lyrName = mname + 'Verse'
                else:
                    lyrName = 'verse'
                if maxLen == 1:
                    # if all staves have only one voice, use \addlyrics...
                    self.assignMusic(mname, mus, octave)
                    if not (self.lyrAllSame.isChecked() and not toGo):
                        for verse in stanzas:
                            Newline(s)
                            lyr.append((lyrName, AddLyrics(s), verse))
                else:
                    # otherwise create explicit Voice and Lyrics contexts.
                    vname = name + str(num or '')
                    v = Seqr(Voice(mus, vname))
                    self.assignMusic(mname, v, octave)
                    if not (self.lyrAllSame.isChecked() and not toGo):
                        for verse in stanzas:
                            lyr.append(
                                (lyrName, LyricsTo(Lyrics(choir), vname), verse))

                if self.ambitus.isChecked():
                    Text(s.getWith(), '\\consists "Ambitus_engraver"\n')
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
                    mname = name + (num and nums(num) or '')
                    vname = name + str(num or '')
                    v = Voice(mus, vname)
                    # Add ambitus to voice, move to the right if necessary
                    if self.ambitus.isChecked():
                        Text(v.getWith(), '\\consists "Ambitus_engraver"\n')
                        if vnum > 1:
                            Text(v.getWith(),
                                "\\override Ambitus #'X-offset = #%s\n" %
                                ((vnum - 1) * 2.0))
                    v = Seqr(v)
                    Text(v, '\\voice' + nums(vnum))
                    self.assignMusic(mname, v, octave)
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
                        s.cid = staffName
                    for verse in stanzas:
                        l = Lyrics(choir)
                        if above:
                            l.getWith()['alignAboveContext'] = staffName
                        lyr.append((lyrName, LyricsTo(l, vname), verse))

        # Assign the lyrics, so their definitions come after the note defs.
        for name, node, verse in lyr:
            self.assignLyrics(name, node, verse)





# The structure of the overview
categories = (
    (_("Strings"), (
            Violin,
            Viola,
            Cello,
            Contrabass,
            BassoContinuo,
        )),
    (_("Plucked strings"), (
            Mandolin,
            Banjo,
            ClassicalGuitar,
            JazzGuitar,
            Bass,
            ElectricBass,
            Harp,
        )),
    (_("Woodwinds"), (
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
    (_("Brass"), (
            HornF,
            TrumpetC,
            TrumpetBb,
            Trombone,
            Tuba,
            BassTuba,
        )),
    (_("Vocal"), (
            LeadSheet,
            SopranoVoice,
            MezzoSopranoVoice,
            AltoVoice,
            TenorVoice,
            BassVoice,
            Choir,
        )),
    (_("Keyboard instruments"), (
            Piano,
            Harpsichord,
            Clavichord,
            Organ,
            Celesta,
        )),
    (_("Percussion"), (
            Timpani,
            Xylophone,
            Marimba,
            Vibraphone,
            TubularBells,
            Glockenspiel,
            Drums,
        )),
    (_("Special"), (
            Chords,
            BassFigures,
        )),
)


