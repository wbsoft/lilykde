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

from PyQt4.QtGui import QCheckBox, QGridLayout, QLabel, QLineEdit, QVBoxLayout, QWidget
from PyKDE4.kdecore import KUrl, i18n
from PyKDE4.kdeui import KDialog, KHBox, KIcon, KMessageBox, KPageDialog, KStandardGuiItem
from PyKDE4.kio import KFile, KUrlRequester

import kateshell.widgets
from kateshell.app import cacheresult


class ManagerDialog(KDialog):
    """A dialog to list the sessions and edit, add or delete them."""
    def __init__(self, manager):
        KDialog.__init__(self, manager.mainwin)
        self.sm = manager
        self.setCaption(i18n("Manage Sessions"))
        self.setButtons(KDialog.ButtonCode(KDialog.Help | KDialog.Close))
        self.setHelp("sessions")
        self.sessions = SessionList(self)
        self.setMainWidget(self.sessions)
        self.sm.sessionAdded.connect(self.load)
        
    def show(self):
        self.load()
        KDialog.show(self)
    
    def load(self):
        self.sessions.load()


class SessionList(kateshell.widgets.ListEdit):
    """Manage the list of sessions."""
    def __init__(self, dialog):
        self.sm = dialog.sm # SessionManager
        super(SessionList, self).__init__(dialog)
        
    def load(self):
        names, current = self.sm.names(), self.sm.current()
        self.setValue(names)
        if current in names:
            self.setCurrentRow(names.index(current))

    def removeItem(self, item):
        self.sm.deleteSession(item.text())
        super(SessionList, self).removeItem(item)

    def openEditor(self, item):
        name = self.sm.editorDialog().edit(item.text())
        if name:
            item.setText(name)
            return True


class EditorDialog(KPageDialog):
    """A dialog to edit properties of a session."""
    def __init__(self, manager):
        super(EditorDialog, self).__init__(manager.mainwin)
        self.mainwin = manager.mainwin
        self.sm = manager
        self.setButtons(KDialog.ButtonCode(
            KDialog.Help | KDialog.Ok | KDialog.Cancel))
        self.setFaceType(KPageDialog.List)
        self.setHelp("sessions")
        
        # First page with name and auto-save option
        page = QWidget(self)
        item = self.firstPage = self.addPage(page, i18n("Session"))
        item.setHeader(i18n("Properties of this session"))
        item.setIcon(KIcon("configure"))
        
        layout = QGridLayout(page)
        
        l = QLabel(i18n("Name:"))
        self.name = QLineEdit()
        l.setBuddy(self.name)
        layout.addWidget(l, 0, 0)
        layout.addWidget(self.name, 0, 1)
        
        self.autosave = QCheckBox(i18n(
            "Always save the list of documents in this session"))
        layout.addWidget(self.autosave, 1, 1)
        
        l = QLabel(i18n("Base directory:"))
        self.basedir = KUrlRequester()
        self.basedir.setMode(KFile.Mode(
            KFile.Directory | KFile.ExistingOnly | KFile.LocalOnly))
        l.setBuddy(self.basedir)
        layout.addWidget(l, 2, 0)
        layout.addWidget(self.basedir, 2, 1)
        
    def edit(self, name=None):
        """Edit the named or new (if not given) session."""
        # load the session
        self._originalName = name
        if name:
            self.setCaption(i18n("Edit session: %1", name))
            self.name.setText(name)
            conf = self.sm.config(name)
            self.autosave.setChecked(conf.readEntry("autosave", True))
            self.basedir.setUrl(KUrl(conf.readPathEntry("basedir", "")))
        else:
            self.setCaption(i18n("Edit new session"))
            self.name.clear()
            self.name.setFocus()
            self.autosave.setChecked(True)
            self.basedir.setUrl(KUrl())
        if self.exec_():
            # save
            name = self.name.text()
            if self._originalName and name != self._originalName:
                self.sm.renameSession(self._originalName, name)
            conf = self.sm.config(name)
            conf.writeEntry("autosave", self.autosave.isChecked())
            conf.writePathEntry("basedir", self.basedir.url().path())
            return name

    def done(self, result):
        if not result or self.validate():
            super(EditorDialog, self).done(result)
        
    def validate(self):
        """Checks if the input is acceptable.
        
        If this method returns True, the dialog is accepted when OK is clicked.
        Otherwise a messagebox could be displayed, and the dialog will remain
        visible.
        """
        # strip off whitespace
        name = self.name.text().strip()
        self.name.setText(name)
        
        if not name:
            KMessageBox.error(self, i18n("Please enter a session name."))
            if self._originalName:
                self.name.setText(self._originalName)
            self.setCurrentPage(self.firstPage)
            self.name.setFocus()
            return False
        
        if name == 'none':
            KMessageBox.error(self, i18n(
                "Please do not use the name '%1'.", "none"))
            self.setCurrentPage(self.firstPage)
            self.name.setFocus()
            return False
        
        if '&' in name:
            KMessageBox.error(self, i18n(
                "Please do not use the ampersand (&) character "
                "in a session name."))
            self.setCurrentPage(self.firstPage)
            self.name.setFocus()
            return False
            
        if self._originalName != name and name in self.sm.names():
            if KMessageBox.warningContinueCancel(self, i18n(
                "Another session with the name %1 exists already.\n\n"
                "Do you want to overwrite it?", name), None,
                KStandardGuiItem.overwrite(), KStandardGuiItem.cancel(),
                "session_overwrite") == KMessageBox.Cancel:
                self.setCurrentPage(self.firstPage)
                self.name.setFocus()
                return False
            
        return True
    
