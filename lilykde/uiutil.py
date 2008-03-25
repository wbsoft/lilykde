"""
UI utility functions in two flavors: one for running inside Kate,
the other independent.
"""

from kdecore import KApplication
from kdeui import KMessageBox

try:
    # if this fails, don't define following functions, because
    # they depend on Kate and Pate present:
    import kate

    def _popup(message, timeout=5, **a):
        a.setdefault('parent', kate.mainWidget().topLevelWidget())
        kate.gui.showPassivePopup(message, timeout, **a)

    def error(message, **a):
        _popup(message, icon="error", **a)

    def sorry(message, **a):
        _popup(message, icon="messagebox_warning", **a)

    def info(message, **a):
        _popup(message, icon="messagebox_info", **a)

    def warncontinue(message):
        return KMessageBox.warningContinueCancel(
            kate.mainWidget(), message) == KMessageBox.Continue


except ImportError:

    def error(message, **a):
        KMessageBox.error(KApplication.kApplication().mainWidget(), message)

    def sorry(message, **a):
        KMessageBox.sorry(KApplication.kApplication().mainWidget(), message)

    def info(message, **a):
        KMessageBox.information(
            KApplication.kApplication().mainWidget(), message)

    def warncontinue(message):
        return KMessageBox.warningContinueCancel(
            KApplication.kApplication().mainWidget(), message
            ) == KMessageBox.Continue


#kate: indent-width 4;
