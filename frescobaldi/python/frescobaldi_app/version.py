# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

""" Functions to run convert-ly and insert the LilyPond version """

from subprocess import Popen, PIPE
import ly.tokenize, ly.version

from PyKDE4.kdecore import i18n, KGlobal
from PyKDE4.kdeui import KMessageBox
from PyKDE4.ktexteditor import KTextEditor

def defaultVersion():
    """
    Returns the LilyPond version according to the user's preference:
    the version of the currently installed LilyPond, the version of the last
    rule in convert-ly, or a custom version.
    """
    lilypond = ly.version.LilyPondInstance(command("lilypond"))
    
    prefs = config("preferences")
    pver = prefs.readEntry("default version", "lilypond")
    
    version = ''
    if pver == "custom":
        version = ly.version.Version.fromString(prefs.readEntry("custom version", ""))
    elif pver == "convert-ly":
        version = lilypond.lastConvertLyRuleVersion()
    return version or lilypond.version()

def insertVersion(mainwin):
    """
    Insert the current LilyPond version into the current document
    if it does not already have a version command.
    """
    doc = mainwin.currentDocument()
    for token in ly.tokenize.LineColumnTokenizer().tokens(doc.text()):
        if token == "\\version":
            doc.view.setCursorPosition(KTextEditor.Cursor(token.line, token.column))
            KMessageBox.sorry(mainwin,
                i18n("Your document has already a LilyPond version statement."),
                i18n("Version already set"))
            return
    else:
        version = defaultVersion()
        if version:
            doc.doc.insertLine(0, '\\version "{0}"'.format(version))
        else:
            KMessageBox.sorry(mainwin,
                i18n("Can't determine the version of LilyPond. "
                     "Please check your LilyPond installation."))

def convertLy(mainwin):
    """
    Run the current document through convert-ly.
    """
    doc = mainwin.currentDocument()
    text = doc.text()
    docVersion = ly.version.getVersion(text)
    lilyVersion = ly.version.LilyPondInstance(command("lilypond")).version()
    
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
        try:
            out, err = Popen(
                (command("convert-ly"), "-f", str(docVersion), "-"),
                stdin=PIPE, stdout=PIPE, stderr=PIPE
                ).communicate(text.encode('utf8'))
            if out:
                doc.setText(u"{0}\n\n%{{\n{1}\n%}}\n".format(out.decode('utf8'), err.decode('utf8')))
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
        except OSError as e:
            msg = unicode(e)
            KMessageBox.error(mainwin, i18n("Could not start convert-ly: %1", msg))

    
def config(group):
    return KGlobal.config().group(group)

def command(cmd):
    return config("commands").readEntry(cmd, cmd)
