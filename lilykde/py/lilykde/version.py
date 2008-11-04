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
- Determines the LilyPond version
- has a function to insert a \version statement in the current document
"""

import re
from subprocess import Popen, PIPE

# Some utils, popups
from lilykde.util import timer
from lilykde.widgets import info, sorry, error

# config and editor backend
from lilykde import config, editor

# Translate the messages
from lilykde.i18n import _


version = None

@timer(1000)
def init():
    global version
    lilypond = config("commands").get("lilypond", "lilypond")
    try:
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", Popen((lilypond, "-v"),
            stdout=PIPE).communicate()[0].splitlines()[0])
    except OSError, e:
        match = None
        error(_("Could not start LilyPond: %s") % e)
    from lilykde.menu import menu
    v = menu.child("insertVersion")
    if match:
        version = tuple(int(s or "0") for s in match.groups())
        v.setText(unicode(v.text()) % "%d.%d.%d" % version)
        v.setEnabled(True)
    else:
        v.setText(unicode(v.text()) % _("unknown"))

def insertVersion():
    """ insert LilyPond version in the current document """
    global version
    match, pos, length = editor.search("\\version", (0, 0))
    if match:
        sorry(_("Your document has already a LilyPond version statement."))
        editor.setPos(pos)
    else:
        versionLine = '\\version "%d.%d.%d"' % version
        editor.insertLine(0, versionLine)
        editor.setPos(0, len(versionLine))

def getVersion():
    """ determine the LilyPond version of the current document """
    match = re.search(r'\\version\s*"(\d+)(?:\.(\d+)(?:\.(\d+))?)?',
        editor.text())
    if match:
        return tuple(int(s or "0") for s in match.groups())
    else:
        return None

def convertLy():
    """ Run convert-ly on the current document """
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
        convert_ly = config("commands").get("convert-ly", "convert-ly")
        try:
            out, err = Popen((convert_ly, "-f", "%d.%d.%d" % docVersion, "-"),
                            stdin=PIPE, stdout=PIPE, stderr=PIPE
                            ).communicate(editor.text().encode('utf8'))
            if out:
                editor.setText(u"%s\n\n%%{\n%s\n%%}\n" %
                    (out.decode('utf8'), err.decode('utf8')))
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


# kate: indent-width 4;
