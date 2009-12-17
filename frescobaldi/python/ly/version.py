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
from functools import wraps
from subprocess import Popen, PIPE, STDOUT

import ly.rx

# global cache of LilyPond instances (prevents loading each time again)
_cache = {}


def LilyPondInstance(command='lilypond', cache=True):
    """
    Returns a LilyPondInstance() for the given lilypond command.
    By default caches the instances for quick return next time.
    """
    if not (cache and command in _cache):
        _cache[command] = _LilyPondInstance(command)
    return _cache[command]


def getVersion(text):
    """
    Determine the version of a LilyPond document.
    Returns a Version instance or None.
    """
    text = ly.rx.all_comments.sub('', text)
    match = re.search(r'\\version\s*"(.*?)"', text)
    if match:
        return Version.fromString(match.group(1))


# Utility functions.....
def cacheresult(func):
    """
    Use as a decorator for methods with no arguments.
    The method is called the first time. For subsequent calls, the cached result
    is returned.
    """
    cache = {}
    @wraps(func)
    def deco(self):
        if self not in cache:
            cache[self] = func(self)
        return cache[self]
    return deco


class Version(tuple):
    """
    Contains a version as a two- or three-tuple (major, minor [, patchlevel]).
    
    Can format itself as "major.minor" or "major.minor.patch"
    Additionally, three attributes are defined:
    - major     : contains the major version number as an int
    - minor     : contains the minor version number as an int
    - patch     : contains the patch level as an int or None
    """
    def __new__(cls, major, minor, patch=None):
        if patch is None:
            obj = tuple.__new__(cls, (major, minor))
        else:
            obj = tuple.__new__(cls, (major, minor, patch))
        obj.major = major
        obj.minor = minor
        obj.patch = patch
        return obj
        
    def __format__(self, formatString):
        return str(self)
        
    def __str__(self):
        return ".".join(map(str, self))

    @classmethod
    def fromString(cls, text):
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
        if match:
            return cls(*map(lambda g: int(g) if g else None, match.groups()))

            
class _LilyPondInstance(object):
    """
    Contains information about a LilyPond instance, referred to by a command
    string defaulting to 'lilypond'.
    """
    
    # name of the convert-ly command
    convert_ly_name = 'convert-ly'
    
    def __init__(self, command='lilypond'):
        self._command = command
    
    @cacheresult
    def command(self):
        """
        Returns the command with full path prepended.
        """
        cmd = self._command
        if os.path.isabs(cmd):
            return cmd
        elif os.path.isabs(os.path.expanduser(cmd)):
            return os.path.expanduser(cmd)
        elif os.sep in cmd and os.access(cmd, os.X_OK):
            return os.path.abspath(cmd)
        else:
            for p in os.environ.get("PATH", os.defpath).split(os.pathsep):
                if os.access(os.path.join(p, cmd), os.X_OK):
                    return os.path.join(p, cmd)
    
    @cacheresult
    def convert_ly(self):
        """
        Returns the full path of the convert-ly command that is in the
        same directory as the corresponding lilypond command.
        """
        cmd = self.command()
        if cmd:
            return os.path.join(os.path.dirname(cmd), self.convert_ly_name)
            
    @cacheresult
    def prefix(self):
        """
        Returns the prefix of a command. E.g. if command is "lilypond"
        and resolves to "/usr/bin/lilypond", this method returns "/usr".
        """
        cmd = self.command()
        if cmd:
            return os.path.dirname(os.path.dirname(cmd))
        
    @cacheresult
    def version(self):
        """
        Returns the version returned by command -v as an instance of Version.
        """
        try:
            output = Popen((self._command, '-v'), stdout=PIPE, stderr=STDOUT).communicate()[0]
            return Version.fromString(output)
        except OSError:
            pass

    @cacheresult
    def datadir(self):
        """
        Returns the datadir of this LilyPond instance. Most times something
        like "/usr/share/lilypond/2.13.3/"
        """
        # First ask LilyPond itself.
        try:
            d = Popen((self._command, '-e',
                "(display (ly:get-option 'datadir)) (newline) (exit)"),
                stdout=PIPE).communicate()[0].strip()
            if os.path.isabs(d) and os.path.isdir(d):
                return d
        except OSError:
            pass
        # Then find out via the prefix.
        version, prefix = self.version(), self.prefix()
        if prefix:
            dirs = ['current']
            if version:
                dirs.append(str(version))
            for suffix in dirs:
                d = os.path.join(prefix, 'share', 'lilypond', suffix)
                if os.path.isdir(d):
                    return d

    @cacheresult
    def lastConvertLyRuleVersion(self):
        """
        Returns the version of the last convert-ly rule of this lilypond
        instance.
        """
        try:
            output = Popen((self.convert_ly(), '--show-rules'), stdout=PIPE).communicate()[0]
            for line in reversed(output.splitlines()):
                match = re.match(r"(\d+)\.(\d+)\.(\d+):", line)
                if match:
                    return Version(*map(int, match.groups()))
        except OSError:
            pass
        


