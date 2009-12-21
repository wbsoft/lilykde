# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
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
Helper classes for communication with UserShortcutManager (in mainwindow.py)
and general user shortcut stuff.

In separate module so this can be lazy-loaded on demand.
"""

import weakref

from PyQt4.QtGui import QGridLayout, QKeySequence, QLabel
from PyKDE4.kdecore import KGlobal, i18n
from PyKDE4.kdeui import KDialog, KKeySequenceWidget, KShortcut

from kateshell.app import blockSignals


class ShortcutClientBase(object):
    """
    Abstract base class for objects that need to manage shortcuts.
    """
    def __init__(self, userShortcutManager):
        self._manager = userShortcutManager
        self._collection = userShortcutManager._collection
    
    def populateAction(self, name, action):
        """
        Must implement this to populate the action based on the given name.
        """
        pass
    
    def actionTriggered(self, name):
        """
        Must implement this to perform the action that belongs to name.
        """
        pass


class ShortcutClient(ShortcutClientBase):
    """
    Base class for objects that need to manage shortcuts.
    """
    def resolveName(self, name):
        return name
        
    def shortcutActions(self):
        """
        Yields two-tuples(name, action) for all our actions.
        """
        for action in self._collection.actions()[:]: # copy
            yield action.objectName(), action

    def shortcut(self, name):
        """
        Returns the shortcut for action, if existing.
        """
        resolvedName = self.resolveName(name)
        action = self._collection.action(resolvedName)
        if action:
            if not action.shortcut().isEmpty():
                return action.shortcut()
            self.removeShortcut(name)
    
    def setShortcut(self, name, shortcut):
        """
        Sets the shortcut for the named action.
        Creates an action if not existing.
        Deletes the action if set to an empty key sequence.
        """
        resolvedName = self.resolveName(name)
        if not shortcut.isEmpty():
            action = self._manager.addAction(resolvedName)
            action.setShortcut(shortcut)
            self._collection.writeSettings(None, True, action)
        else:
            self.removeShortcut(name)
    
    def removeShortcut(self, name):
        """
        Deletes the given action if existing.
        """
        resolvedName = self.resolveName(name)
        action = self._collection.action(resolvedName)
        if action:
            action.deleteLater()
            KGlobal.config().group(self._manager.configGroup).deleteEntry(resolvedName)
    
    def shortcuts(self):
        """
        Returns the list of names we have non-empty shortcuts for.
        """
        return [name
            for name, action in self.shortcutActions()
            if not action.shortcut().isEmpty()]
                
    def shakeHands(self, names):
        """
        Deletes all actions not in names, and returns a list of the names
        we have valid actions for.
        """
        result = []
        for name, action in self.shortcutActions():
            if name not in names:
                self.removeShortcut(name) 
            elif not action.shortcut().isEmpty():
                result.append(name)
        return result
        
    def shortcutText(self, name):
        """
        Returns the shortcut keys as a readable string, e.g. "Ctrl+Alt+D"
        """
        key = self.shortcut(name)
        return key and key.toList()[0].toString() or ''
        
    def keySetCheckActionCollections(self, keySequenceWidget):
        keySequenceWidget.setCheckActionCollections(
            [coll for name, coll in self._manager.mainwin.allActionCollections()])
    
    def keyLoadShortcut(self, keySequenceWidget, name):
        """
        Sets the KKeySequenceWidget in key to the sequence stored for name.
        """
        key = self.shortcut(name)
        with blockSignals(keySequenceWidget) as w:
            w.setKeySequence(key and key.toList()[0] or QKeySequence())

    def keySaveShortcut(self, keySequenceWidget, name, keySequence = None):
        """
        Stores the shortcut in the KKeySequenceWidget under 'name'.
        """
        if keySequence is None:
            keySequence = keySequenceWidget.keySequence()
        keySequenceWidget.applyStealShortcut()
        self.setShortcut(name, KShortcut(keySequence))
            
    def editShortcut(self, name, title, icon=None, globalPos=None):
        """
        Shows a dialog to set a keyboard shortcut for a name (string).
        The title argument should contain a description for this action.
        """
        dlg = KDialog(self._manager.mainwin)
        dlg.setCaption(i18n("Configure Keyboard Shortcut"))
        dlg.setButtons(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel))
        l = QGridLayout(dlg.mainWidget())
        l.setHorizontalSpacing(12)
        if icon:
            pic = QLabel()
            pic.setPixmap(icon.pixmap(22))
            l.addWidget(pic, 0, 0)
        l.addWidget(QLabel("<p>{0}<br /><b>{1}</b></p>".format(
            i18n("Press the button to configure the keyboard shortcut for:"), title)), 0, 1)
        key = KKeySequenceWidget()
        l.addWidget(key, 1, 1)
        self.keySetCheckActionCollections(key)
        self.keyLoadShortcut(key, name)
        if dlg.exec_():
            self.keySaveShortcut(key, name)


class UserShortcutDispatcher(ShortcutClientBase):
    """
    Communicates with a UserShortcuts object to handle shortcuts for
    different clients.
    
    Objects that wants to use this class can either mix it in or instantiate
    it as an helper object.
    
    Clients register with a string name, and all the shortcut names for that
    client get that name prepended.
    """
    def __init__(self, userShortcutManager):
        self._manager = userShortcutManager
        self._clients = weakref.WeakValueDictionary()
        
    def registerClient(self, client, name):
        self._clients[name] = client
        
    def populateAction(self, name, action):
        """ Dispatch to the correct client. """
        if ':' in name:
            client, name = name.split(':', 1)
            if client in self._clients:
                self._clients[client].populateAction(name, action)
                
    def actionTriggered(self, name):
        """ Dispatch to the correct client. """
        if ':' in name:
            client, name = name.split(':', 1)
            if client in self._clients:
                self._clients[client].actionTriggered(name)


class ShortcutDispatcherClient(ShortcutClient):
    """
    Base class for clients of a UserShortcutDispatcher.
    """
    def __init__(self, dispatcher, name):
        ShortcutClient.__init__(self, dispatcher._manager)
        dispatcher.registerClient(self, name)
        self._name = name
        
    def resolveName(self, name):
        return self._name + ":" + name
        
    def shortcutActions(self):
        """
        Yields two-tuples(name, action) for all our actions.
        """
        for action in self._collection.actions()[:]: # copy
            if action.objectName().startswith(self._name + ":"):
                yield action.objectName().split(":", 1)[1], action


