"""
LilyKDE module to run Rumor
"""

import os, re
from time import time
from subprocess import Popen, PIPE

from qt import *
from kdecore import KStandardDirs, KProcess

import kate
import kate.gui

from lilykde.util import kprocess, qstringlist2py, py2qstringlist
from lilykde.widgets import error, ProcessButton
from lilykde import config

# Translate the messages
from lilykde.i18n import _

def rdict(d):
    """ reverse a dict """
    return dict((v,k) for k,v in d.iteritems())

pitches = {
    'ne': {
        'fes':-8, 'ces':-7, 'ges':-6, 'des':-5, 'as':-4,
        'aes':-4, 'es':-3, 'ees':-3, 'bes':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'b':5, 'fis':6, 'cis':7,
        'gis':8, 'dis':9, 'ais':10, 'eis':11, 'bis':12
        },
    'en-short': {
        'ff':-8, 'cf':-7, 'gf':-6, 'df':-5,
        'af':-4, 'ef':-3, 'bf':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'b':5, 'fs':6, 'cs':7,
        'gs':8, 'ds':9, 'as':10, 'es':11, 'bs':12
        },
    'en': {
        'fflat':-8, 'cflat':-7, 'gflat':-6, 'dflat':-5,
        'aflat':-4, 'eflat':-3, 'bflat':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'b':5, 'fsharp':6, 'csharp':7,
        'gsharp':8, 'dsharp':9, 'asharp':10, 'esharp':11, 'bsharp':12
        },
    'de': {
        'fes':-8, 'ces':-7, 'ges':-6, 'des':-5, 'as':-4,
        'aes':-4, 'es':-3, 'ees':-3, 'b':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'h':5, 'fis':6, 'cis':7,
        'gis':8, 'dis':9, 'ais':10, 'eis':11, 'his':12
        },
    'sv': {
        'fess':-8, 'cess':-7, 'gess':-6, 'dess':-5, 'ass':-4,
        'aess':-4, 'ess':-3, 'eess':-3, 'b':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'h':5, 'fiss':6, 'ciss':7,
        'giss':8, 'diss':9, 'aiss':10, 'eiss':11, 'hiss':12
        },
    # no = (de|sv), su = de
    'it': {
        'fab':-8, 'dob':-7, 'solb':-6, 'reb':-5, 'lab':-4,
        'mib':-3, 'sib':-2, 'fa':-1,
        'do':0, 'sol':1, 're':2, 'la':3, 'mi':4, 'si':5, 'fad':6, 'dod':7,
        'sold':8, 'red':9, 'lad':10, 'mid':11, 'sid':12
        },
    'es': {
        'fab':-8, 'dob':-7, 'solb':-6, 'reb':-5, 'lab':-4,
        'mib':-3, 'sib':-2, 'fa':-1,
        'do':0, 'sol':1, 're':2, 'la':3, 'mi':4, 'si':5, 'fas':6, 'dos':7,
        'sols':8, 'res':9, 'las':10, 'mis':11, 'sis':12
        },
    # ca = (it|es), po = es
    'vl': {
        'fab':-8, 'dob':-7, 'solb':-6, 'reb':-5, 'lab':-4,
        'mib':-3, 'sib':-2, 'fa':-1,
        'do':0, 'sol':1, 're':2, 'la':3, 'mi':4, 'si':5, 'fak':6, 'dok':7,
        'solk':8, 'rek':9, 'lak':10, 'mik':11, 'sik':12
        },
}

revpitches = dict((lang, rdict(p)) for lang,p in pitches.iteritems())


# Handling of translated text in comboboxes
AUTO = _("Auto")

def autofy(s):
    return s == AUTO and "auto" or s

def unautofy(s):
    return s == "auto" and AUTO or s

# find Rumor support files
def getRumorFiles(pattern = "*"):
    """
    Returns a list of all files matching pattern in lilykde/rumor/
    """
    return qstringlist2py(KStandardDirs.findAllResources("data",
        os.path.join("lilykde", "rumor", pattern)))

def parseAconnectOutput(channel):
    """
    Returns a list of tuples ('0:0', 'Port name') of the
    available MIDI ports for either reading (channel = 'i')
    or writing (channel = 'o')
    """
    option = channel == 'i' and '--input' or '--output'
    cmd = config("commands").get("aconnect", "aconnect")
    res = []
    for line in Popen([cmd, option], stdout=PIPE).communicate()[0].splitlines():
        m = re.match(r"client\s*(\d+)|\s*(\d+)\s+'([^']+)'", line)
        if m.group(1):
            client = m.group(1)
        else:
            port, name = m.group(2,3)
            res.append(("%s:%s" % (client, port), name.strip()))
    return res

def getOSSnrMIDIs():
    """
    Get the number of MIDI devices when OSS is used
    """
    try:
        import struct, fcntl, ossaudiodev
        return struct.unpack('i', fcntl.ioctl(
            open("/dev/sequencer"),
            ossaudiodev.SNDCTL_SEQ_NRMIDIS,
            struct.pack('i', 0)))[0]
    except:
        return 0


class TimidityButton(ProcessButton):
    """ A Button to start or stop Timidity as an ALSA client """
    def __init__(self, parent):
        ProcessButton.__init__(self, _("TiMidity"), parent)
        QToolTip.add(self, _("Start or stop the TiMidity ALSA MIDI client."))

    def onStart(self):
        self.command = config("commands").get("timidity",
            'timidity -iA -B2,8 -Os -EFreverb=0')

    def started(self):
        self.parent().status.message(_("TiMidity successfully started."), 2000)

    def stopped(self):
        self.parent().status.message(_("TiMidity stopped."), 2000)

    def failed(self):
        error(_(
            "Could not start TiMidity. Please try the command\n%s\nin a "
            "terminal to find out what went wrong.") % self.command,
            timeout = 10)


class RumorButton(ProcessButton):
    """
    The button that starts and stops Rumor.
    The parent is the widget object that holds the button
    and other controls.
    """

    restKey = " "

    def __init__(self, parent):
        ProcessButton.__init__(self, _("REC"), parent)
        self.setFont(QFont("Sans", 20, 75))
        self.setMinimumHeight(100)
        self.setMinimumWidth(100)
        self.setMaximumHeight(200)
        QToolTip.add(self, _("Start or stop Rumor"))

    def heightForWidth(self, w):
        return min(max(w, 100), 200)

    def onStart(self):
        """ Here we construct the command etc. """
        p = self.parent()
        p.saveSettings()
        conf = config("rumor")
        # - indent of current line
        self.indent = re.match(r'\s*',
            kate.view().currentLine[:kate.view().cursor.position[1]]).group()

        # Here we should check the user settings (meter, lang, key etc.)
        # if "Default" is selected, try to determine in a really unintelligent
        # way!

        # - text from start to cursor
        text = kate.document().fragment((0, 0), kate.view().cursor.position)
        cmd = [config("commands").get("rumor", "rumor")]
        # Language
        lang = conf.get("language", "auto")
        if lang not in (
                'ne', 'en', 'en-short', 'de', 'no', 'sv', 'it', 'ca', 'es'):
            # determine lily language from document
            m = re.compile(r'.*\\include\s*"('
                "nederlands|english|deutsch|norsk|svenska|suomi|"
                "italiano|catalan|espanol|portuges|vlaams"
                r')\.ly"', re.DOTALL).match(text)
            if m:
                lang = m.group(1)[:2]
                if lang == "po": lang = "es"
                elif lang == "su": lang = "de"
                elif lang == "en" and not re.match(
                        r'\b[a-g](flat|sharp)\b', text):
                    lang == "en-short"
                elif lang == "vl":
                    # "vlaams" is not supported by Rumor
                    # TODO: rewrite the pitches output by Rumor :-)
                    lang == "it"
            else:
                lang = "ne" # the default
        cmd.append("--lang=%s" % lang)

        # Step recording?
        if int(conf.get("step", "0")):
            cmd.append("--flat")
        else:
            # No, set tempo, quantization and meter
            cmd.append("--tempo=%s" % conf.get("tempo", "100"))
            cmd.append("--grain=%s" % conf.get("quantize", "16"))
            meter = conf.get("meter", "auto")
            if meter == "auto":
                # determine from document - find the latest \time command:
                m = re.compile(r'.*\\time\s*(\d+/(1|2|4|8|16|32|64|128))(?!\d)',
                    re.DOTALL).match(text)
                if m:
                    meter = m.group(1)
                else:
                    meter = '4/4'
            cmd.append("--meter=%s" % meter)

        # Monophonic input?
        if int(conf.get("mono", "0")):
            cmd.append("--no-chords")

        cmd.append("--oss=1") # FIXME
        self.keyboardEmu = True # FIXME

        if self.keyboardEmu:
            cmd.append("--kbd")
            p.setFocus()
            self.comm = KProcess.All
            self.pty = True
        else:
            self.comm = KProcess.AllOutput
            self.pty = False
        self.command = cmd

    def receivedStdout(self, proc, buf, length):
        """ Writes the received text from Rumor into the Kate buffer """
        text = unicode(QString.fromUtf8(buf, length))
        text = text.replace('\n', '\n' + self.indent)
        kate.view().insertText(text)

    def started(self):
        self.parent().status.message(_(
            "Rumor is recording, press ESC to stop."))
        self.lastKey = None

    def stop(self):
        """ Stop the process """
        if self.keyboardEmu:
            self.send(self.restKey)
            QTimer.singleShot(100, lambda:
                ProcessButton.stop(self, 2))
        else:
            ProcessButton.stop(self, 2)

    def stopped(self):
        self.parent().status.clear()
        if self.keyboardEmu:
            kate.mainWidget().setFocus()

    def sendkey(self, key):
        # pass key to Rumor
        if key == self.restKey or key != self.lastKey:
            self.send(key)
            self.lastKey = key
        else:
            self.send(self.restKey + key)



class Rumor(QFrame):
    """
    A Rumor (tool) widget.
    """
    def __init__(self, *args):
        QFrame.__init__(self, *args)
        # Accept keyboard focus
        self.setFocusPolicy(QWidget.ClickFocus)
        layout = QGridLayout(self, 4, 5, 4)
        layout.setColStretch(4, 1)
        self.setMinimumHeight(120)
        self.setMaximumHeight(200)

        # Big Start/stop toggle button
        self.r = RumorButton(self)
        layout.addMultiCellWidget(self.r, 0, 3, 0, 0)

        # labels for other controls:
        layout.addWidget(QLabel(_("Tempo:"), self), 0, 1)
        layout.addWidget(QLabel(_("Meter:"), self), 1, 1)
        layout.addWidget(QLabel(_("Key:"), self), 2, 1)

        # Status line
        self.status = QStatusBar(self)
        self.status.setSizeGripEnabled(False)
        layout.addMultiCellWidget(self.status, 3, 3, 1, 4)

        # Tempo adjustment (spinbox + long slider)
        self.tempo = TempoControl(self)
        layout.addWidget(self.tempo.spinbox, 0, 2)
        hb = QHBoxLayout()
        layout.addLayout(hb, 0, 3)
        hb.addWidget(self.tempo.slider)
        hb.addWidget(self.tempo.tapButton)
#        hb.addStretch(1)

        # Meter select (editable qcombobox defaulting to document)
        self.meter = QComboBox(self)
        self.meter.setEditable(True)
        self.meter.insertStringList(py2qstringlist([
            AUTO,
            '1/4', '2/4', '3/4', '4/4', '5/4', '6/4',
            '2/2', '3/2',
            '3/8', '6/8', '9/8', '12/8',
            '3/16',
            ]))
        self.meter.setValidator(QRegExpValidator(QRegExp(
            re.escape(AUTO) + "|[1-9][0-9]*/(1|2|4|8|16|32|64|128)"),
            self.meter))
        QToolTip.add(self.meter, _(
            "The meter to use. Leave 'Auto' to let LilyKDE determine "
            "the meter from the LilyPond document."))
        layout.addWidget(self.meter, 1, 2)

        # Quantize (1,2,4,8,16,32,64 or 128, default to 16)
        hb = QHBoxLayout()
        layout.addLayout(hb, 1, 3)
        hb.addWidget(QLabel(_("Quantize:"), self))
        self.quantize = QComboBox(self)
        self.quantize.insertStringList(py2qstringlist(
            str(2**i) for i in range(8)))
        QToolTip.add(self.quantize, _(
            "The shortest note duration to use."))
        hb.addWidget(self.quantize)

        # Step recording: (checkbox, disables the three controls above)
        self.step = QCheckBox(_("Step"), self)
        QToolTip.add(self.step, _(
            "Record LilyPond input note by note, without durations."))
        hb.addWidget(self.step)

        # Monophonic input (no chords)
        self.mono = QCheckBox(_("Mono"), self)
        QToolTip.add(self.mono, _(
            "Record monophonic input, without chords."))
        hb.addWidget(self.mono)
#        hb.addStretch(1)

        # Key signature select (any lilypond pitch, defaulting to document)
        self.keysig = QComboBox(self)
        self.keysig.insertItem(AUTO)
        self.keysig.insertStringList(py2qstringlist(
            "%d" % i for i in range(-7, 1)))
        self.keysig.insertStringList(py2qstringlist(
            "%+d" % i for i in range(1, 8)))
        QToolTip.add(self.keysig, _(
            "The number of accidentals. A negative number designates flats. "
            "Leave 'Auto' to let LilyKDE determine the key signature from "
            "the LilyPond document."))
        layout.addWidget(self.keysig, 2, 2)

        # Button 'More Settings'
        hb = QHBoxLayout()
        layout.addLayout(hb, 2, 3)
        self.settingsButton = QPushButton(_("More Settings"), self)
        QToolTip.add(self.settingsButton, _(
            "Adjust more settings, like MIDI input and output."))
        hb.addWidget(self.settingsButton)

        # Timidity button
        self.timidity = TimidityButton(self)
        hb.addWidget(self.timidity)

        # Input Select (button with popup menu)
        # Output select (button with popup menu)

        # Smaller options:
        # - language (any of the lily languages, defaulting to document)
        # - no-chords (Mono: checkbox)
        # - explicit-durations (checkbox)
        # - absolute-ptiches (checkbox)

        # in Settings page:
        # - Metronome settings (creating a scm script that rumor loads)

        self.loadSettings()


    def keyPressEvent(self, e):
        """ Called when the user presses a key. """
        if not self.r.isRunning():
            return
        if e.key() == Qt.Key_Escape:
            self.r.animateClick()
        elif self.r.keyboardEmu:
            if e.key() == Qt.Key_Enter:
                kate.view().insertText('\n' + self.r.indent)
            elif not e.isAutoRepeat() and not e.text().isEmpty():
                # pass key to Rumor
                self.r.sendkey(str(e.text()))

    def saveSettings(self):
        """ Saves the settings to lilykderc """
        conf = config("rumor")
        conf["tempo"] = self.tempo.tempo()
        conf["quantize"] = self.quantize.currentText()
        conf["step"] = self.step.isChecked() and "1" or "0"
        conf["mono"] = self.mono.isChecked() and "1" or "0"
        conf["meter"] = autofy(self.meter.currentText())
        conf["keysig"] = autofy(self.keysig.currentText())
        conf["timidity"] = self.timidity.isRunning() and "1" or "0"

    def loadSettings(self):
        """ Loads the settings from lilykderc """
        conf = config("rumor")
        self.tempo.setTempo(int(conf.get("tempo", 100)))
        self.quantize.setCurrentText(conf.get("quantize", "16"))
        self.step.setChecked(bool(int(conf.get("step", "0"))))
        self.mono.setChecked(bool(int(conf.get("mono", "0"))))
        self.meter.setCurrentText(unautofy(conf.get("meter", "auto")))
        self.keysig.setCurrentText(unautofy(conf.get("meter", "auto")))
        if int(conf.get("timidity", "0")):
            self.timidity.start()


class TempoControl(object):
    """
    A combination of a spinbox, slider, and tap button to set the tempo.
    """
    minBPM = 30
    maxBPM = 400

    def __init__(self, parent):
        self.spinbox = QSpinBox(self.minBPM, self.maxBPM, 1, parent)
        self.slider = QSlider(
            self.minBPM, self.maxBPM, 1, 100, Qt.Horizontal, parent)
        self.tapButton = QPushButton(_("Tap"), parent)
        # setup signals
        QObject.connect(self.tapButton, SIGNAL("pressed()"), self.tap)
        QObject.connect(self.slider, SIGNAL("valueChanged(int)"),
            self.spinbox.setValue)
        QObject.connect(self.spinbox, SIGNAL("valueChanged(int)"),
            self.slider.setValue)
        self.slider.setMinimumWidth(200)
        QToolTip.add(self.spinbox, _(
            "The tempo in beats per minute."))
        QToolTip.add(self.tapButton, _(
            "Click this button a few times to set the tempo."))
        # init tap time
        self.time = 0.0

    def tempo(self):
        return self.spinbox.value()

    def setTempo(self, value):
        self.spinbox.setValue(value)

    def tap(self):
        """ Tap the tempo """
        self.time, t = time(), self.time
        bpm = int(60.0 / (self.time - t))
        if self.minBPM <= bpm <= self.maxBPM:
            self.setTempo(bpm)



# Main stuff
tool = kate.gui.Tool(_("Rumor"), "ly", kate.gui.Tool.bottom)
rumor = Rumor(tool.widget)
show = tool.show
hide = tool.hide
