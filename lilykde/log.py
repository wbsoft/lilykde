""" A Log Window.
On first import a tool view is created.
"""

import kate

from qt import QWidget

from lilykde.widgets import LogWidget

# Translate the messages
from lilykde.i18n import _


tool = kate.gui.Tool(_("LilyPond Log"), "log", kate.gui.Tool.bottom)
log = LogWidget(tool.widget)
log.setFocusPolicy(QWidget.NoFocus)
log.show()
tool.show()

# make these easily available
show = tool.show
hide = tool.hide

def logWidget():
    return log
