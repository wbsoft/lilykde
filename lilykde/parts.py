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


class Violin(part):
    name = _("Violin")
    pass


class _KeyboardBase(part):
    """
    Base class for keyboard instruments.
    """

    # Should contain a tuple with translated and standard italian
    # instrument names, both long and short, combined with a pipe symbol,
    # to ease the translation (otherwise the short names are not understood.)
    instrumentNames = "Translated|Tr.", "Italian|It."

    def buildStaff(self, name, clef, octave, pdoc, numVoices):
        """
        Build a staff with the given number of voices and name.
        """
        staff = self.newStaff(pdoc, name)
        c = Seq(staff)
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
        self.buildStaff('right', 'treble', 1, s, self.rightVoices.value())
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
    pass


class Harpsichord(_KeyboardBase):
    name = _("Harpsichord")
    instrumentNames = _("Harpsichord|Hs."), "Cembalo|Cemb."
    midiInstrument = 'harpsichord'
    pass


class Clavichord(_KeyboardBase):
    name = _("Clavichord")
    instrumentNames = _("Clavichord|Clv."), "Clavichord|Clv."
    midiInstrument = 'clav'
    pass


class Celesta(_KeyboardBase):
    name = _("Celesta")
    instrumentNames = _("Celesta|Cel."), "Celesta|Cel."
    midiInstrument = 'celesta'
    pass


class _SaxBase(part):
    """
    All saxophones.
    """
    name = _("Sax")

    def build(self):
        s = self.newStaff()
        self.assignTransposedMusic('sax', s, *self.transpose)
        self.addPart(s)


class SopraninoSax(_SaxBase):
    name = _("Sopranino Sax")
    instrumentNames = _("Sopranino Sax|SiSx."), "Sopranino-Sax|Si-Sx."
    midiInstrument = 'soprano sax'
    transpose = (0, 2, -1)    # es'
    pass


class SopranoSax(_SaxBase):
    name = _("Soprano Sax")
    instrumentNames = _("Soprano Sax|SoSx."), "Soprano-Sax|So-Sx."
    midiInstrument = 'soprano sax'
    transpose = (-1, 6, -1)   # bes
    pass


class AltoSax(_SaxBase):
    name = _("Alto Sax")
    instrumentNames = _("Alto Sax|ASx."), "Alto-Sax|A-Sx."
    midiInstrument = 'alto sax'
    transpose = (-1, 2, -1)   # es
    pass


class TenorSax(_SaxBase):
    name = _("Tenor Sax")
    instrumentNames = _("Tenor Sax|TSx."), "Tenor-Sax|T-Sx."
    midiInstrument = 'tenor sax'
    transpose = (-2, 6, -1)   # bes,
    pass


class BaritoneSax(_SaxBase):
    name = _("Baritone Sax")
    instrumentNames = _("Baritone Sax|BSx."), "Bariton-Sax|B-Sx."
    midiInstrument = 'baritone sax'
    transpose = (-2, 2, -1)   # es,
    pass


class BassSax(_SaxBase):
    name = _("Bass Sax")
    instrumentNames = _("Bass Sax|BsSx."), "Basso-Sax|Bs-Sx."
    midiInstrument = 'baritone sax'
    transpose = (-3, 6, -1)   # bes,,
    pass




# The structure of the overview
categories = (
    (_("Strings"), (
            Violin,
        )),
    (_("Plucked strings"),
        ()),
    (_("Woodwinds"), (
            SopraninoSax,
            SopranoSax,
            AltoSax,
            TenorSax,
            BaritoneSax,
            BassSax,
        )),
    (_("Brass"), (

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


