""" Contains small often used utility functions """

from qt import Qt, QApplication, QCursor, QTimer
from kdeui import KMessageBox

import kate
import kate.gui

# No translatable messages in this file!

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
