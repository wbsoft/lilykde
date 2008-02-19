"""
- Determines the LilyPond version
- has a function to insert a \version statement in the current document
"""

import re
from subprocess import Popen, PIPE
from qt import QTimer
import kate

from lilykde_i18n import _


version = None

def timer(msec):
    """ decorator that executes a function after the given time interval
    in milliseconds """
    def action(func):
        QTimer.singleShot(msec, func)
        return func
    return action

@timer(1000)
def init():
    global version
    try:
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", Popen(("lilypond","-v"),
            stdout=PIPE).communicate()[0].splitlines()[0])
    except OSError, e:
        match = None
        from lilykde import error
        error(_("Could not start LilyPond: %s") % e)
    from lymenu import insertVersion as v
    if match:
        version = tuple(int(s or "0") for s in match.groups())
        v.setText(unicode(v.text()) % "%d.%d.%d" % version)
        v.setEnabled(True)
    else:
        v.setText(unicode(v.text()) % _("unknown"))

def insertVersion():
    """ insert LilyPond version in the current document """
    global version
    d = kate.document()
    match, pos, length = d.search("\\version", (0, 0))
    if match:
        from lilykde import sorry
        sorry(_("Your document has already a LilyPond version statement."))
        d.view.cursor.position = pos
    else:
        d.insertLine(0, '\\version "%d.%d.%d"' % version)
        d.view.cursor.position = (0, d.lineLength(0))

def getVersion():
    """ determine the LilyPond version of the current document """
    d = kate.document()
    match = re.search(r'\\version\s*"(\d+)(?:\.(\d+)(?:\.(\d+))?)?"', d.text)
    if match:
        return tuple(int(s or "0") for s in match.groups())
    else:
        return None

def convertLy():
    """ Run convert-ly on the current document """
    from lilykde import sorry, info, error
    global version
    docVersion = getVersion()
    if not docVersion:
        sorry(_("Can't determine the LilyPond version of the current document."
                " Please add a \\version statement with the correct version."))
    elif not version:
        sorry(_("Can't determine the version of LilyPond. "
                "Please check your LilyPond installation."))
    elif docVersion >= version:
        sorry(_("This LilyPond document is already up-to-date."))
    else:
        # Ok, let's run convert-ly.
        # We add the from-version. Only in that case convert-ly wants to
        # read from stdin.
        try:
            out, err = Popen(("convert-ly", "-f", "%d.%d.%d" % docVersion, "-"),
                            stdin=PIPE, stdout=PIPE, stderr=PIPE
                            ).communicate(kate.document().text.encode('utf8'))
            if out:
                kate.document().text = u"%s\n\n%%{\n%s\n%%}\n" % (
                out.decode('utf8'), err.decode('utf8'))
                info(_(
                 "The document has been processed with convert-ly. You'll find "
                 "the messages of convert-ly in a comment block at the end. "
                 "You still may have to edit some parts manually."), timeout=10)
            else:
                msg = err.decode('utf8').replace('\n', '<br>')
                info(_(
                 "The document has been processed with convert-ly, but "
                 "remained unchanged. This is the message given by "
                 "convert-ly: %s") % "<br><br>%s" % msg, timeout=10)
        except OSError, e:
            error(_("Could not start convert-ly: %s") % e)
