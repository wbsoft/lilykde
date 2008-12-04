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

import os, sip, dbus, dbus.service, dbus.mainloop.qt
from dbus.service import method, signal

from PyQt4.QtCore import QObject, SIGNAL
from PyKDE4.kdecore import i18n, KGlobal, KUrl
from PyKDE4.kdeui import KApplication
from PyKDE4.ktexteditor import KTextEditor

from kateshell import DBUS_IFACE_PREFIX
from kateshell.mainwindow import MainWindow, listeners


# Make the Qt mainloop the default one
dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)

class DBusItem(dbus.service.Object):
    """
    An exported DBus item for our application.
    To be subclassed!
    """
    def __init__(self, serviceName, path=None):
        self.serviceName = serviceName
        if path is None:
            path = '/%s' % self.__class__.__name__
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(self.serviceName, bus)
        dbus.service.Object.__init__(self, bus_name, path)
    

class MainApp(DBusItem):
    """
    Our main application instance. Also exposes some methods to DBus.
    Instantiated only once.
    """
    iface = DBUS_IFACE_PREFIX + "MainApp"
    defaultEncoding = 'UTF-8'
    defaultHighlightingMode = None
    fileTypes = []
    
    def __init__(self, servicePrefix):
        # listeners to our events
        listeners.add(self.activeChanged)
        # We manage our own documents.
        self.documents = []
        self.history = []       # latest shown documents

        # KApplication needs to be instantiated before any D-Bus stuff
        self.kapp = KApplication()
        serviceName = "%s%d" % (servicePrefix, os.getpid())
        DBusItem.__init__(self, serviceName, '/MainApp')

        # We support only one MainWindow.
        self.mainwin = self.createMainWindow()
        self.kapp.setTopWidget(self.mainwin)

        # Get our beloved editor :-)
        self.editor = KTextEditor.EditorChooser.editor()


        # restore session etc.

    def createMainWindow(self):
        return MainWindow(self)

    def createDocument(self, url="", encoding=None):
        return Document(self, url, encoding)
        
    def findDocument(self, url):
        """ Return the opened document or False. """
        for d in self.documents:
            if d.url() == url:
                return d
        return False
    
    @method(iface, in_signature='ss', out_signature='o')
    def openUrl(self, url, encoding=None):
        if not encoding:
            encoding = self.defaultEncoding
        # If there is only one document open and it is empty, nameless and
        # unmodified, close it.
        close0 = (url and len(self.documents) == 1
            and not self.documents[0].isModified()
            and not self.documents[0].url()
            and self.documents[0].isEmpty())
        d = (url and self.findDocument(url)
            or self.createDocument(url, encoding))
        d.setActive()
        if close0:
            self.documents[0].close()
        return d

    @method(iface, in_signature='', out_signature='o')
    def new(self):
        d = self.createDocument()
        d.setActive()
        return d

    @method(iface, in_signature='', out_signature='', sender_keyword="sender")
    def run(self, sender=None):
        """
        Is called by a remote app after new documents are opened.
        Currently need not to do anything.
        
        If we are the caller ourselves, enter the KDE event loop.
        """
        if sender is not None:
            return
        # At the very last, instantiate one empty doc if nothing loaded yet.
        if len(self.documents) == 0:
            self.createDocument().setActive()
        self.kapp.exec_()
        KGlobal.config().sync()
       
    @method(iface, in_signature='s', out_signature='b')
    def isOpen(self, url):
        """
        Returns true is the specified URL is opened by the current application
        """
        return bool(self.findDocument(url))
        
    @method(iface, in_signature='', out_signature='o')
    def activeDocument(self):
        """
        Returns the currently active document
        """
        return self.history[-1]

    @method(iface, in_signature='', out_signature='')
    def back(self):
        """
        Sets the previous document active.
        """
        i = self.documents.index(self.activeDocument()) - 1
        self.documents[i].setActive()

    @method(iface, in_signature='', out_signature='')
    def forward(self):
        """
        Sets the next document active.
        """
        i = self.documents.index(self.activeDocument()) + 1
        i %= len(self.documents)
        self.documents[i].setActive()

    @method(iface, in_signature='', out_signature='b')
    def quit(self):
        return self.mainwin.close()

    def addDocument(self, doc):
        self.documents.append(doc)
        self.history.append(doc)

    def removeDocument(self, doc):
        if doc in self.documents:
            # Was this the active document?
            wasActive = doc is self.activeDocument()
            self.documents.remove(doc)
            self.history.remove(doc)
            if len(self.documents) == 0:
                self.createDocument()
            # If we were the active document, switch to the previous active doc.
            if wasActive:
                self.history[-1].setActive()

    @signal(iface, signature='o')
    def activeChanged(self, doc):
        self.history.remove(doc)
        self.history.append(doc)
        listeners.call(self.activeChanged, doc)
        

class Document(DBusItem):
    """
    A loaded (LilyPond) text document.
    We support lazy document instantiation: only when a view is requested,
    we create the KTextEditor document and view.
    """
    __instance_counter = 0
    iface = DBUS_IFACE_PREFIX + "Document"

    def __init__(self, app, url="", encoding=None):
        Document.__instance_counter += 1
        path = "/Document/%d" % Document.__instance_counter
        DBusItem.__init__(self, app.serviceName, path)

        self.app = app

        self.doc = None         # this is going to hold the KTextEditor doc
        self.view = None        # this is going to hold the KTextEditor view
        self._url = url         # as long as no doc is really loaded, this
                                # is the url
        self._edited = False    # has this document been modified and saved?
        self._cursor = None     # line, col. None = not set.
        self._encoding = encoding or self.app.defaultEncoding # encoding [UTF-8]

        self.app.addDocument(self)
        listeners.add(self.updateCaption, self.updateStatus, self.updateSelection,
            self.close)

    def materialize(self):
        """ Really load the document, create doc and view etc. """
        if self.doc:
            return
        self.doc = self.app.editor.createDocument(self.app.mainwin)
        self.doc.setEncoding(self._encoding)
        self.view = self.doc.createView(self.app.mainwin)

        self.app.mainwin.addDoc(self)

        if self._url:
            self.doc.openUrl(KUrl(self._url))
        elif self.app.defaultHighlightingMode:
            self.doc.setHighlightingMode(self.app.defaultHighlightingMode)

        if self._cursor is not None:
            self.view.setCursorPosition(KTextEditor.Cursor(*self._cursor))

        for s in ("documentUrlChanged(KTextEditor::Document*)",
                  "modifiedChanged(KTextEditor::Document*)"):
            QObject.connect(self.doc, SIGNAL(s), self.updateCaption)
        for s in (
            "cursorPositionChanged(KTextEditor::View*, const KTextEditor::Cursor&)",
            "viewModeChanged(KTextEditor::View*)",
            "informationMessage(KTextEditor::View*)"):
            QObject.connect(self.view, SIGNAL(s), self.updateStatus)
        for s in ("selectionChanged(KTextEditor::View*)",):
            QObject.connect(self.view, SIGNAL(s), self.updateSelection)
    
    def save(self):
        if self.doc:
            self.doc.save()
            
    def openUrl(self, url):
        self._url = url
        if self.doc:
            self.doc.openUrl(KUrl(url))
    
    def updateCaption(self):
        """ Called when name or modifiedstate changes """
        if not self.isModified():
            self._edited = True
        listeners.call(self.updateCaption, self)

    def updateStatus(self):
        """ Called on signals from the View """
        listeners.call(self.updateStatus, self)

    def updateSelection(self):
        """ Called when the selection changes """
        listeners.call(self.updateSelection, self)

    @method(iface, in_signature='s', out_signature='')
    def setEncoding(self, encoding):
        if self.doc:
            self.doc.setEncoding(encoding)
        else:
            self._encoding = encoding

    @method(iface, in_signature='', out_signature='s')
    def url(self):
        """Returns the URL of this document"""
        if self.doc:
            return unicode(self.doc.url().url())
        else:
            return self._url

    @method(iface, in_signature='', out_signature='s')
    def localPath(self):
        if self.doc:
            return unicode(self.doc.url().toLocalFile())
        elif self._url:
            return unicode(KUrl(self._url).toLocalFile())
        else:
            return ""

    @method(iface, in_signature='', out_signature='s')
    def documentName(self):
        if self.doc:
            return self.doc.documentName()
        else:
            return i18n("Untitled")

    def documentIcon(self):
        """Returns None or a suitable icon name for this document"""
        if self.isModified():
            return "document-save"
        elif self.isEdited():
            return "dialog-ok-apply"
        elif self.doc:
            return "dialog-ok"

    @method(iface, in_signature='', out_signature='b')
    def isModified(self):
        """Returns true if the document has unsaved changes."""
        return self.doc and self.doc.isModified()

    @method(iface, in_signature='', out_signature='b')
    def isEdited(self):
        """Returns true is the document has already been modified and saved
        during this process."""
        return self._edited
    
    @method(iface, in_signature='', out_signature='b')
    def isEmpty(self):
        if self.doc:
            return self.doc.isEmpty()
        return False # if not loaded, because we don't know it yet.

    @method(iface, in_signature='', out_signature='b')
    def isActive(self):
        return self.app.activeDocument() is self

    @method(iface, in_signature='', out_signature='')
    def setActive(self):
        """ Make the document the active (shown) document """
        self.materialize()
        self.app.activeChanged(self)

    @method(iface, in_signature='ii', out_signature='')
    def setCursorPosition(self, line, column):
        """Sets the cursor in this document. Lines start at 1, columns at 0."""
        line -= 1
        if self.view:
            self.view.setCursorPosition(KTextEditor.Cursor(line, column))
        else:
            self._cursor = (line, column)

    @method(iface, in_signature='b', out_signature='b')
    def close(self, prompt=True):
        """Closes this document, returning true if closing succeeded."""
        if self.doc:
            if not self.doc.closeUrl(prompt):
                return False # cancel
            listeners.call(self.close, self) # before we are really deleted
            self.app.mainwin.removeDoc(self)
            sip.delete(self.view)
            sip.delete(self.doc)
        else:
            listeners.call(self.close, self) # probably never needed...
        listeners.remove(self.updateCaption, self.updateStatus, self.updateSelection,
            self.close)
        self.remove_from_connection() # remove our exported D-Bus object
        self.app.removeDocument(self)
        return True



