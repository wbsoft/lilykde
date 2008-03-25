"""
A LogWidget that displays LilyPond output
"""

import re
import shlex
from subprocess import Popen, PIPE

from qt import Qt, QFont, QObject, SIGNAL
from kdecore import KApplication, KURL
from kdeui import KTextBrowser

from lilykde import config
from lilykde.util import keepspaces, htmlescapeurl, htmlescape, krun
from lilykde.uiutil import warncontinue

# translate the messages
from lilykde.i18n import _

class LogWidget(KTextBrowser):
    """
    A LogWidget that displays LilyPond output
    """
    def __init__(self, parent):
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

    def msg(self, text, color=None, bold=False):
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
        cmd = shlex.split(str(config.group("commands").get("lpr", "lpr")))
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

