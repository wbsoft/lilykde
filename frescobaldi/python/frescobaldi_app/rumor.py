# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
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
Frescobaldi module to run Rumor
"""

import os, re, sys
from subprocess import Popen, PIPE

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.ktexteditor import KTextEditor

import ly.key
from frescobaldi_app.widgets import ProcessButtonBase, TempoControl

class RumorPanel(QWidget):
    def __init__(self, tool):
        QWidget.__init__(self)
        self.mainwin = tool.mainwin
        self._rumorSettings = None
        
        layout = QGridLayout(self)
        
        # large start-stop toggle button
        layout.addWidget(RumorButton(self), 0, 0, 3, 1)
        
        # Tempo adjustment (spinbox + long slider)
        t = TempoControl()
        layout.addWidget(t.spinbox, 0, 2)
        hb = QHBoxLayout()
        layout.addLayout(hb, 0, 3)
        hb.addWidget(t.tapButton)
        hb.addWidget(t.slider)
        self.tempo = t
        
        # Meter select (editable qcombobox defaulting to document)
        self.meter = QComboBox()
        self.meter.setEditable(True)
        self.meter.addItems((
            AUTO(),
            '1/4', '2/4', '3/4', '4/4', '5/4', '6/4',
            '2/2', '3/2',
            '3/8', '6/8', '9/8', '12/8',
            '3/16',
            ))
        self.meter.setValidator(QRegExpValidator(QRegExp(
            re.escape(AUTO()) + "|[1-9][0-9]*/(1|2|4|8|16|32|64|128)"),
            self.meter))
        self.meter.setToolTip(i18n(
            "The meter to use. Leave 'Auto' to let Frescobaldi determine "
            "the meter from the LilyPond document."))
        layout.addWidget(self.meter, 1, 2)

        # Quantize (1,2,4,8,16,32,64 or 128, default to 16)
        hb = QHBoxLayout()
        layout.addLayout(hb, 1, 3)
        l = QLabel(i18n("Quantize:"))
        hb.addWidget(l)
        self.quantize = QComboBox()
        self.quantize.addItems([str(2**i) for i in range(8)])
        self.quantize.setCurrentIndex(4)
        self.quantize.setToolTip(i18n(
            "The shortest note duration to use."))
        hb.addWidget(self.quantize)
        l.setBuddy(self.quantize)

        # Step recording: (checkbox, disables the three controls above)
        self.step = QCheckBox(i18n("Step"))
        self.step.setToolTip(i18n(
            "Record LilyPond input note by note, without durations."))
        hb.addWidget(self.step)

        # Monophonic input (no chords)
        self.mono = QCheckBox(i18n("Mono"))
        self.mono.setToolTip(i18n(
            "Record monophonic input, without chords."))
        hb.addWidget(self.mono)

        # Key signature select (any lilypond pitch, defaulting to document)
        self.keysig = QComboBox()
        self.keysig.addItem(AUTO())
        self.keysig.addItems(["%d" % i for i in range(-7, 1)])
        self.keysig.addItems(["%+d" % i for i in range(1, 8)])
        self.keysig.setToolTip(i18n(
            "The number of accidentals. A negative number designates flats. "
            "Leave 'Auto' to let Frescobaldi determine the key signature from "
            "the LilyPond document."))
        layout.addWidget(self.keysig, 2, 2)

        # labels for controls:
        l = QLabel(i18n("Tempo:"))
        l.setBuddy(self.tempo.spinbox)
        layout.addWidget(l, 0, 1)
        l = QLabel(i18n("Meter:"))
        l.setBuddy(self.meter)
        layout.addWidget(l, 1, 1)
        l = QLabel(i18n("Key:"))
        l.setBuddy(self.keysig)
        layout.addWidget(l, 2, 1)

        hb = QHBoxLayout()
        layout.addLayout(hb, 2, 3)

        # Timidity button
        self.timidity = TimidityButton(self)
        hb.addWidget(self.timidity)

        # Button 'More Settings'
        sb = QPushButton(i18n("Configure..."))
        sb.setToolTip(i18n("Adjust more settings, like MIDI input and output."))
        QObject.connect(sb, SIGNAL("clicked()"), self.showRumorSettings)
        hb.addWidget(sb)

        # Save Button
        sb = QPushButton(i18n("Save"))
        sb.setToolTip(i18n("Set these settings as default."))
        QObject.connect(sb, SIGNAL("clicked()"), self.saveSettings)
        hb.addWidget(sb)

        self.loadSettings()


    def saveSettings(self):
        """ Saves the settings to lilykderc """
        conf = config("rumor")
        conf.writeEntry("tempo", QVariant(self.tempo.tempo()))
        conf.writeEntry("quantize", self.quantize.currentText())
        conf.writeEntry("step", QVariant(self.step.isChecked()))
        conf.writeEntry("mono", QVariant(self.mono.isChecked()))
        conf.writeEntry("meter", autofy(self.meter.currentText()))
        conf.writeEntry("keysig", autofy(self.keysig.currentText()))
        conf.writeEntry("timidity", QVariant(self.timidity.isChecked()))
        self.showMessage(i18n("Settings have been saved."), 1000)

    def loadSettings(self):
        """ Loads the settings from lilykderc """
        conf = config("rumor")
        self.tempo.setTempo(conf.readEntry("tempo", QVariant(100)).toInt()[0])
        setComboBox(self.quantize, conf.readEntry("quantize", "16"))
        self.step.setChecked(conf.readEntry("step", QVariant(False)).toBool())
        self.mono.setChecked(conf.readEntry("mono", QVariant(False)).toBool())
        setComboBox(self.meter, unautofy(conf.readEntry("meter", "auto")))
        setComboBox(self.keysig, unautofy(conf.readEntry("meter", "auto")))
        if conf.readEntry("timidity", QVariant(False)).toBool():
            self.timidity.start()

    def showRumorSettings(self):
        if not self._rumorSettings:
            self._rumorSettings = RumorSettings(self.mainwin)
        self._rumorSettings.show()
        
    def showMessage(self, msg, timeout=0):
        self.mainwin.statusBar().showMessage(msg, timeout)

    def getRumorArguments(self):
        """
        Return the arguments needed to run Rumor conform the user's settings,
        also set some state variables in self from configuration.
        
        """
        conf = config("rumor")
        args = []
        # indent of current line
        self.indent = re.match(r'\s*',
            self.mainwin.currentLineText()[:self.mainwin.currentColumn()]
            ).group()
        # text from start to cursor
        v = self.mainwin.view()
        d, cursor = v.document(), v.cursorPosition()
        text = unicode(
            d.text(KTextEditor.Range(0, 0, cursor.line(), cursor.column())))
        
        # Language
        lang = conf.readEntry("language", "auto")
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
        args.append("--lang=%s" % lang)

        # Step recording?
        if self.step.isChecked():
            args.append("--flat")
        else:
            # No, set tempo, quantization and meter
            args.append("--tempo=%d" % self.tempo.tempo())
            args.append("--grain=%s" % self.quantize.currentText())
            meter = autofy(self.meter.currentText())
            if meter == "auto":
                # determine from document - find the latest \time command:
                m = re.compile(r'.*\\time\s*(\d+/(1|2|4|8|16|32|64|128))(?!\d)',
                    re.DOTALL).match(text)
                if m:
                    meter = m.group(1)
                else:
                    meter = '4/4'
            args.append("--meter=%s" % meter)

        # Key signature
        acc = autofy(self.keysig.currentText())
        if acc == "auto":
            # Determine key signature from document.
            m = re.compile(
                r'.*\\key\s+(' + '|'.join(ly.key.key2num[lang].keys()) + r')\s*\\'
                r'(major|minor|(ion|dor|phryg|(mixo)?lyd|aeol|locr)ian)\b',
                re.DOTALL).match(text)
            if m:
                pitch, mode = m.group(1,2)
                acc = ly.key.key2num[lang][pitch] + modes[mode]
            else:
                acc = 0
        else:
            acc == int(acc)
        acc += 2    # use sharps for half tones leading to second, fifth, sixth
        args.append("--key=%s" % ly.key.num2key[lang][bound(acc, -8, 12)])

        # Monophonic input?
        if self.mono.isChecked():
            args.append("--no-chords")

        # Absolute pitches?
        if conf.readEntry("absolute pitches", QVariant(False)).toBool():
            args.append("--absolute-pitches")

        # Explicit durations?
        if conf.readEntry("explicit durations", QVariant(False)).toBool():
            args.append("--explicit-durations")

        # No barlines?
        self.noBarlines = conf.readEntry("no barlines", QVariant(False)).toBool()

        # No dots?
        if conf.readEntry("no dots", QVariant(False)).toBool():
            args.append("--no-dots")

        # Legato?
        if conf.readEntry("legato", QVariant(False)).toBool():
            args.append("--legato")

        # Strip rests?
        if conf.readEntry("strip rests", QVariant(False)).toBool():
            args.append("--strip")

        # Guile scripts?
        scripts = map(unicode, conf.readEntry("scripts", ()))
        if scripts:
            paths = dict((os.path.basename(path), path) for path in rumorScripts())
            for s in scripts:
                if s in paths:
                    args.append("--script=%s" % paths[s])

        # input/output
        i = unicode(conf.readEntry("midi in", "oss:1"))
        o = unicode(conf.readEntry("midi out", "oss:1"))
        if o.startswith('oss:'):
            args.append("--oss=%s" % o.split(":")[1])
        elif re.match(r"\d", o) and re.match(r"\d", i):
            args.append("--alsa=%s,%s" % (i, o))
        elif re.match(r"\d", o):
            args.append("--alsa=%s" % o)
        self.keyboardEmu = i == "keyboard"

        if self.keyboardEmu:
            args.append("--kbd")
        return args
    
    def insertRumorOutput(self, text):
        """ Insert the output received from Rumor in the editor. """
        text = text.replace('\r', '')       # remove carriage returns
        if text == '\n':
            return  # discard single newline, typically output on exit.
        if self.noBarlines:
            text = text.replace('|', '')
        text = text.replace('\n\n', '\n')   # avoid empty lines
        text = text.replace('\n', '\n' + self.indent)
        self.mainwin.view().insertText(text)
        
        
class RumorButton(ProcessButtonBase, QToolButton):
    def __init__(self, panel):
        super(RumorButton, self).__init__()
        self.setIconSize(QSize(48, 48))
        self.setIcon(KIcon("media-record"))
        self.setText(i18n("Record"))
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setToolTip(i18n("Start or stop Rumor MIDI-recording."))
        self.panel = panel
        
    def initializeProcess(self, p):
        rumor = config("commands").readEntry("rumor", "rumor")
        cmd = [rumor] + self.panel.getRumorArguments()
        if self.panel.keyboardEmu:
            # Run Rumor in a pty when keyboard input is used.
            runpty = KGlobal.dirs().findResource("appdata", "lib/runpty.py")
            cmd[0:0] = [sys.executable, runpty]
        p.setProgram(cmd)
        p.setOutputChannelMode(KProcess.OnlyStdoutChannel)
        
    def started(self):
        self.panel.showMessage(i18n("Rumor is recording, press ESC to stop."))
        self.panel.mainwin.installEventFilter(self)
        self.panel.installEventFilter(self)
        if self.panel.keyboardEmu:
            self.panel.setFocus()
            
    def stop(self):
        # Rumor wants to be killed with SIGINT
        os.kill(self.process().pid(), 2)
        
    def readOutput(self, text):
        self.panel.insertRumorOutput(unicode(text))

    def finished(self, exitCode, exitStatus):
        self.panel.showMessage(i18n("Rumor stopped."), 1000)
        self.panel.mainwin.removeEventFilter(self)
        self.panel.removeEventFilter(self)
        self.panel.mainwin.view().setFocus()
        
    def eventFilter(self, obj, ev):
        """
        Event filter:
        on mainwin to catch the ESC key to stop Rumor.
        on self to also send input keys to Rumor.
        """
        if ev.type() != QEvent.KeyPress:
            return False
        elif ev.key() == Qt.Key_Escape:
            self.stop()
            return True
        elif obj == self.panel and self.panel.keyboardEmu:
            if ev.key() in (Qt.Key_Enter, Qt.Key_Return):
                self.panel.mainwin.view().insertText('\n' + self.panel.indent)
                return True
            elif not ev.isAutoRepeat() and not ev.text().isEmpty():
                self.writeInput(ev.text().toLocal8Bit())
                return True
        return False

            
class TimidityButton(ProcessButtonBase, QPushButton):
    def __init__(self, *args):
        super(TimidityButton, self).__init__(*args)
        self.setText(i18n("TiMidity"))
        self.setToolTip(i18n("Start or stop the TiMidity ALSA MIDI client."))
        self.setIcon(KIcon("media-playback-start"))

    def initializeProcess(self, p):
        cmd, err = KShell.splitArgs(config("commands").readEntry("timidity",
            default_timidity_command))
        if err == KShell.NoError:
            p.setProgram(cmd)
        else:
            pass # TODO: warn user about incorrect command


class RumorSettings(KDialog):
    """
    Dialog with more Rumor settings.
    """
    def __init__(self, mainwin):
        KDialog.__init__(self, mainwin)
        self.setCaption(i18n("Rumor Settings"))
        self.setModal(True)
        self.setButtons(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel))

        layout = QGridLayout(self.mainWidget())
        # MIDI input and output.
        # Get the list of available OSS and ALSA devices
        oslist = [('oss:%d' % i, i18n("OSS device %1", i))
            for i in range(getOSSnrMIDIs())]
        i = oslist + parseAconnect('i') + [("keyboard", i18n("Keyboard"))]
        o = oslist + parseAconnect('o')
        self.ilist, ititles = map(list, zip(*i))
        self.olist, otitles = map(list, zip(*o))

        # input
        layout.addWidget(QLabel(i18n("MIDI input:")), 1, 0)
        self.ibut = QComboBox()
        self.ibut.addItems(ititles)
        self.ibut.setToolTip(i18n("MIDI input to use. Choose 'Keyboard' if "
            "you want to play on the keyboard of your computer."))
        layout.addWidget(self.ibut, 1, 1)

        # output
        layout.addWidget(QLabel(i18n("MIDI output:")), 2, 0)
        self.obut = QComboBox()
        self.obut.addItems(otitles)
        self.obut.setToolTip(i18n("MIDI output to use."))
        layout.addWidget(self.obut, 2, 1)

        # Language
        layout.addWidget(QLabel(i18n("Language:")), 3, 0)
        self.lang = QComboBox()
        self.lang.addItems((
            AUTO(), 'ne', 'en', 'en-short', 'de', 'no', 'sv', 'it', 'ca', 'es'))
        self.lang.setToolTip(i18n("The LilyPond language you want Rumor to "
            "output the pitches in."))
        layout.addWidget(self.lang, 3, 1)

        hb = QHBoxLayout()
        layout.addLayout(hb, 4, 0, 1, 2)
        # explicit durations
        self.explDur = QCheckBox(i18n("Explicit durations"))
        self.explDur.setToolTip(i18n(
            "Add a duration after every note, even if it is the same as the "
            "preceding note."))
        hb.addWidget(self.explDur)

        # absolute pitches
        self.absPitches = QCheckBox(i18n("Absolute pitch"))
        self.absPitches.setToolTip(i18n(
            "Use absolute pitches instead of relative."))
        hb.addWidget(self.absPitches)

        hb = QHBoxLayout()
        layout.addLayout(hb, 5, 0, 1, 2)
        # No Barlines
        self.noBar = QCheckBox(i18n("No barlines"))
        self.noBar.setToolTip(i18n(
            "Filter the barlines out of Rumor's output."))
        hb.addWidget(self.noBar)

        # No dots
        self.noDots = QCheckBox(i18n("No dots"))
        self.noDots.setToolTip(i18n(
            "Do not use dotted notes, but ties instead."))
        hb.addWidget(self.noDots)

        # Legato
        self.legato = QCheckBox(i18n("Legato"))
        self.legato.setToolTip(i18n("Do not use rests, but give all notes "
            "the maximum length."))
        hb.addWidget(self.legato)

        # Strip rests
        self.stripRests = QCheckBox(i18n("Strip rests"))
        self.stripRests.setToolTip(i18n(
            "Strip leading and trialing rests from output."))
        hb.addWidget(self.stripRests)

        layout.addWidget(QLabel(i18n(
            "Guile scripts to load:")), 6, 0, 1, 2)

        # Guile scripts listview
        self.scripts = QTreeWidget()
        self.scripts.setRootIsDecorated(False)
        self.scripts.setHeaderLabels((i18n("Name"), i18n("Description")))
        self.scripts.setToolTip(i18n(
            "Here you can select which Guile scripts you want Rumor to load. "
            "Check \"What's this\" for more information."))
        localRumorDir = "~/.kde/share/apps/frescobaldi/rumor/"
        self.scripts.setWhatsThis(i18n(
            "Here you can select which Guile scripts you want Rumor to load. "
            "You can add your own scripts by putting them in %1. "
            "If the first line of your script starts with a semicolon (;) "
            "that line will be shown as description.", localRumorDir))
        layout.addWidget(self.scripts, 7, 0, 1, 2)
        
    def show(self):
        self.loadSettings()
        KDialog.show(self)

    def done(self, result):
        if result:
            self.saveSettings()
        KDialog.done(self, result)

    def loadSettings(self):
        """ Load the settings """
        conf = config("rumor")
        if 'oss:1' in self.ilist:
            idefault = odefault = 'oss:1'
        else:
            idefault = 'kbd'
            odefault = self.olist[max(1, len(self.olist)-1)]
        i = conf.readEntry("midi in", idefault)
        o = conf.readEntry("midi out", odefault)
        if i in self.ilist:
            self.ibut.setCurrentIndex(self.ilist.index(i))
        if o in self.olist:
            self.obut.setCurrentIndex(self.olist.index(o))
        setComboBox(self.lang, unautofy(conf.readEntry("language", "auto")))
        self.absPitches.setChecked(conf.readEntry("absolute pitches", QVariant(False)).toBool())
        self.explDur.setChecked(conf.readEntry("explicit durations", QVariant(False)).toBool())
        self.noBar.setChecked(conf.readEntry("no barlines", QVariant(False)).toBool())
        self.noDots.setChecked(conf.readEntry("no dots", QVariant(False)).toBool())
        self.legato.setChecked(conf.readEntry("legato", QVariant(False)).toBool())
        self.stripRests.setChecked(conf.readEntry("strip rests", QVariant(False)).toBool())
        # Guile scripts
        self.scripts.clear()
        scripts = conf.readEntry("scripts", ())
        for path in rumorScripts():
            name = os.path.basename(path)
            try:
                desc = open(path).readline().strip()
                item = QTreeWidgetItem(self.scripts)
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(0, (name in scripts) and Qt.Checked or Qt.Unchecked)
                item.setText(0, name)
                if desc.startswith(';'):
                    item.setText(1, desc.strip(";"))
            except IOError:
                pass
        for col in 0, 1:
            self.scripts.resizeColumnToContents(col)

    def saveSettings(self):
        """ Save the settings """
        conf = config("rumor")
        conf.writeEntry("midi in", self.ilist[self.ibut.currentIndex()])
        conf.writeEntry("midi out", self.olist[self.obut.currentIndex()])
        conf.writeEntry("language", autofy(self.lang.currentText()))
        conf.writeEntry("absolute pitches", QVariant(self.absPitches.isChecked()))
        conf.writeEntry("explicit durations", QVariant(self.explDur.isChecked()))
        conf.writeEntry("no barlines", QVariant(self.noBar.isChecked()))
        conf.writeEntry("no dots", QVariant(self.noDots.isChecked()))
        conf.writeEntry("legato", QVariant(self.legato.isChecked()))
        conf.writeEntry("strip rests", QVariant(self.stripRests.isChecked()))
        # Read script treeview
        names = []
        for row in range(self.scripts.topLevelItemCount()):
            item = self.scripts.topLevelItem(row)
            if item.checkState(0) == Qt.Checked:
                names.append(item.text(0))
        conf.writeEntry("scripts", names)



def parseAconnect(channel):
    """
    Returns a list of tuples ('0:0', 'Port name') of the
    available MIDI ports for either reading (channel = 'i')
    or writing (channel = 'o')
    """
    option = channel == 'i' and '--input' or '--output'
    cmd = unicode(config("commands").readEntry("aconnect", "aconnect"))
    res = []
    for line in Popen([cmd, option], stdout=PIPE).communicate()[0].splitlines():
        m = re.match(r"client\s*(\d+)|\s*(\d+)\s+'([^']+)'", line)
        if m.group(1):
            client = m.group(1)
        elif client != "0":
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

def rumorScripts():
    return map(unicode, KGlobal.dirs().findAllResources("appdata", "rumor/*"))

def config(group="rumor"):
    return KGlobal.config().group(group)

def bound(x, minValue, maxValue):
    """ Clips x according to the boundaries minValue and maxValue """
    return max(minValue, min(maxValue, x))

AUTO = lambda: unicode(i18n("Auto"))
autofy = lambda s: s == AUTO() and "auto" or s
unautofy = lambda s: s == "auto" and AUTO() or s

def setComboBox(c, text):
    """
    Set a combobox to some value. To compensate for the loss
    of QComboBox.setCurrentText()...
    """
    index = c.findText(text)
    if index == -1:
        if c.isEditable():
            c.addItem(text)
            c.setCurrentIndex(c.count() - 1)
    else:
        c.setCurrentIndex(index)
        

default_timidity_command = "timidity -iA -B2,8 -Os -EFreverb=0"