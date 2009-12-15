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

"""
LilyPond version information
"""

import os, re
from subprocess import Popen, PIPE, STDOUT


class LilyPondVersion(object):
    def __init__(self, command = 'lilypond'):
        self.versionTuple = ()
        self.versionString = ""
        try:
            output = Popen((command, '-v'), stdout=PIPE, stderr=STDOUT).communicate()[0].splitlines()[0]
            match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", output)
            if match:
                self.versionTuple = tuple(int(s or "0") for s in match.groups())
                self.versionString = "{0}.{1}.{2}".format(*self.versionTuple)
        except OSError:
            pass


class ConvertLyLastRuleVersion(object):
    def __init__(self, command = 'convert-ly'):
        self.versionTuple = ()
        self.versionString = ""
        try:
            output = Popen((command, '--show-rules'), stdout=PIPE).communicate()[0]
            for line in reversed(output.splitlines()):
                match = re.match(r"((\d+)\.(\d+)\.(\d+)):", line)
                if match:
                    self.versionString = match.group(1)
                    self.versionTuple = tuple(int(s) for s in match.group(2, 3, 4))
                    return
        except OSError:
            pass


def datadir(command = 'lilypond'):
    """ Returns the data directory of the given lilypond binary """
    
    # First ask LilyPond itself.
    try:
        datadir = Popen((command, '-e',
            "(display (ly:get-option 'datadir)) (newline) (exit)"),
            stdout=PIPE).communicate()[0].strip()
        if os.path.isabs(datadir) and os.path.isdir(datadir):
            return datadir
    except OSError:
        pass
    # Then find out by manipulating path.
    if not os.path.isabs(command):
        command = findexe(command)
        if not command:
            return False
    # LilyPond is found. Go up to prefix and then into share/lilypond        
    prefix = os.path.dirname(os.path.dirname(command))
    dirs = ['current']
    version = LilyPondVersion(command).versionString
    if version:
        dirs.append(version)
    for suffix in dirs:
        datadir = os.path.join(prefix, 'share', 'lilypond', suffix)
        if os.path.isdir(datadir):
            return datadir
    return False
    

def getVersion(text):
    """
    Determine the version of a LilyPond document.
    Always returns a three-tuple, truncating or padding with zero's
    """
    match = re.search(r'\\version\s*".*?"', text)
    if match:
        return tuple((map(int, re.findall('\\d+', match.group())) + [0, 0, 0])[:3])



# Utility functions.....
def isexe(path):
    """
    Return path if it is an executable file, otherwise False
    """
    return os.access(path, os.X_OK) and path


def findexe(filename):
    """
    Look up a filename in the system PATH, and return the full
    path if it can be found. If the path is absolute, return it
    unless it is not an executable file.
    """
    if os.path.isabs(os.path.expanduser(filename)):
        return isexe(os.path.expanduser(filename))
    for p in os.environ.get("PATH", os.defpath).split(os.pathsep):
        if isexe(os.path.join(p, filename)):
            return os.path.join(p, filename)
    return False
