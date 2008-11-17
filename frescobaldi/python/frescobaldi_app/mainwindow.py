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
from PyKDE4.kio import *

class _signalstore(dict):
    def __new__(cls):
        return dict.__new__(cls)
    def call(self, meth, obj):
        for f in self[meth]:
            f(obj)
    def add(self, *methods):
        for meth in methods:
            self[meth] = []
    def remove(self, *methods):
        for meth in methods:
            del self[meth]

# global hash with listeners
listeners = _signalstore()



class MainWindow(KParts.MainWindow):
    def __init__(self, app):
        super(MainWindow, self).__init__()
        self.app = app
        self._currentDoc = None
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)
        self.resize(500,400) # FIXME: save window size and set reasonable default
        self.show()
        listeners[app.activeChanged].append(self.showDoc)
        listeners[app.activeChanged].append(self.updateCaption)
        listeners[app.activeChanged].append(self.updateStatusBar)

        # status bar
        sb = self.statusBar()
        self.sb_linecol = QLabel(sb)
        sb.addWidget(self.sb_linecol, 0)
        
        self.sb_modified = QLabel(sb)
        self.sb_modified.setFixedSize(16, 16)
        sb.addWidget(self.sb_modified, 0)
        
        self.sb_insmode = QLabel(sb)
        sb.addWidget(self.sb_insmode, 0)
        
        self.sb_selmode = QLabel(sb)
        sb.addWidget(self.sb_selmode, 0)
        
        

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
        action('file_open', KStandardAction.Open, self.openDocument)
        action('file_close', KStandardAction.Close,
            lambda: app.activeDocument().close())
        action('file_quit', KStandardAction.Quit, app.quit)
        action('doc_back', KStandardAction.Back, app.back)
        action('doc_forward', KStandardAction.Forward, app.forward)
        
        self.setXMLFile("frescobaldiui.rc")
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
        if self._currentDoc:
            listeners[self._currentDoc.updateCaption].remove(self.updateCaption)
            listeners[self._currentDoc.updateStatus].remove(self.updateStatusBar)
            self.guiFactory().removeClient(self._currentDoc.view)
        self._currentDoc = doc
        self.guiFactory().addClient(doc.view)
        self.stack.setCurrentWidget(doc.view)
        listeners[doc.updateCaption].append(self.updateCaption)
        listeners[doc.updateStatus].append(self.updateStatusBar)
        doc.view.setFocus()

    def addDoc(self, doc):
        self.stack.addWidget(doc.view)
        
    def removeDoc(self, doc):
        self.stack.removeWidget(doc.view)
        if doc is self._currentDoc:
            self.guiFactory().removeClient(doc.view)
            self._currentDoc = None

    def updateCaption(self, doc):
        if doc.isModified():
            self.setCaption(doc.documentName() + " [%s]" % i18n("modified"))
            self.sb_modified.setPixmap(KIcon("document-properties").pixmap(16))
        else:
            self.setCaption(doc.documentName())
            self.sb_modified.setPixmap(QPixmap())
    
    def updateStatusBar(self, doc):
        pos = doc.view.cursorPositionVirtual()
        line, col = pos.line()+1, pos.column()
        self.sb_linecol.setText(i18n("Line: %1 Col: %2", line, col))
        
        if doc.view.blockSelection():
            t, w = i18n("BLOCK"), i18n("Block selection mode")
        else:
            t, w = i18n("LINE"), i18n("Line selection mode")
        self.sb_selmode.setText(" %s " % t)
        self.sb_selmode.setToolTip(w)
        
        self.sb_insmode.setText(doc.view.viewMode())

    def populateDocMenu(self):
        for a in self.docGroup.actions():
            sip.delete(a)
        for d in self.app.documents:
            a = KAction(d.documentName(), self.docGroup)
            a.setCheckable(True)
            a.doc = d
            if d.isModified():
                a.setIcon(KIcon("document-save"))
            elif d.isEdited():
                a.setIcon(KIcon("dialog-ok-apply"))
            elif d.doc:
                a.setIcon(KIcon("dialog-ok"))
            if d is self._currentDoc:
                a.setChecked(True)
            self.docGroup.addAction(a)
            self.docMenu.addAction(a)

    def openDocument(self):
        """ Open an existing document. """
        res = KEncodingFileDialog.getOpenUrlsAndEncoding(
            'UTF-8', '::lilypond', "*.ly *.ily *.lyi|%s\n*|%s"
            % (i18n("LilyPond files"), i18n("All Files")),
            self, i18n("Open File"))
        for url in res.URLs:
            if url != '':
                self.app.openUrl(unicode(url.url()), res.encoding)

    def queryClose(self):
        """ Quit the application, also called by closing the window """
        for d in self.app.documents[:]: # iterate over a copy
            if d.isModified():
                d.setActive()
            if not d.close(True):
                return False
        return True
        