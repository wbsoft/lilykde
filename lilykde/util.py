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

""" Contains small often used utility functions """

import os, re

from qt import SIGNAL, Qt, QApplication, QCursor, QObject, QTimer, QStringList
from kdecore import KConfig, KConfigGroup, KProcess, KURL
from kio import KRun

# Translate the messages
from lilykde.i18n import _


def busy(b=True, cursor=None):
    """
    if True, set a busy mouse cursor for the whole app, otherwise unset.
    """
    if b:
        if cursor is None:
            cursor = QCursor(Qt.BusyCursor)
        QApplication.setOverrideCursor(cursor)
    else:
        QApplication.restoreOverrideCursor()

# Small html functions
def encodeurl(s):
    """Encode an URL, but leave html entities alone."""
    for a, b in (
        ('%', '%25'),
        (' ', "%20"),
        ('~', "%7E"),
        ): s = s.replace(a,b)
    return s

_hextochr = dict(('%02x' % i, chr(i)) for i in range(256))
_hextochr.update(('%02X' % i, chr(i)) for i in range(256))

def decodeurl(s):
    """Decode an URL, based on Python urllib.unquote"""
    res = s.split('%')
    for i in xrange(1, len(res)):
        item = res[i]
        try:
            res[i] = _hextochr[item[:2]] + item[2:]
        except KeyError:
            res[i] = '%' + item
        except UnicodeDecodeError:
            res[i] = unichr(int(item[:2], 16)) + item[2:]
    return "".join(res)

def htmlescape(s):
    """Escape strings for use in HTML text and attributes."""
    for a, b in (
        ("&", "&amp;"),
        (">", "&gt;"),
        ("<", "&lt;"),
        ("'", "&apos;"),
        ('"', "&quot;"),
        ): s = s.replace(a,b)
    return s

def htmlescapeurl(s):
    """Escape strings for use as URL in HTML href attributes etc."""
    return htmlescape(encodeurl(s))

def keepspaces(s):
    """
    Changes "  " into "&nbsp; ".
    Hack needed because otherwise the spaces disappear in the LogWindow.
    """
    s = s.replace("  ","&nbsp; ")
    s = s.replace("  ","&nbsp; ")
    return re.sub("^ ", "&nbsp;", s)

def py2qstringlist(l):
    """
    convert a list of strings to a QStringList
    """
    r = QStringList()
    for i in l:
        r.append(i)
    return r

def qstringlist2py(ql):
    """
    convert a QStringList to a python list of unicode strings
    """
    return map(unicode, ql)

def bound(x, minValue, maxValue):
    """ Clips x according to the boundaries minValue and maxValue """
    return max(minValue, min(maxValue, x))

def rdict(d):
    """ reverse a dict """
    return dict((v,k) for k,v in d.iteritems())

# Thanks: http://billmill.org/python_roman.html
_roman_numerals = (("M", 1000), ("CM", 900), ("D", 500), ("CD", 400),
("C", 100),("XC", 90),("L", 50),("XL", 40), ("X", 10), ("IX", 9), ("V", 5),
("IV", 4), ("I", 1))

def romanize(n):
    roman = []
    for ltr, num in _roman_numerals:
        k, n = divmod(n, num)
        roman.append(ltr * k)
    return "".join(roman)

def splitcommandline(s):
    """ Splits a commandline like the shell, keeping quoted parts together """
    return _splitcommandline_re.sub(_splitcommandline, s.strip()).split('\0')

_splitcommandline_re = re.compile(
    r'(")((\\.|[^"])*)"'    # double quoted string
    r"|(')([^']*)'"         # single quoted string
    r"|\s+")                # space

def _splitcommandline(m):
    if m.group(1):
        return re.sub(r"\\(.)", r"\1", m.group(2))
    elif m.group(4):
        return m.group(5)
    else:
        return '\0'

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

# Some decorators
def timer(msec):
    """
    A decorator that executes a function after the given time interval
    in milliseconds
    """
    def action(func):
        QTimer.singleShot(msec, func)
        return func
    return action

def onSignal(sender, signal):
    """
    A decorator that connects its function to a Qt signal.
    """
    def sig(func):
        QObject.connect(sender, SIGNAL(signal), func)
        return func
    return sig

# Some helper or wrapper classes
class _kconfigbase(object):
    """
    A wrapper around KConfigBase-like objects, to access them like a dictionary.
    """
    def get(self, key, default=''):
        return unicode(self.kc.readEntry(key)) or default

    def __getitem__(self, key):
        return unicode(self.kc.readEntry(key))

    def __setitem__(self, key, value):
        self.kc.writeEntry(key, value)

    def __contains__(self, key):
        return self.kc.hasKey(key)

    def sync(self):
        self.kc.sync()


class kconfig(_kconfigbase):
    """
    A wrapped KConfig object, that can be accessed like a dictionary
    """
    def __init__(self, *args):
        self.kc = KConfig(*args)

    def setGroup(self, groupname):
        self.kc.setGroup(groupname)

    def group(self, groupname):
        """ return an object for this group """
        return kconfiggroup(self, groupname)


class kconfiggroup(_kconfigbase):
    """
    A wrapped KConfigGroup object, that can be accessed like a dictionary
    """
    def __init__(self, master, groupname):
        self.kc = _WrappedKConfigGroup(master.kc, groupname)
        # keep a pointer to master, because Kate crashes if it goes out of scope
        self.master = master


class _WrappedKConfigGroup(KConfigGroup):
    """
    Somehow PyKDE won't let me instantiate KConfigGroup objects directly,
    saying that KConfigGroup represents a c++ abstract class.
    """
    pass


class kprocess(KProcess):
    """
    A wrapper around KProcess that keeps a pointer to itself until
    a processExited() signal has been received
    """
    __savedInstances = []

    def __init__(self):
        KProcess.__init__(self)
        QObject.connect(self,
            SIGNAL("processExited(KProcess*)"), self._slotExit)

    def start(self, runmode=KProcess.NotifyOnExit, comm=KProcess.AllOutput):
        res = KProcess.start(self, runmode, comm)
        if res:
            kprocess.__savedInstances.append(self)
            busy()
        return res

    def _slotExit(self, p):
        busy(False)
        self.wait()
        self._finish()
        kprocess.__savedInstances.remove(self)

    def _finish(self):
        pass

    @staticmethod
    def instances():
        return kprocess.__savedInstances


class krun(KRun):
    """
    A wrapper around KRun that keeps a pointer to itself until
    a finished() signal has been received
    """
    __savedInstances = []

    def __init__(self, url):
        KRun.__init__(self, KURL(url))
        self.setAutoDelete(False)
        krun.__savedInstances.append(self)
        QObject.connect(self, SIGNAL("finished()"), self._slotExit)

    def _slotExit(self):
        krun.__savedInstances.remove(self)


#kate: indent-width 4;
