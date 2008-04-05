"""
LilyKDE module to run Rumor
"""

import os, re
from subprocess import Popen, PIPE

from qt import *
from kdecore import KStandardDirs, KProcess

import kate
import kate.gui

from lilykde.util import kprocess, qstringlist2py
from lilykde import config

# Translate the messages
from lilykde.i18n import _


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





class Rumor(QFrame):
    """
    A Rumor (tool) widget.
    """
    def __init__(self, *args):
        QFrame.__init__(self, *args)

        self.p = None       # placeholder for Rumor KProcess
        self.pending = []   # stack for pending data to write

        self.mode = "keyboard"      # Temporary

        # Accept keyboard focus
        self.setFocusPolicy(QWidget.ClickFocus)

        # Big Start/stop toggle button
        r = QPushButton("REC", self)
        r.setToggleButton(True)
        r.setMinimumHeight(100)
        r.setMinimumWidth(100)
        r.setFont(QFont("Sans", 20, 75))
        r.connect(r, SIGNAL("toggled(bool)"), self.rec)
        self.recButton = r



        # Meter select (editable qcombobox defaulting to document)
        # Tempo adjustment (spinbox + long slider, 10 - 500, defaulting to doc)
        # Quantize (1,2,4,8,16,32,64 or 128, default to 16)
        # Step recording: (checkbox, disables the three controls above)
        # Key signature select (any lilypond pitch, defaulting to document)

        # Input Select (button with popup menu)
        # Output select (button with popup menu)

        # Smaller options:
        # - language (any of the lily languages, defaulting to document)
        # - no-chords (Mono: checkbox)
        # - explicit-durations (checkbox)
        # - absolute-ptiches (checkbox)

        # in Settings page:
        # - Metronome settings (creating a scm script that rumor loads)


    def rec(self, start):
        """
        start = bool: True or False
        Start or stop Rumor.
        """
        if start:
            self._startRumor()
        else:
            self._stopRumor()

    def _startRumor(self):
        """ Start Rumor """
        # first collect some data:
        # - indent of current line
        self.indent = re.match(r'\s*', kate.view().currentLine).group()

        # Here we should check the user settings (meter, lang, key etc.)
        # if "Default" is selected, try to determine in a really unintelligent
        # way!
        meter = "4/4"   # FIXME

        # - text from start to cursor
        text = kate.document().fragment((0, 0), kate.view().cursor.position)
        # - find the latest \time command:
        m = re.compile(r'.*\\time\s*(\d+/(1|2|4|8|16|32|64|128))(?!\d)',
            re.DOTALL).match(text)
        if m:
            meter = m.group(1)
        # - determine lily language
        m = re.compile(r'.*\\include\s*"('
            "nederlands|english|deutsch|norsk|svenska|suomi|"
            "italiano|catalan|espanol|portuges|vlaams"
            r')\.ly"', re.DOTALL).match(text)
        if m:
            lang = m.group(1)[:2]
            if lang == "po": lang = "es"
            elif lang == "su": lang = "de"
            elif lang == "en" and not re.match(r'\b[a-g](flat|sharp)\b', text):
                lang == "en-short"
            elif lang == "vl":
                # "vlaams" is not supported by Rumor
                # TODO: rewrite the pitches output by Rumor
                lang == "it"
        else:
            lang = "ne" # the default

        # wrap in pty if keyboard used and grab keyboard
        cmd = [config("commands").get("rumor", "rumor")]
        cmd.append("--meter=" + meter)
        cmd.append("--lang=" + lang)
        cmd.append("--oss=1") # FIXME
        p = KProcess()
        if self.mode == "keyboard":
            self.setFocus()
            cmd.append("--kbd")
            # wrap in pty
            cmd[0:0] = ["python", '-c',
                "import sys,pty,signal;"
                "signal.signal(2,lambda i,j:1);"
                "pty.spawn(sys.argv[1:])"]
            comm = KProcess.All
            p.connect(p, SIGNAL("wroteStdin(KProcess*)"), self.wroteStdin)
        else:
            comm = KProcess.AllOutput
        p.setExecutable(cmd[0])
        p.setArguments(cmd[1:])
        p.connect(p, SIGNAL("processExited(KProcess*)"), self.processExited)
        p.connect(p, SIGNAL("receivedStdout(KProcess*, char*, int)"),
            self.receive)
        if p.start(KProcess.NotifyOnExit, comm):
            self.p = p
            # Rumor keyboard emulation handling
            self.lastKey = None # last played key
            self.restKey = " "  # the key that generates a rest event
        else:
            self.p = None
            self.recButton.setState(QButton.Off)

    def _stopRumor(self):
        """ Stop Rumor """
        # just send rumor a kill(2) signal (SIGINT)
        if self.isRunning():
            self.send(self.restKey)
            QTimer.singleShot(100, self._kill)

    def _kill(self):
        self.p.kill(2)

    def processExited(self):
        """ Called when Rumor exits """
        # set REC button to off, because Rumor might have exited by itself
        self.p = None
        self.recButton.setState(QButton.Off)
        if self.mode == "keyboard":
            kate.mainWidget().setFocus()

    def isRunning(self):
        return self.p is not None

    def receive(self, proc, buf, length):
        """ Writes the received text from Rumor into the Kate buffer """
        text = unicode(QString.fromUtf8(buf, length))
        text = text.replace('\n', '\n' + self.indent)
        kate.view().insertText(text)

    def send(self, text):
        """ Send keyboard input to the Rumor process """
        self.pending.append(text + '\n')
        if len(self.pending) == 1:
            text = self.pending[0]
            self.p.writeStdin(text, len(text))

    def wroteStdin(self):
        """ Called by the KProcess when ready for new stdin data """
        del self.pending[0]
        if self.pending:
            text = self.pending[0]
            self.p.writeStdin(text, len(text))

    def keyPressEvent(self, e):
        """ Called when the user presses a key. """
        if (self.isRunning() and e.key() == Qt.Key_Escape) or \
           (self.mode != "keyboard" and e.key() == Qt.Key_Space):
            self.recButton.toggle()
        elif self.mode == "keyboard" and self.isRunning() and \
                not e.isAutoRepeat() and not e.text().isEmpty():
            # pass key to Rumor, TODO: make repeats possible
            key = str(e.text())
            if key == self.restKey or key != self.lastKey:
                self.send(key)
                self.lastKey = key
            else:
                self.send(self.restKey + key)



# Main stuff
tool = kate.gui.Tool(_("Rumor"), "ly", kate.gui.Tool.bottom)
rumor = Rumor(tool.widget)
show = tool.show
hide = tool.hide
