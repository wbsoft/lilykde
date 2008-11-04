# This file is part of LilyKDE, http://lilykde.googlecode.com/
#
# Copyright (c) 2008  Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# See http://www.gnu.org/licenses/ for more information.

"""
A Log Window.
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
clear = log.clear

def logWidget():
    return log
