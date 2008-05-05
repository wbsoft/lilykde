"""
Part types for the Score Wizard (scorewiz.py).

In separate file to ease maintenance
"""

# Translate titles, etc.
from lilykde.i18n import _

from lilykde.scorewiz import part

class Organ(part):
    name = _("Church organ")
    pass

class Piano(part):
    name = _("Piano")
    pass

class Violin(part):
    name = _("Violin")
    pass

# The structure of the overview
categories = (
    (_("Keyboards"),
        (Organ, Piano)),
    (_("Strings"),
        (Violin,)),
)


