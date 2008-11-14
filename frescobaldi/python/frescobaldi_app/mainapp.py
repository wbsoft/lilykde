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

import os, re, sys
import dbus, dbus.service, dbus.mainloop.qt
from dbus.service import method, signal

from PyQt4.QtCore import QObject, SIGNAL
from PyKDE4.kdecore import i18n, KUrl
from PyKDE4.kdeui import KApplication
from PyKDE4.ktexteditor import KTextEditor

from . import DBUS_PREFIX, DBUS_MAIN_PATH, DBUS_IFACE_PREFIX
from .mainwindow import MainWindow, listeners


# Make the Qt mainloop the default one
dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)

DBUS_SERVICE = "%s%d" % (DBUS_PREFIX, os.getpid())

class DBusItem(dbus.service.Object):
    """
    An exported DBus item for our application.
    To be subclassed!
    """
    def __init__(self, path=None):
        if path is None:
            path = '/%s' % self.__class__.__name__
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(DBUS_SERVICE, bus)
        dbus.service.Object.__init__(self, bus_name, path)
    

class MainApp(DBusItem):
    """
    Our main application instance. Also exposes some methods to DBus.
    Instantiated only once.
    """
    iface = DBUS_IFACE_PREFIX + "MainApp"
    
    def __init__(self):
        # listeners to our events
        listeners[self.activeChanged] = []
        # We manage our own documents.
        self.documents = []
        self.history = []       # latest shown documents

        # KApplication needs to be instantiated before any D-Bus stuff
        self.kapp = KApplication()
        DBusItem.__init__(self, DBUS_MAIN_PATH)

        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = DBUS_SERVICE + DBUS_MAIN_PATH
        print "TEXTEDIT_DBUS_PATH=" + DBUS_SERVICE + DBUS_MAIN_PATH # DEBUG

        # We support only one MainWindow.
        self.mainwin = MainWindow(self)
        self.kapp.setTopWidget(self.mainwin)

        # Get our beloved editor :-)
        self.editor = KTextEditor.EditorChooser.editor()


        # restore session etc.

        
    def findDocument(self, url):
        """ Return the opened document or False. """
        for d in self.documents:
            if d.url() == url:
                return d
        return False
    
    @method(iface, in_signature='s', out_signature='o')
    def openUrl(self, url):
        print "openUrl", url       # DEBUG
        # TODO: parse textedit urls here.

        # If there is only one document open and it is empty, nameless and
        # unmodified, do not create a new one.
        if (    len(self.documents) == 1
                and not self.documents[0].isModified()
                and not self.documents[0].url()
                and self.documents[0].isEmpty()):
            self.documents[0].close()
        d = self.findDocument(url)
        if not d:
            print "New document."
            d = Document(self, url)
        else:
            print "Found document:", d.url()
        d.setActive()
        # TODO: if textedit url, set cursor position
        return d

    @method(iface, in_signature='', out_signature='o')
    def new(self):
        print "new" # DEBUG
        d = Document(self)
        d.setActive()
        return d

    @method(iface, in_signature='', out_signature='', sender_keyword="sender")
    def run(self, sender=None):
        """
        Is called by a remote app after new documents are opened.
        Currently need not to do anything.
        
        If we are the caller ourselves, run the KDE app.
        """
        if sender is not None:
            return
        # At the very last, instantiate one empty doc if nothing loaded yet.
        if len(self.documents) == 0:
            Document(self).setActive()
        self.kapp.exec_()

    @method(iface, in_signature='s', out_signature='b')
    def isOpen(self, url):
        """
        Returns true is the specified URL is opened by the current application
        """
        return bool(self.findDocument(url))
        
    @method(iface, in_signature='', out_signature='')
    def quit(self):
        self.kapp.quit()

    @dbus.service.method("org.lilypond.TextEdit", in_signature='s', out_signature='b')
    def openTextEditUrl(self, url):
        """
        To be called by ktexteditservice (part of lilypond-kde4).
        Opens the specified textedit:// URL.
        """
        print "openTextEditUrl called:", url # DEBUG
        return bool(self.openUrl(url))

    def addDocument(self, doc):
        self.documents.append(doc)
        self.history.append(doc)

    def removeDocument(self, doc):
        if doc in self.documents:
            self.documents.remove(doc)
            self.history.remove(doc)
            if len(self.documents) == 0:
                Document(self)

    def activeChanged(self, doc):
        self.history.remove(doc)
        self.history.append(doc)
        for f in listeners[self.activeChanged]:
            f(doc)
        

class Document(DBusItem):
    """
    A loaded LilyPond text document.
    We support lazy document creation: only when a view is requested, we create
    the KTextEditor document and view.
    """
    __instance_counter = 0
    iface = DBUS_IFACE_PREFIX + "Document"

    def __init__(self, app, url=""):
        Document.__instance_counter += 1
        path = "/Document/%d" % Document.__instance_counter
        DBusItem.__init__(self, path)

        self.app = app
        self.mainwin = app.mainwin  # our MainWindow

        self.doc = None         # this is going to hold the KTextEditor doc
        self.view = None        # this is going to hold the KTextEditor view
        self._url = url         # as long as no doc is really loaded, this
                                # is the url
        self._oldname = None    # check if name really changes when url changes
        self._cursor = None     # line, col. None = not set.

        self.checknum()
        self.app.addDocument(self)

    def materialize(self):
        """ Really load the document, create doc and view etc. """
        if self.doc:
            return
        self.doc = self.app.editor.createDocument(self.mainwin)
        self.view = self.doc.createView(self.mainwin)

        self.mainwin.addView(self.view)

        if self._url:
            self.doc.openUrl(KUrl(self._url))
        else:
            self.doc.setHighlightingMode("LilyPond")

        if self._cursor is not None:
            self.view.setCursorPosition(KTextEditor.Cursor(*self._cursor))

        for s in ("documentUrlChanged(KTextEditor::Document*)",
                  "modifiedChanged(KTextEditor::Document*)"):
            QObject.connect(self.doc, SIGNAL(s), self.propertiesChanged)
        
    def propertiesChanged(self, doc):
        """ Called when name or modifiedstate changes """
        self.checknum()
        self.mainwin.updateState(self)

    def checknum(self):
        """
        Counts documents with the same name.
        We don't use the argument which documentUrlChanged(d) supplies.
        """
        name = self.name()
        if name != self._oldname:
            self._oldname = name
            same = [d._num for d in self.app.documents
                           if d is not self and d.name() == name]
            self._num = same and (max(same) + 1) or 1

    @method(iface, in_signature='', out_signature='')
    def setActive(self):
        """ Make the document the active (shown) document """
        self.materialize()
        self.app.activeChanged(self)

    @method(iface, in_signature='', out_signature='s')
    def url(self):
        """Returns the URL of this document"""
        if self.doc:
            return unicode(self.doc.url().url())
        else:
            return self._url

    def name(self):
        if self.url():
            return os.path.basename(self.url())
        else:
            return i18n("Untitled")
                
    @method(iface, in_signature='', out_signature='s')
    def title(self):
        name = self.name()
        if self._num > 1:
            name += " (%d)" % self._num
        return name

    @method(iface, in_signature='', out_signature='b')
    def isModified(self):
        """Returns true if the document has unsaved changes."""
        return self.doc and self.doc.isModified()

    @method(iface, in_signature='', out_signature='b')
    def isEmpty(self):
        if self.doc:
            return self.doc.isEmpty()
        return False # if not loaded, because we don't know it yet.

    @method(iface, in_signature='', out_signature='b')
    def isActive(self):
        return self.app.history[-1] is self

    @method(iface, in_signature='ii', out_signature='')
    def setCursorPosition(self, line, column):
        """Sets the cursor in this document. Lines start at 1, columns at 0."""
        print "setCursorPosition called: ", line, column # DEBUG
        line -= 1
        if self.view:
            self.view.setCursorPosition(KTextEditor.Cursor(line, column))
        else:
            self._cursor = (line, column)

    @method(iface, in_signature='', out_signature='b')
    def close(self):
        """Closes this document, returning true if closing succeeded."""
        # TODO implement, ask user etc.
        

        # Were we the active document?
        wasActive = self.isActive()
        # remove our exported D-Bus object
        self.remove_from_connection()
        self.app.removeDocument(self)
        if self.view:
            self.mainwin.removeView(self.view)
        # If we were the active document, show the last displayed other one.
        if wasActive:
            self.app.history[-1].setActive()
        return True




