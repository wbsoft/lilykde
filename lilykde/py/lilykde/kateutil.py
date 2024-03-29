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
Utility functions for interacting with Kate.
"""
from qt import QDialog, QVBoxLayout, QPoint, QWidget
import sip

import kate

from lilykde import config
from lilykde.widgets import sorry
from lilykde.about import PROGRAMNAME


class DockDialog(QDialog):
    """
    A QDialog that (re)docks itself when closed.
    """
    def __init__(self, dockable, parent = None):
        super(DockDialog, self).__init__(parent)
        self.dockable = dockable

    def closeEvent(self, e):
        self.dockable.dock()


class Dockable(object):
    """
    Holds a a widget, and makes it possible to dock and undock
    the widget in/from the tool view sidebar.

    title, name and orientation are given to the kate.gui.Tool.
    size may hold a tuple (width, height).
    if focus is False: do not allow keyboard focus when docked.

    The orientation is one of Dockable.{top,right,bottom,left}
    """
    top    = kate.gui.Tool.top
    right  = kate.gui.Tool.right
    bottom = kate.gui.Tool.bottom
    left   = kate.gui.Tool.left

    def __init__(self, widget, title, name, orientation,
            size = None, focus = True):
        self.title = title
        self.name = name
        self.orientation = orientation
        self.focus = focus
        self.widget = widget

        self.tool = None
        self.dialog = None
        self.dialogSize = size
        self.dialogPos = None
        self.dock()

    def dock(self):
        """
        Docks the widget in a Kate sidebar tool view.
        """
        if not self.tool:
            t = kate.gui.Tool(self.title, self.name, self.orientation)
            self.widget.reparent(t.widget, QPoint(0, 0))
            if not self.focus:
                self.widget.setFocusPolicy(QWidget.NoFocus)
            self.tool = t
            if self.dialog:
                # remember dialog size
                self.dialogSize = self.dialog.width(), self.dialog.height()
                pos = self.dialog.pos()
                self.dialogPos = pos.x(), pos.y()
                sip.delete(self.dialog)
                self.dialog = None
            self.show()

    def undock(self):
        """
        Undocks the widget and place it in a QDialog
        """
        if not self.dialog:
            parent = None
            if config("preferences")["keep undocked on top"] != '0':
                parent = kate.mainWidget()
            d = DockDialog(self, parent)
            d.setCaption("%s - %s" % (self.title, PROGRAMNAME))
            if self.dialogSize:
                d.resize(*self.dialogSize)
            if self.dialogPos:
                d.move(*self.dialogPos)
            QVBoxLayout(d).setAutoAdd(True)
            self.widget.reparent(d, QPoint(0, 0))
            if not self.focus:
                self.widget.setFocusPolicy(QWidget.WheelFocus)
            self.dialog = d
            if self.tool:
                sip.delete(self.tool.widget)
                self.tool = None
            self.show()

    def docked(self):
        """
        Returns True if the widget is docked.
        """
        return bool(self.tool)

    def show(self):
        """ Show the widget """
        w = self.tool or self.dialog
        if w:
            w.show()

    def hide(self):
        """ Hide the widget. Not when undocked. """
        if self.tool:
            self.tool.hide()

    def toggle(self):
        """ Toggle dock / undock """
        if self.tool:
            self.undock()
        else:
            self.dock()


# kate: indent-width 4;
