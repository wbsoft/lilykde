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
from lilykde.widgets import ProcessButton
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


class RumorData(object):
    """ Collects all data before starting Rumor """
    def __init__(self):
        # - indent of current line
        self.indent = re.match(r'\s*',
            kate.view().currentLine[:kate.view().cursor.position[1]]).group()

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
        self.keyboardEmu = True # FIXME
        if self.keyboardEmu:
            cmd.append("--kbd")

        self.command = cmd


class RumorButton(ProcessButton):
    """
    The button that starts and stops Rumor.
    The parent is the widget object that holds the button
    and other controls.
    """

    restKey = " "

    def __init__(self, parent):
        ProcessButton.__init__(self, "REC", parent)
        self.setMinimumHeight(100)
        self.setMinimumWidth(100)
        self.setFont(QFont("Sans", 20, 75))

    def onStart(self):
        """ Here we construct the command etc. """
        self.d = RumorData()
        self.command = self.d.command
        if self.d.keyboardEmu:
            self.parent().setFocus()
            self.comm = KProcess.All
            self.pty = True
        else:
            self.comm = KProcess.AllOutput
            self.pty = False

    def receivedStdout(self, proc, buf, length):
        """ Writes the received text from Rumor into the Kate buffer """
        text = unicode(QString.fromUtf8(buf, length))
        text = text.replace('\n', '\n' + self.d.indent)
        kate.view().insertText(text)

    def started(self):
        self.lastKey = None

    def stop(self):
        """ Stop the process """
        if self.d.keyboardEmu:
            self.send(self.restKey)
            QTimer.singleShot(100, lambda:
                ProcessButton.stop(self, 2))
        else:
            ProcessButton.stop(self, 2)

    def stopped(self):
        if self.d.keyboardEmu:
            kate.mainWidget().setFocus()

    def sendkey(self, key):
        # pass key to Rumor, TODO: make repeats possible
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

        # Big Start/stop toggle button
        self.r = RumorButton(self)


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

    def keyPressEvent(self, e):
        """ Called when the user presses a key. """
        if (self.r.isRunning() and e.key() == Qt.Key_Escape) or \
           (not self.r.d.keyboardEmu and e.key() == Qt.Key_Space):
            self.r.animateClick()
        elif self.r.d.keyboardEmu and self.r.isRunning() and \
                not e.isAutoRepeat() and not e.text().isEmpty():
            # pass key to Rumor
            self.r.sendkey(str(e.text()))



# Main stuff
tool = kate.gui.Tool(_("Rumor"), "ly", kate.gui.Tool.bottom)
rumor = Rumor(tool.widget)
show = tool.show
hide = tool.hide
