"""
Part types for the Score Wizard (scorewiz.py).

In separate file to ease maintenance.
"""

from qt import *

# Translate titles, etc.
from lilykde.i18n import _
from lilykde.scorewiz import part
from lilydom import *


_nums = (
    'Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
    'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
    'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen')

_tens = (
    'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty',
    'Ninety', 'Hundred')

def nums(num):
    """
    Returns a textual representation of a number (e.g. 1 -> "One"), for use
    in LilyPond identifiers (that do not support numbers).
    Supports numbers 0 to 109.
    """
    if num < 20:
        return _nums[num]
    d, r = divmod(num, 10)
    n = _tens[d-2]
    if r:
        n += _nums[r]
    return n


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
        if self.transpose:
            self.assignTransposedMusic('', s, self.octave, self.transpose)
        else:
            self.assignMusic('', s, self.octave)



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


class Mandolin(_SingleVoice):
    name = _("Mandolin")
    instrumentNames = _("Mandolin|Mdl."), "Mandolino|Mdl."
    midiInstrument = 'acoustic guitar (steel)'


class Banjo(_SingleVoice):
    name = _("Banjo")
    instrumentNames = _("Banjo|Bj."), "Banjo|Bj."
    midiInstrument = 'banjo'


class ClassicalGuitar(_SingleVoice):
    name = _("Classical guitar")
    instrumentNames = _("Guitar|Gt."), "Chitarra|Chit."
    midiInstrument = 'acoustic guitar (nylon)'
    transpose = (-1, 0, 0)


class JazzGuitar(_SingleVoice):
    name = _("Jazz guitar")
    instrumentNames = _("Jazz guitar|J.Gt."), "Jazz Chitarra|J.Chit."
    midiInstrument = 'electric guitar (jazz)'
    transpose = (-1, 0, 0)


class Bass(_SingleVoice):
    name = _("Bass")
    instrumentNames = _("Bass|Bs."), "Bass|B." #FIXME
    midiInstrument = 'acoustic bass'
    transpose = (-1, 0, 0)
    clef = 'bass'
    octave = -1


class ElectricBass(_SingleVoice):
    name = _("Electric bass")
    instrumentNames = _("Electric bass|E.Bs."), "Electric bass|E.B." #FIXME
    midiInstrument = 'electric bass (finger)'
    transpose = (-1, 0, 0)
    clef = 'bass'
    octave = -1


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
            Celesta
        )),
    (_("Percussion"), (

        )),
    (_("Special"), (

        )),
)


