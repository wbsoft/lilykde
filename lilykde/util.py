""" Contains small often used utility functions """

import re

from qt import SIGNAL, Qt, QApplication, QCursor, QTimer, QStringList
from kdecore import KConfig, KConfigGroup
from kdeui import KMessageBox

import kate
import kate.gui

from lilykde.i18n import _

def popup(message, timeout=5, **a):
    a.setdefault('parent', kate.mainWidget().topLevelWidget())
    kate.gui.showPassivePopup(message, timeout, **a)

def error(message, **a):
    popup(message, icon="error", **a)

def sorry(message, **a):
    popup(message, icon="messagebox_warning", **a)

def info(message, **a):
    popup(message, icon="messagebox_info", **a)

def warncontinue(message):
    return KMessageBox.warningContinueCancel(kate.mainWidget(),message) == \
        KMessageBox.Continue

def timer(msec):
    """ decorator that executes a function after the given time interval
    in milliseconds """
    def action(func):
        QTimer.singleShot(msec, func)
        return func
    return action

def busy(b=True, cursor=QCursor(Qt.BusyCursor)):
    """ if True, set a busy mouse cursor for the whole app, otherwise unset. """
    if b:
        QApplication.setOverrideCursor(cursor)
    else:
        QApplication.restoreOverrideCursor()

# storage too keep pointers to KRun or KProcess objects to prevent them from
# going out of scope
_savedObjects = []

def onSignal(sender, signal, saveObj=None):
    """ a decorator that connects a function to a Qt signal """
    if saveObj is None:
        def sig(func):
            sender.connect(sender, SIGNAL(signal), func)
        return sig
    else:
        _savedObjects.append(saveObj)
        def sig(func):
            def cleanup(*args):
                # don't call func with arguments it doesn't want
                func(*args[0:func.func_code.co_argcount])
                _savedObjects.remove(saveObj)
            sender.connect(sender, SIGNAL(signal), cleanup)
        return sig

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

def runOnSelection(func):
    """
    Decorator that makes a function run on the selection,
    and replaces the selection with its output if not None
    """
    def selFunc():
        sel = kate.view().selection
        if not sel.exists:
            sorry(_("Please select some text first."))
            return
        d, v, text = kate.document(), kate.view(), sel.text
        text = func(text)
        if text is not None:
            d.editingSequence.begin()
            sel.removeSelectedText()
            v.insertText(text)
            d.editingSequence.end()
    return selFunc


class _kconfigbase(object):
    """
    A wrapper around KConfigBase-like objects, to access them like a dictionary.
    """
    def get(self, key, default=''):
        return unicode(self.kc.readEntry(key, default))

    def __getitem__(self, key):
        return unicode(self.kc.readEntry(key))

    def __setitem__(self, key, value):
        self.kc.writeEntry(key, value)

    def __contains__(self, key):
        return self.kc.hasKey(key)


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


#kate: indent-width 4;