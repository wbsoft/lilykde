# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
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

""" Functions to run convert-ly and insert the LilyPond version """

from subprocess import Popen, PIPE
import ly.version

from PyKDE4.kdecore import i18n, KGlobal
from PyKDE4.kdeui import KMessageBox
from PyKDE4.ktexteditor import KTextEditor

def insertVersion(mainwin):
    """
    Insert the current LilyPond version into the current document
    if it does not already have a version command.
    """
    doc = mainwin.view().document()
    search = doc.searchInterface()
    res = search.searchText(doc.documentRange(), '\\version')
    if res[0].isValid():
        mainwin.view().setCursorPosition(res[0].start())
        KMessageBox.sorry(mainwin,
            i18n("Your document has already a LilyPond version statement."),
            i18n("Version already set"))
    else:
        version = ly.version.LilyPondVersion().versionString
        if version:
            mainwin.view().document().insertLine(0, '\\version "%s"' % version)
        else:
            KMessageBox.sorry(mainwin,
                i18n("Can't determine the version of LilyPond. "
                     "Please check your LilyPond installation."))


def convertLy(mainwin):
    """
    Run the current document through convert-ly.
    """
    doc = mainwin.view().document()
    text = unicode(doc.text())
    docVersion = ly.version.getVersion(text) #or ly.guess.version(text)
    lilyVersion = ly.version.LilyPondVersion().versionTuple
    
    if not docVersion:
        KMessageBox.sorry(mainwin, i18n(
            "Can't determine the LilyPond version of the current document."
            " Please add a \\version statement with the correct version."))
    elif not lilyVersion:
        KMessageBox.sorry(mainwin, i18n(
            "Can't determine the version of LilyPond. "
            "Please check your LilyPond installation."))
    elif docVersion >= lilyVersion:
        KMessageBox.information(mainwin, i18n(
            "This LilyPond document is already up-to-date."))
    else:
        # Ok, let's run convert-ly.
        # We add the from-version. Only in that case convert-ly wants to
        # read from stdin.
        convert_ly = unicode(config("commands").readEntry("convert-ly", "convert-ly"))
        try:
            out, err = Popen((convert_ly, "-f", "%d.%d.%d" % docVersion, "-"),
                            stdin=PIPE, stdout=PIPE, stderr=PIPE
                            ).communicate(text.encode('utf8'))
            if out:
                doc.setText(u"%s\n\n%%{\n%s\n%%}\n" %
                    (out.decode('utf8'), err.decode('utf8')))
                KMessageBox.information(mainwin, i18n(
                 "The document has been processed with convert-ly. You'll find "
                 "the messages of convert-ly in a comment block at the end. "
                 "You still may have to edit some parts manually."))
            else:
                msg = "<br><br>" + err.decode('utf8').replace('\n', '<br>')
                KMessageBox.information(mainwin, i18n(
                 "The document has been processed with convert-ly, but "
                 "remained unchanged. This is the message given by "
                 "convert-ly: %1", msg))
        except OSError, e:
            msg = unicode(e)
            KMessageBox.error(mainwin, i18n("Could not start convert-ly: %1", msg))

    
def config(group="rumor"):
    return KGlobal.config().group(group)
