# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
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

import sip

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kparts import KParts
from PyKDE4.ktexteditor import KTextEditor

from .actions import setupActions

class _signalstore(dict):
    def __new__(cls):
        return dict.__new__(cls)
    def call(self, meth, obj):
        for f in self[meth]:
            f(obj)
    def add(self, meth):
        self[meth] = []
    def remove(self, meth):
        del self[meth]

# global hash with listeners
listeners = _signalstore()



class MainWindow(KParts.MainWindow):
    def __init__(self, app):
        super(MainWindow, self).__init__()
        self.app = app
        self._currentView = None
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)
        self.resize(500,400) # FIXME: save window size and set reasonable default
        self.show()
        listeners[app.activeChanged].append(self.showDoc)
        listeners[app.activeChanged].append(self.updateState)

            
        # actions, helper function
        def action(name, texttype, func, icon=None, whatsthis=None, key=None):
            if isinstance(texttype, KStandardAction.StandardAction):
                a = self.actionCollection().addAction(texttype, name)
            else:
                a = self.actionCollection().addAction(name)
                a.setText(texttype)
            QObject.connect(a, SIGNAL("triggered()"), func)
            if icon: a.setIcon(KIcon(icon))
            if whatsthis: a.setWhatsThis(whatsthis)
            if key: a.setShortcut(KShortcut(key))
        
        action('file_new', KStandardAction.New, app.new)
        action('file_close', KStandardAction.Close,
            lambda: app.history[-1].close()) # FIXME, make more robust

        self.createShellGUI(True)

        # Documents menu
        self.docMenu = self.factory().container("documents", self)
        self.docGroup = QActionGroup(self.docMenu)
        self.docGroup.setExclusive(True)
        QObject.connect(self.docMenu, SIGNAL("aboutToShow()"),
            self.populateDocMenu)
        QObject.connect(self.docGroup, SIGNAL("triggered(QAction*)"),
            lambda a: a.doc.setActive())
        

    def showDoc(self, doc):
        if self._currentView:
            self.guiFactory().removeClient(self._currentView)
        self.guiFactory().addClient(doc.view)
        self._currentView = doc.view
        self.stack.setCurrentWidget(doc.view)
        doc.view.setFocus()

    def addView(self, view):
        self.stack.addWidget(view)
        
    def removeView(self, view):
        self.stack.removeWidget(view)
        if view is self._currentView:
            self.guiFactory().removeClient(view)
            self._currentView = None

    def updateState(self, doc):
        if doc.view is not self._currentView:
            return
        title = doc.title()
        if doc.isModified():
            title += " [%s]" % i18n("modified")
        self.setCaption(title)

    def populateDocMenu(self):
        for a in self.docGroup.actions():
            sip.delete(a)
        for d in self.app.documents:
            a = KAction(d.title(), self.docGroup)
            a.setCheckable(True)
            a.doc = d
            if d.isModified():
                a.setIcon(KIcon("document-save"))
            if self._currentView is d.view:
                a.setChecked(True)
            self.docGroup.addAction(a)
            self.docMenu.addAction(a)
