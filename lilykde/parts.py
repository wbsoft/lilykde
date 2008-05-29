"""
Part types for the Score Wizard (scorewiz.py).

In separate file to ease maintenance.
"""

from qt import *

# Translate titles, etc.
from lilykde.i18n import _
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

    def build(self):
        s = self.newStaff()
        self.addPart(s)
        self.setInstrumentNames(s, *self.instrumentNames)
        s = Seqr(s)
        if self.clef:
            Clef(s, self.clef)
        self.assignMusic('', s)

    def assignMusic(self, name, node):
        """ automatically handles transposing instruments """
        super(_SingleVoice, self).assignMusic(
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
        # add two staffs, with a respective number of voices.
        self.buildStaff('right', '', 1, s, self.rightVoices.value())
        self.buildStaff('left', 'bass', 0, s, self.leftVoices.value())

    def widgetsStaffVoice(self, p):
        l = QLabel('<p>%s <i>(%s)</i></p>' % (
            _("Adjust how many separate voices you want on each staff:"),
            _("This is primarily useful when you write polyphonic music "
            "like a fuge.")), p)
        h = QHBox(p)
        QLabel(_("Right hand:"), h)
        self.rightVoices = QSpinBox(1, 4, 1, h)
        h = QHBox(p)
        QLabel(_("Left hand:"), h)
        self.leftVoices = QSpinBox(1, 4, 1, h)

    def widgets(self, p):
        self.widgetsStaffVoice(p)


class Organ(_KeyboardBase):
    name = _("Organ")
    instrumentNames = _("Organ|Org."), "Organo|Org."
    midiInstrument = 'church organ'

    def widgetsStaffVoice(self, p):
        super(Organ, self).widgetsStaffVoice(p)
        h = QHBox(p)
        QLabel(_("Pedal:"), h)
        self.pedalVoices = QSpinBox(0, 4, 1, h)
        self.pedalVoices.setValue(1)
        QToolTip.add(self.pedalVoices, _(
            "Set to 0 to disable the pedal altogether"))

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
    octave = 0


class Contrabass(_StringBase):
    name = _("Contrabass")
    instrumentNames = _("Contrabass|Cb."), "Contrabasso|Cb."
    midiInstrument = 'contrabass'
    clef = 'bass'
    octave = -1


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
    name = "Horn in F"
    instrumentNames = ("Horn in F|Hn.F."), "Corno|Cor."
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
        QLabel(_("Staff type:"), h)
        self.staffType = QComboBox(False, h)
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
        QLabel(_("Tuning:"), h)
        self.tuningSel = QComboBox(False, h)
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
        # add two staffs, with a respective number of voices.
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
        QLabel(_("Voices:"), h)
        self.drumVoices = QSpinBox(1, 4, 1, h)
        QToolTip.add(h, _("How many drum voices to put in this staff."))
        h = QHBox(p)
        QLabel(_("Style:"), h)
        self.drumStyle = QComboBox(False, h)
        for i in (
                _("Drums (5 lines, default)"),
                _("Timbales-style (2 lines)"),
                _("Congas-style (2 lines)"),
                _("Bongos-style (2 lines)"),
                _("Percussion-style (1 line)"),
            ):
            self.drumStyle.insertItem(i)
        self.drumStems = QCheckBox(_("Remove stems"), p)
        QToolTip.add(self.drumStems, _("Remove the stems from the drum notes"))





# The structure of the overview
categories = (
    (_("Strings"), (
            Violin,
            Viola,
            Cello,
            Contrabass,
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

        )),
)


