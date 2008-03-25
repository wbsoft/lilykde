"""
Utility functions for interacting with Kate
"""

import kate

# Translate the messages
from lilykde.i18n import _

def runOnSelection(func):
    """
    A decorator that makes a function run on the selection,
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


# kate: indent-width 4;
