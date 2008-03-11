"""
This is the LilyPond Kate main menu.

You can disable actions by calling lymenu.action.setEnabled(false), e.g.
lymenu.preview.setEnabled(False)

You can call actions by calling e.g. lymenu.publish.activate()
"""
import sys
import kate

# translate the messages
from lilykde.i18n import _

# setup LilyPond menu. Somehow it seems not to be possible to use pate's
# standard decorators on an own toplevel menu.
# The menu is not yet created, etc. Just setup our own.
from kdecore import KShortcut
from kdeui import KAction, KActionMenu, KActionSeparator

class Menu(KActionMenu):
    def add(self, text, key="", icon=""):
        """ Returns a function that when called returns a KAction. """
        def action(func):
            a = KAction(text, icon, KShortcut(key), func, self, "")
            self.insert(a)
            return a
        return action

menu = Menu(_("LilyPond"))

@menu.add(_("Run LilyPond (preview)"), "Ctrl+Shift+M", "ly")
def preview():
    from lilykde.runlily import runLilyPond
    runLilyPond(kate.document(), preview=True)

@menu.add(_("Run LilyPond (publish)"), "Ctrl+Shift+P", "ly")
def publish():
    from lilykde.runlily import runLilyPond
    runLilyPond(kate.document())

menu.insert(KActionSeparator())

@menu.add(_("Clear LilyPond Log"), "", "eraser")
def clearLog():
    if 'lilykde.log' in sys.modules:
        sys.modules['lilykde.log'].clear()

menu.insert(KActionSeparator())

@menu.add(_("Insert LilyPond version (%s)"), "Ctrl+Shift+V", "ok")
def insertVersion():
    from lilykde import version
    version.insertVersion()

insertVersion.setEnabled(False)

@menu.add(_("Update with convert-ly"), "", "add")
def convertLy():
    from lilykde import version
    version.convertLy()

menu.insert(KActionSeparator())

@menu.add(_("Hyphenate text"), "Ctrl+Shift+H")
def hyphenateText():
    from lilykde import hyphen
    hyphen.hyphenateText()

@menu.add(_("Remove hyphenation"))
def deHyphenateText():
    from lilykde import hyphen
    hyphen.deHyphenateText()



# kate: indent-width 4;
