"""
- Determines the LilyPond version
- has a function to insert a \version statement in the current document
"""

from lilykde_i18n import _


version = None

def timer(msec):
    """ decorator that executes a function after the given time interval
    in milliseconds """
    def action(func):
        from qt import QTimer
        QTimer.singleShot(msec, func)
        return func
    return action

@timer(1000)
def init():
    import re
    from subprocess import Popen, PIPE
    try:
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", Popen(("lilypond","-v"),
            stdout=PIPE).communicate()[0].splitlines()[0])
    except OSError, e:
        match = None
        from lilykde import error
        error(_("Could not start LilyPond: %s") % e)
    from lymenu import insertVersion as v
    global version
    if match:
        version = tuple(int(s or "0") for s in match.groups())
        v.setText(unicode(v.text()) % "%d.%d.%d" % version)
        v.setEnabled(True)
    else:
        v.setText(unicode(v.text()) % _("unknown"))

def insertVersion():
    """ insert LilyPond version in the current document """
    import kate
    global version
    d = kate.document()
    match, pos, length = d.search("\\version", (0, 0))
    if match:
        from lilykde import sorry
        sorry(_("Your document has already a LilyPond version statement."))
        d.view.cursor.position = pos
    else:
        d.insertLine(0, '\\version "%s"' % version)
        d.view.cursor.position = (0, d.lineLength(0))
