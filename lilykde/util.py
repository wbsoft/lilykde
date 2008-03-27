""" Contains small often used utility functions """

import re

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

def onSignal(sender, signal, saveObj=None):
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
