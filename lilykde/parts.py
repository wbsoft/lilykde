"""
Part types for the Score Wizard (scorewiz.py).

In separate file to ease maintenance.
"""

# Translate titles, etc.
from lilykde.i18n import _
from lilykde.scorewiz import part
from lilydom import *

class Violin(part):
    name = _("Violin")
    pass

class Organ(part):
    name = _("Organ")
    pass

class Piano(part):
    name = _("Piano")

    def build(self):
        """
        Must return:
        1 -
        May also return lists of assignments and resp. cids (both Python Lists)
        to resolve naming conflicts later.
        """
        p = self.addPart(PianoStaff)
        p.instrName("Piano", "Pi")
        s = Sim(p)
        r = Seq(Staff(s, 'right'))
        Text(r, '\\clef treble\n')
        l = Seq(Staff(s, 'left'))
        Text(l, '\\clef bass\n')
        self.assignMusic('right', r, 0)
        self.assignMusic('left', l, -1)





# The structure of the overview
categories = (
    (_("Strings"),
        (Violin,)),
    (_("Keyboards"),
        (Organ, Piano)),
)


