"""
This is the LilyPond Kate main menu.

You can disable actions by calling lymenu.action.setEnabled(false), e.g.
lymenu.preview.setEnabled(False)

You can call actions by calling e.g. lymenu.publish.activate()
"""
import sys
import kate

# translate the messages
from lilykde_i18n import _

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
    import lilykde
    lilykde.runLilyPond(kate.document(), preview=True)

@menu.add(_("Run LilyPond (publish)"), "Ctrl+Shift+P", "ly")
def publish():
    import lilykde
    lilykde.runLilyPond(kate.document())

menu.insert(KActionSeparator())

@menu.add(_("Clear LilyPond Log"), "", "eraser")
def clearLog():
    if 'lilykde' in sys.modules:
        import lilykde
        lilykde.LogWindow().clear()

menu.insert(KActionSeparator())

@menu.add(_("Insert LilyPond version ()"), "Ctrl+Shift+V", "ok")
def insertVersion():
    import lyversion
    lyversion.insertVersion()

insertVersion.setEnabled(False)



# kate: indent-width 4;
