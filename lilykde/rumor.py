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


class Rumor(QFrame):
    """
    A Rumor (tool) widget.
    """
    def __init__(self, *args):
        QFrame.__init__(self, *args)

        self.p = None               # placeholder for Rumor KProcess
        self.pending = []           # stack for pending data to write

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
            self.startRumor()
        else:
            self.stopRumor()

    def startRumor(self):
        """ Start Rumor """
        # wrap in pty if keyboard used and grab keyboard
        rumor = config("commands").get("rumor", "rumor")
        cmd = [rumor]
        cmd.append("--oss=1") # FIXME
        p = KProcess()
        if self.mode == "keyboard":
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
        p.connect(p, SIGNAL("processExited(KProcess*)"), self.stopped)
        p.connect(p, SIGNAL("receivedStdout(KProcess*, char*, int)"),
            self.receive)
        if p.start(KProcess.NotifyOnExit, comm):
            self.p = p
        else:
            self.p = None
            self.recButton.setState(QButton.Off)

    def stopRumor(self):
        """ Stop Rumor """
        # just send rumor a kill(2) signal (SIGINT)
        self.p.kill(2)

    def stopped(self):
        """ Called when Rumor exits """
        # set REC button to off, because Rumor might have exited by itself
        self.recButton.setState(QButton.Off)
        # release the grab, if keyboard is used

        self.p = None

    def isRunning(self):
        return self.p is not None

    def receive(self, proc, buf, length):
        """ Writes the received text from Rumor into the Kate buffer """
        text = unicode(QString.fromUtf8(buf, length))
        kate.view().insertText(text)

    def send(self, text):
        """ Send keyboard input to the Rumor process """
        self.pending.append(text)
        if len(self.pending) == 1:
            text = self.pending[0]
            self.p.writeStdin(text, len(text))

    def wroteStdin(self):
        """ Called by the KProcess when ready for new stdin data """
        del self.pending[0]
        if self.pending:
            text = self.pending[0]
            self.p.writeStdin(text, len(text))


tool = kate.gui.Tool(_("Rumor"), "ly", kate.gui.Tool.bottom)
rumor = Rumor(tool.widget)
show = tool.show
hide = tool.hide
