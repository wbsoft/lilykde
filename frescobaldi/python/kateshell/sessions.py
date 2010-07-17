# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

from __future__ import unicode_literals

"""
Code for managing editor sessions.
See SessionManager (started on startup) in mainwindow.py.
"""

from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KDialog, KPageDialog

import kateshell.widgets
from kateshell.app import cacheresult


class ManagerDialog(KDialog):
    """A dialog to list the sessions and edit, add or delete them."""
    def __init__(self, manager):
        KDialog.__init__(self, manager.mainwin)
        self.sm = manager
        self.mainwin = manager.mainwin
        self.setCaption(i18n("Manage Sessions"))
        self.setButtons(KDialog.ButtonCode(KDialog.Help | KDialog.Close))
        self.sessions = SessionList(self)
        self.setMainWidget(self.sessions)
        
    def show(self):
        self.sessions.load()
        KDialog.show(self)


class SessionList(kateshell.widgets.ListEdit):
    """Manage the list of sessions."""
    def __init__(self, dialog):
        self.sm = dialog.sm # SessionManager
        super(SessionList, self).__init__(dialog)
        
    def load(self):
        self.clear()
        self.setValue(self.sm.names())

    def removeItem(self, item):
        self.sm.deleteSession(item.text())
        super(SessionList, self).removeItem(item)


class EditorDialog(KPageDialog):
    """A dialog to edit properties of one session."""
    
    
    
    