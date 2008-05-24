"""
This is the LilyPond Kate main menu.

You can disable actions by calling menu.child("name").setEnabled(false), e.g.
menu.child("preview").setEnabled(False)

You can call actions by calling e.g. menu.child("publish").activate().

The name of each action is set to the function name.
"""
import sys
import kate

# Translate the messages
from lilykde.i18n import _

# setup LilyPond menu. Somehow it seems not to be possible to use pate's
# standard decorators on an own toplevel menu.
# The menu is not yet created, etc. Just setup our own.
from kdecore import KShortcut
from kdeui import KAction, KActionMenu, KActionSeparator

def add(menu, text, key="", icon=""):
    """ Returns a function that when called returns a KAction. """
    def action(f):
        # Give the KAction the name of the function it calls
        menu.insert(KAction(text, icon, KShortcut(key), f, menu, f.func_name))
        return f
    return action

menu = KActionMenu(_("LilyPond"))

@add(menu, _("Setup New Score..."), "", "filenew")
def scoreWizard():
    from lilykde import scorewiz
    #scorewiz.ScoreWizard(kate.mainWidget()).exec_loop()
    scorewiz.scorewiz.show()

@add(menu, _("Run LilyPond (preview)"), "Ctrl+Shift+M", "ly")
def preview():
    from lilykde import runlily
    runlily.runLilyPond(kate.document(), preview=True)

@add(menu, _("Run LilyPond (publish)"), "Ctrl+Shift+P", "ly")
def publish():
    from lilykde import runlily
    runlily.runLilyPond(kate.document())

menu.insert(KActionSeparator())

@add(menu, _("Interrupt LilyPond Job"), "Shift+Esc", "stop")
def interrupt():
    from lilykde import runlily
    runlily.interrupt(kate.document())

@add(menu, _("Clear LilyPond Log"), "", "eraser")
def clearLog():
    if 'lilykde.log' in sys.modules:
        sys.modules['lilykde.log'].clear()

menu.insert(KActionSeparator())

@add(menu, _("Insert LilyPond version (%s)"), "Ctrl+Shift+V", "ok")
def insertVersion():
    from lilykde import version
    version.insertVersion()

menu.child("insertVersion").setEnabled(False)

@add(menu, _("Update with convert-ly"), "", "add")
def convertLy():
    from lilykde import version
    version.convertLy()

menu.insert(KActionSeparator())

@add(menu, _("Hyphenate Lyrics Text"), "Ctrl+Shift+H")
def hyphenateText():
    from lilykde import hyphen
    hyphen.hyphenateText()

@add(menu, _("Remove hyphenation"))
def deHyphenateText():
    from lilykde import hyphen
    hyphen.deHyphenateText()

menu.insert(KActionSeparator())

@add(menu, _("Record MIDI with Rumor"), "Ctrl+Shift+R")
def rumor():
    import lilykde.rumor
    lilykde.rumor.show()


# kate: indent-width 4;
