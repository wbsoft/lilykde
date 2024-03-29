# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
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

from __future__ import unicode_literals

"""
Functions that can be run if the user updates Frescobaldi
to a newer version.
"""

import os, re, sys

from PyKDE4.kdecore import KConfig, KGlobal, KStandardDirs

def install(app, oldVersion):
    """
    Run when the version in the root config group is different from the
    running Frescobaldi version.
    """
    version = tuple(map(int, re.findall(r'\d+', oldVersion)))
    
    if not version:
        installKateModeRC()
    
    if version < (1, 1, 0):
        newLilyPondConfig()
    
    if version < (1, 1, 2):
        saveOnRunWarning()
    
    # ... other stuff can be added here ...
    


def installKateModeRC():
    """ Preset a few variables in the LilyPond Kate mode """
    katemoderc = KConfig("katemoderc", KConfig.NoGlobals)
    rc = katemoderc.group("LilyPond")
    rc.writeEntry("Variables", "kate: "
        "indent-mode lilypond; "
        )
    rc.sync()

def installOkularPartRC():
    """ Set our custom editor command in okularpartrc """
    # determine the command needed to run us
    command = sys.argv[0]
    if os.path.sep in command: # does the command contain a directory separator?
        if not os.path.isabs(command):
            command = os.path.abspath(command)
        if command == KStandardDirs.findExe("frescobaldi"):
            command = "frescobaldi"
    command += " --smart --line %l --column %c"
    okularpartrc = KConfig("okularpartrc", KConfig.NoGlobals)
    group = okularpartrc.group("General")
    group.writeEntry("ExternalEditor", "Custom")
    group.writeEntry("ExternalEditorCommand", command)
    if not group.readEntry("WatchFile", True):
        group.writeEntry("WatchFile", True)
    group.sync()
    
def newLilyPondConfig():
    """ Take old lilypond path preference over to new multi-version config (1.1.0) """
    c = KGlobal.config()
    group = c.group("lilypond")
    if not group.hasKey("default"):
        cmds = c.group("commands")
        lily = cmds.readEntry("lilypond", "lilypond")
        conv = cmds.readEntry("convert-ly", "convert-ly")
        if (os.path.isabs(lily) and os.path.isabs(conv)
            and os.path.dirname(lily) == os.path.dirname(conv)):
            conv = os.path.basename(conv)
        group.writeEntry("default", lily)
        group.writeEntry("paths", [lily])
        group = group.group(lily)
        group.writeEntry("convert-ly", conv)
        c.sync()
    
def saveOnRunWarning():
    """ Copy old setting to the new save on run notification setting (1.1.2)"""
    c = KGlobal.config()
    group = c.group("preferences")
    if group.readEntry("save on run", False):
        group = c.group("Notification Messages")
        group.writeEntry("save_on_run", False)
        c.sync()

