"""
Widgets used in LilyKDE
"""

import re, shlex
from subprocess import Popen, PIPE

from qt import *
from kdecore import KApplication, KURL
from kdeui import KMessageBox, KTextBrowser

from lilykde import config
from lilykde.util import findexe, keepspaces, htmlescapeurl, htmlescape, krun

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
        cmd = shlex.split(str(config("commands").get("lpr", "lpr")))
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


# kate: indent-width 4;
