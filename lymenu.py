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

menu = KActionMenu(_("LilyPond"), None, "lilypond")

def add(name, shortcut=None, icon=None):
    """
    This function returns a function that when called returns a KAction.
    """
    def action(func):
        global menu
        a = KAction(name, icon or "", KShortcut(shortcut or ""), func, menu, "")
        menu.insert(a)
        return a
    return action

@add(_("Run LilyPond (preview)"), "Ctrl+Shift+M", "ly")
def preview():
    import lilykde
    lilykde.runLilyPond(kate.document(), preview=True)

@add(_("Run LilyPond (publish)"), "Ctrl+Shift+P", "ly")
def publish():
    import lilykde
    lilykde.runLilyPond(kate.document())

menu.insert(KActionSeparator())

@add(_("Clear LilyPond Log"))
def clearLog():
    if 'lilykde' in sys.modules:
        import lilykde
        lilykde.LogWindow().clear()

@kate.onWindowShown
def initLilyPond():
    global menu
    menu.plug(kate.mainWidget().topLevelWidget().menuBar(), 5)
