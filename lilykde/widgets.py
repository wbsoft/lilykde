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
Widgets used in LilyKDE
"""

import os, re
from time import time
from subprocess import Popen, PIPE

from qt import *
from kdecore import KApplication, KProcess, KURL
from kdeui import KMessageBox, KTextBrowser

from lilykde import config, appdir
from lilykde.util import \
    findexe, keepspaces, htmlescapeurl, htmlescape, krun, splitcommandline

# Translate the messages
from lilykde.i18n import _


try:
    # if this fails, don't define following functions, because
    # they depend on Kate and Pate present:
    import kate

    def _popup(message, timeout=5, **a):
        a.setdefault('parent', kate.mainWidget().topLevelWidget())
        kate.gui.showPassivePopup(message, timeout, **a)

    def error(message, **a):
        _popup(message, icon="error", **a)

    def sorry(message, **a):
        _popup(message, icon="messagebox_warning", **a)

    def info(message, **a):
        _popup(message, icon="messagebox_info", **a)

    def warncontinue(message):
        return KMessageBox.warningContinueCancel(
            kate.mainWidget(), message) == KMessageBox.Continue


except ImportError:

    # These are defined when LilyKDE runs outside of Kate
    def error(message, **a):
        KMessageBox.error(KApplication.kApplication().mainWidget(), message)

    def sorry(message, **a):
        KMessageBox.sorry(KApplication.kApplication().mainWidget(), message)

    def info(message, **a):
        KMessageBox.information(
            KApplication.kApplication().mainWidget(), message)

    def warncontinue(message):
        return KMessageBox.warningContinueCancel(
            KApplication.kApplication().mainWidget(), message
            ) == KMessageBox.Continue


class LogWidget(KTextBrowser):
    """
    A LogWidget that displays LilyPond output
    """
    def __init__(self, parent=None):
        KTextBrowser.__init__(self, parent, None, True)
        self.setTextFormat(Qt.RichText)
        self.setFont(QFont("Sans", 9))
        QObject.connect(self, SIGNAL("urlClick(const QString&)"), runAction)

    def append(self, text, color=None, bold=False):
        text = keepspaces(text)
        if bold:
            text = "<b>%s</b>" % text
        if color:
            text = "<font color=%s>%s</font>" % (color, text)
        KTextBrowser.append(self, text)

    def msg(self, text, color=None, bold=True):
        self.append(u"* %s" % text, color, bold)

    def ok(self, text, color="darkgreen", bold=True):
        self.msg(text, color, bold)

    def fail(self, text, color="red", bold=True):
        self.msg(text, color, bold)

    def actions(self, actions, color="blue", bold=True):
        if actions:
            self.msg(" - ".join([
                '<a href="%s">%s</a>' % (htmlescapeurl(u), htmlescape(m))
                    for u, m in actions]), color, bold)


def runAction(url):
    """
    Runs an URL with KRun. If url starts with "email=" or "emailpreview=",
    it is converted to a mailto: link with the url attached, and opened in
    the default KDE mailer.
    If url starts with "print=", the file is directly printed with lpr.
    """
    # hack: prevent QTextView recognizing mailto: urls cos it can't handle
    # query string
    url = unicode(url)        # url could be a QString
    m = re.match("([a-z]+)=(.*)", url)
    if not m:
        return krun(url)
    command, url = m.groups()
    if command == 'print':
        path = unicode(KURL(url).path())
        cmd = splitcommandline(config("commands").get("lpr", "lpr"))
        cmd.append(path)
        p = Popen(cmd, stderr=PIPE)
        if p.wait() != 0:
            error(_("Printing failed: %s") % p.stderr.read())
        else:
            info(_("The document has been sent to the printer."))
    elif command in ('email', 'emailpreview'):
        if command == "email" or warncontinue(_(
            "This PDF has been created with point-and-click urls (preview "
            "mode), which increases the file size dramatically. It's better "
            "to email documents without point-and-click urls (publish mode), "
            "because they are much smaller. Continue anyway?")):
            KApplication.kApplication().invokeMailer(
                KURL(u"mailto:?attach=%s" % url), "", True)


class ExecLineEdit(QLineEdit):
    """
    A QLineEdit to enter a filename or path.
    The background changes to red if the entered path is not an
    executable command.
    """
    def __init__(self, *args):
        QLineEdit.__init__(self, *args)
        self.connect(self, SIGNAL("textChanged(const QString&)"),
            self._checkexec)

    def _get(self, filename):
        return str(filename)

    def _checkexec(self, filename):
        if not findexe(self._get(filename)):
            self.setPaletteBackgroundColor(QColor("#FAA"))
        else:
            self.unsetPalette()


class ExecArgsLineEdit(ExecLineEdit):
    """
    An ExecLineEdit that allows arguments in the command string.
    """
    def _get(self, filename):
        return str(filename).split()[0]


class ProcessButton(QPushButton):
    """
    A Pushbutton that starts a process when clicked, and stops it when
    clicked again.
    """

    # these can be shadowed away by instance variables:
    command = "kdialog --sorry 'Not Implemented'"
    pty     = False
    comm    = KProcess.NoCommunication

    def __init__(self, *args):
        QPushButton.__init__(self, *args)
        self.connect(self, SIGNAL("clicked()"), self.clicked)
        self._p = None      # placeholder for KProcess

    def kProcess(self):
        """ Returns the associated KProcess instance or None """
        return self._p

    def onStart(self):
        """
        Implement this to set:
        - the command(line) to execute.
        - which in/out streams to connect
        - other parameters

        This function is called right before start.
        """
        pass

    def started(self):
        """ Called after a successful start """
        pass

    def failed(self):
        """ Called after an unsuccessful start """
        pass

    def stopped(self, proc):
        """ Called on exit. The process can be queried for exit info. """
        pass

    def clicked(self):
        """ called when the button is clicked """
        if self.isRunning():
            self.stop()
        else:
            self.start()

    def isRunning(self):
        return self._p is not None and self._p.isRunning()

    def start(self):
        """
        Starts the process. If successful, show the button pressed.
        """
        # Call this to perform setup right before start
        self.onStart()
        # Now start...
        p = KProcess()
        cmd = self.command
        if isinstance(cmd, basestring):
            cmd = splitcommandline(cmd)
        if self.pty:
            # p.setUsePty does currently not work on Gentoo
            if hasattr(p, "setUsePty"):
                p.setUsePty(KProcess.Stdin, False)
            else:
                # Hack to let a process think it reads from a terminal
                cmd[0:0] = ["python", os.path.join(appdir, "runpty.py")]
        p.setExecutable(cmd[0])
        p.setArguments(cmd[1:])
        # Setup the signals
        if self.comm & KProcess.Stdin:
            self.pending = []
            p.connect(p, SIGNAL("wroteStdin(KProcess*)"), self.wroteStdin)
        if self.comm & KProcess.Stdout:
            p.connect(p, SIGNAL("receivedStdout(KProcess*, char*, int)"),
                self.receivedStdout)
        if self.comm & KProcess.Stderr:
            p.connect(p, SIGNAL("receivedStderr(KProcess*, char*, int)"),
                self.receivedStderr)
        p.connect(p, SIGNAL("processExited(KProcess*)"), self.processExited)
        if p.start(KProcess.NotifyOnExit, self.comm):
            self._p = p
            self.setDown(True)
            self.started()
        else:
            self._p = None
            self.failed()

    def stop(self, signal=15):
        """ Stop the process """
        self._p.kill(signal)

    def processExited(self):
        self.stopped()
        self._p = None
        self.setDown(False)

    def receivedStdout(self, proc, buf, length):
        pass

    def receivedStderr(self, proc, buf, length):
        pass

    def wroteStdin(self):
        """ Called by the KProcess when ready for new stdin data """
        del self.pending[0]
        if self.pending:
            text = self.pending[0]
            self._p.writeStdin(text, len(text))

    def send(self, text):
        """ Send input to the process """
        self.pending.append(text)
        if len(self.pending) == 1:
            text = self.pending[0]
            self._p.writeStdin(text, len(text))


class TapButton(QPushButton):
    """
    A button the user can tap a tempo on.
    """
    def __init__(self, parent, callback):
        QPushButton.__init__(self, _("Tap"), parent)
        self.callback = callback
        self.tapTime = 0.0
        QObject.connect(self, SIGNAL("pressed()"), self.tap)
        QToolTip.add(self, _("Click this button a few times to set the tempo."))

    def tap(self):
        self.tapTime, t = time(), self.tapTime
        bpm = int(60.0 / (self.tapTime - t))
        self.callback(bpm)



# kate: indent-width 4;
