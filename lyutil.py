""" Contains small often used utility functions """

import kate
import kate.gui
from kdeui import KMessageBox

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
