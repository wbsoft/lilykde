""" A Log Window.
On first import a tool view is created.
"""

import re

import kate
import kate.gui

from qt import SIGNAL, QFont, Qt, QWidget
from kdecore import KApplication, KURL
from kdeui import KTextBrowser
from kio import KRun

from lyutil import *

# translate the messages
from lilykde_i18n import _

tool = kate.gui.Tool(_("LilyPond Log"), "log", kate.gui.Tool.bottom)
log = KTextBrowser(tool.widget, None, True)
log.setTextFormat(Qt.RichText)
log.setFont(QFont("Sans", 9))
log.setFocusPolicy(QWidget.NoFocus)
log.show()
tool.show()

# make these easily available
show = tool.show
hide = tool.hide
clear = log.clear

def append(text, color=None, bold=False):
    text = keepspaces(text)
    if bold:
        text = "<b>%s</b>" % text
    if color:
        text = "<font color=%s>%s</font>" % (color, text)
    log.append(text)

def msg(text, color=None, bold=False):
    append(u"*** %s" % text, color, bold)

def ok(text, color="darkgreen", bold=True):
    msg(text, color, bold)

def fail(text, color="red", bold=True):
    msg(text, color, bold)

def actions(actions, color="blue", bold=True):
    if actions:
        msg(" - ".join(['<a href="%s">%s</a>' % (htmlescapeurl(u), htmlescape(m))
            for u, m in actions]), color, bold)

@onSignal(log, "urlClick(const QString&)")
def _runURL(url):
    """
    Runs an URL with KRun. If url starts with "email=" or "emailpreview=",
    it is converted to a mailto: link with the url attached, and opened in
    the default KDE mailer.
    """
    # hack: prevent QTextView recognizing mailto: urls cos it can't handle
    # query string
    url = unicode(url)        # url could be a QString
    m = re.match("([a-z]+)=(.*)", url)
    if not m:
        return OpenURL(url)
    command, url = m.groups()
    if command in ('email', 'emailpreview'):
        if command == "email" or warncontinue(_(
            "This PDF has been created with point-and-click urls (preview "
            "mode), which increases the file size dramatically. It's better "
            "to email documents without point-and-click urls (publish mode), "
            "because they are much smaller. Continue anyway?")):
            KApplication.kApplication().invokeMailer(
                KURL(u"mailto:?attach=%s" % url), "", True)


class OpenURL(object):
    """
    Runs an URL with KRun, but keeps a pointer so the instance will not go
    out of scope, causing the process to terminate.
    """
    def __init__(self, url):
        self.p = KRun(KURL(url))
        self.p.setAutoDelete(False)
        # save our instance in this inner function
        @onSignal(self.p, "finished()")
        def finish():
            # delete p, so the signal is also disconnected and we get garbage
            # collected.
            del self.p

# kate: indent-width 4
