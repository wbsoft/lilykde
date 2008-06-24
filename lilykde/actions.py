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
All code related to actions (the blue clickable links in the log widget)
is collected here.
"""

import re
from subprocess import Popen, PIPE

from kdecore import KApplication, KURL

from lilykde import config
from lilykde.widgets import error, info
from lilykde.util import krun, splitcommandline

# Translate the messages
from lilykde.i18n import _

actions = (
    ('open_folder', 1,
        _("Open folder"),
        _("Open the folder containing the LilyPond and PDF documents.")),
    ('open_pdf', 1,
        _("Open PDF"),
        _("Open the generated PDF file with the default PDF viewer.")),
    ('print_pdf', 1,
        _("Print"),
        _("Print the PDF using the print command set in the Commands "
            "settings page.")),
    ('email_pdf', 1,
        _("Email PDF"),
        _("Attach the PDF to an email message.")),
    ('play_midi', 1,
        _("Play MIDI"),
        _("Play the generated MIDI files using the default MIDI player "
            "(Timidity++ is recommended).")),
    ('embed_source', 0,
        _("Embed source"),
        _("Embed the LilyPond source files in the published PDF "
            "(using pdftk).")),
)

def actionsConfig():
    """
    Returns a dictionary with action names mapping to a value 0 or 1,
    (whether they are enabled by the user or by default).
    """
    conf = config("actions")
    return dict((name, int(conf[name] or default))
        for name, default, title, tooltip in actions)

def runAction(url):
    """
    Runs an URL with KRun. If url starts with "email=" or "emailpreview=",
    it is converted to a mailto: link with the url attached, and opened in
    the default KDE mailer.
    If url starts with "print=", the file is directly printed with lpr.
    If url starts with "embed=", a subroutine in pdftk is called to embed
    LilyPond documents in the output PDF.
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
    elif command == 'embed':
        ly = unicode(KURL(url).path())
        from lilykde import pdftk
        pdftk.attach_files(ly)

def listActions(lyfile, preview):
    """
    returns a actions list that LogWidget (see widgets.py) can display,
    based on the given LyFile object (see runlily.py) and the preview
    mode (True or False).
    """
    act = actionsConfig()
    actions = []
    if act["open_folder"]:
        actions.append(("file://%s" % lyfile.directory, _("Open folder")))
    if lyfile.hasUpdatedPDF():
        if act["open_pdf"]:
            actions.append(("file://%s" % lyfile.pdf, _("Open PDF")))
        if act["print_pdf"]:
            actions.append(("print=file://%s" % lyfile.pdf, _("Print")))
        if act["email_pdf"]:
            # hack: prevent QTextView from recognizing mailto urls, as
            # it then uses the mailClick signal, which does not give us
            # the query string. Later on, we prepend the "mailto:?" :)
            if preview:
                actions.append(("emailpreview=file://%s" % lyfile.pdf,
                    _("Email PDF (preview)")))
            else:
                actions.append(("email=file://%s" % lyfile.pdf,
                    _("Email PDF")))
        # should we embed the LilyPond source files in the PDF?
        from lilykde import pdftk
        if act["embed_source"] and pdftk.installed() and (preview or
                config("preferences")['embed source files'] != '1'):
            actions.append(("embed=file://%s" % lyfile.path, _("Embed source")))
    midis = lyfile.getUpdated(".midi")
    if act["play_midi"] and midis:
        actions.append(("file://%s" % midis[0], _("Play MIDI")))
        actions.extend([("file://%s" % m, str(n+1))
            for n, m in enumerate(midis[1:])])
    return actions


#kate: indent-width 4;
