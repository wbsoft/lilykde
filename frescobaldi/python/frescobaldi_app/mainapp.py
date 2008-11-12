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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import KUrl
from PyKDE4.kdeui import KApplication
from PyKDE4.ktexteditor import KTextEditor

from . import DBUS_PREFIX, DBUS_MAIN_PATH, DBUS_IFACE_PREFIX
from .mainwindow import MainWindow


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
         # KApplication needs to be instantiated before any D-Bus stuff
        self.kapp = KApplication()
        DBusItem.__init__(self, DBUS_MAIN_PATH)

        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = DBUS_SERVICE + DBUS_MAIN_PATH
        print "TEXTEDIT_DBUS_PATH=" + DBUS_SERVICE + DBUS_MAIN_PATH # DEBUG

        # We support only one MainWindow.
        self.mainwin = MainWindow()
        self.kapp.setTopWidget(self.mainwin)

        # We manage our own documents.
        self.documents = []

        # Get our beloved editor :-)
        self.editor = KTextEditor.EditorChooser.editor()
        

    def getDocumentByUrl(self, url):
        """ Return the opened document or False. """
        for d in self.documents:
            if d.url() == url:
                return d
        return False
    
    @dbus.service.method(iface, in_signature='s', out_signature='o')
    def openUrl(self, url):
        print url       # DEBUG
        d = self.getDocumentByUrl(url)
        if not d:
            d = Document(self, url)
        return d

    @dbus.service.method(iface, in_signature='', out_signature='', sender_keyword="sender")
    def run(self, sender=None):
        """
        Is called by a remote app after new documents are opened.
        Currently need not to do anything.
        
        If we are the caller ourselves, run the KDE app.
        """
        if sender is None:
            self.kapp.exec_()

    @dbus.service.method(iface, in_signature='s', out_signature='b')
    def isOpen(self, url):
        """
        Returns true is the specified URL is opened by the current application
        """
        return bool(self.getDocumentByUrl(url))
        
    @dbus.service.method(iface, in_signature='', out_signature='')
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
        self._cursor = None     # line, col. None = not set.

        self.app.documents.append(self)
        self.materialize()


    def materialize(self):
        """ Really load the document, create doc and view etc. """
        if self.doc:
            return True
        self.doc = self.app.editor.createDocument(self.mainwin)
        self.view = self.doc.createView(self.mainwin)

        self.show()

        if self._url:
            self.doc.openUrl(KUrl(self._url))
        
        if self._cursor is not None:
            self.view.setCursorPosition(KTextEditor.Cursor(*self._cursor))

    def show(self):
        """ Show the document """
        self.mainwin.guiFactory().addClient(self.view)
        self.mainwin.setCentralWidget(self.view)
        

    @dbus.service.method(iface, in_signature='', out_signature='s')
    def url(self):
        """Returns the URL of this document"""
        if self.doc:
            return unicode(self.doc.url().url())
        else:
            return self._url

    @dbus.service.method(iface, in_signature='ii', out_signature='')
    def setCursorPosition(self, line, column):
        """Sets the cursor in this document. Lines start at 1, columns at 0."""
        print "setCursorPosition called: ", line, column
        column += 1
        if self.view:
            self.view.setCursorPosition(KTextEditor.Cursor(line, column))
        else:
            self._cursor = (line, column)

    @dbus.service.method(iface, in_signature='', out_signature='b')
    def close(self):
        """Closes this document, returning true if closing succeeded."""
        # TODO implement, ask user etc.
        

        self.remove_from_connection()
        self.app.documents.remove(self)
        return True




