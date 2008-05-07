"""
Part types for the Score Wizard (scorewiz.py).

In separate file to ease maintenance.
"""

# Translate titles, etc.
from lilykde.i18n import _
from lilykde.scorewiz import part

class Violin(part):
    name = _("Violin")
    pass

class Organ(part):
    name = _("Organ")
    pass

class Piano(part):
    name = _("Piano")
    pass


# The structure of the overview
categories = (
    (_("Strings"),
        (Violin,)),
    (_("Keyboards"),
        (Organ, Piano)),
)


