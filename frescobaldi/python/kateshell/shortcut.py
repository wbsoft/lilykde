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

"""
Helper classes for communication with UserShortcutManager (in mainwindow.py)
and general user shortcut stuff.
"""

import weakref

from PyQt4.QtGui import QKeySequence, QLabel, QVBoxLayout
from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KDialog, KKeySequenceWidget, KShortcut

from kateshell.app import blockSignals

class ShortcutClient(object):
    """
    Abstract base class (not obligate) for objects that need to manage shortcuts.
    """
    def __init__(self, userShortcutManager):
        self._shortcuts = userShortcutManager
        
    def setShortcut(self, name, shortcut):
        self._shortcuts.setShortcut(name, shortcut)
        
    def shortcut(self, name):
        return self._shortcuts.shortcut(name)
    
    def shortcutText(self, name):
        """
        Returns the shortcut keys as a readable string, e.g. "Ctrl+Alt+D"
        """
        key = self.shortcut(name)
        return key and key.toList()[0].toString() or ''
        
    def keySetCheckActionCollections(self, keySequenceWidget):
        mainwin = self._shortcuts.mainwin
        keySequenceWidget.setCheckActionCollections(
            [coll for name, coll in mainwin.allActionCollections()])
    
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
        mainwin = self._shortcuts.mainwin
        dlg = KDialog(mainwin)
        dlg.setCaption(i18n("Configure keyboard shortcut"))
        dlg.setButtons(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel))
        l = QVBoxLayout(dlg.mainWidget())
        l.addWidget(QLabel("<p>{0}<br /><b>{1}</b></p>".format(
            i18n("Press the button to configure the keyboard shortcut for:"), title)))
        key = KKeySequenceWidget()
        l.addWidget(key)
        self.keySetCheckActionCollections(key)
        self.keyLoadShortcut(key, name)
        key.setKeySequence(shortcut and shortcut.toList()[0] or QKeySequence())
        if dlg.exec_():
            self.keySaveShortcut(key, name)

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
    

class UserShortcutDispatcher(ShortcutClient):
    """
    Communicates with a UserShortcuts object to handle shortcuts for
    different clients.
    
    Objects that wants to use this class can either mix it in or instantiate
    it as an helper object.
    
    Clients register with a string name, and all the shortcut names for that
    client get that name prepended.
    
    Clients need to provide almost the same two methods as when communicating
    with a UserShortcuts object directly:
    
    - populateAction(name, action)      # instead of only the action
    - actionTriggered(name)
    """
    def __init__(self, userShortcutManager):
        ShortcutClient.__init__(self, userShortcutManager)
        self._clients = weakref.WeakValueDictionary()
        
    def registerClient(self, client, name):
        self._clients[name] = client
        
    def populateAction(self, action):
        """ Dispatch to the correct client. """
        if ':' in action.objectName():
            client, name = action.objectName().split(':')
            if client in self._clients:
                self._clients[client].populateAction(name, action)
                
    def actionTriggered(self, name):
        """ Dispatch to the correct client. """
        if ':' in name:
            client, name = name.split(':')
            if client in self._clients:
                self._clients[client].actionTriggered(name)


class ShortcutDispatcherClient(ShortcutClient):
    """
    Base class for clients of a UserShortcutDispatcher.
    """
    def __init__(self, dispatcher, name):
        self._name = name
        self._shortcuts = dispatcher._shortcuts
        dispatcher.registerClient(self, name)
        
    def setShortcut(self, name, shortcut):
        self._shortcuts.setShortcut(self._name + ":" + name, shortcut)
        
    def shortcut(self, name):
        return self._shortcuts.shortcut(self._name + ":" + name)
        
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


