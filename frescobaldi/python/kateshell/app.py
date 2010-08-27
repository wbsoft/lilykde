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

import os, re, sip, sys, time, weakref
from contextlib import contextmanager
from functools import wraps

import dbus, dbus.service, dbus.mainloop.qt
from dbus.service import method, signal

from signals import Signal

from PyQt4.QtCore import QDir, QObject, QThread, Qt, SIGNAL
from PyQt4.QtGui import QCursor
from PyKDE4.kdecore import i18n, KConfig, KGlobal, KUrl
from PyKDE4.kdeui import KApplication, KMessageBox, KStandardGuiItem
from PyKDE4.kio import KEncodingFileDialog
from PyKDE4.ktexteditor import KTextEditor

from kateshell import DBUS_IFACE_PREFIX


# Make the Qt mainloop the default one
dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)


# Easily get our global config
def config(group="kateshell"):
    return KGlobal.config().group(group)


def cacheresult(func):
    """Method decorator that caches the result of method calls.
    
    The method is invoked and the return value cached in a dictionary with
    the arguments tuple as key.
    
    When the method is invoked and the arguments tuple is available in the
    cache, the cached value is returned instead of invoking the method again.
    The decorator does not keep references to the arguments and the object the
    method belongs to.
    
    """
    cache = weakref.WeakKeyDictionary()
    @wraps(func)
    def wrapper(obj, *args):
        h = hash(args)
        try:
            return cache[obj][h]
        except KeyError:
            result = cache.setdefault(obj, {})[h] = func(obj, *args)
            return result
    return wrapper


def naturalsort(text):
    """Returns a key for the list.sort() method.
    
    Intended to sort strings in a human way, for e.g. version numbers.
    
    """
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', text))


@contextmanager
def blockSignals(widget):
    """Creates a context for a widget to perform code with blocked signals.
    
    Usage:
    
    with blockSignals(widget) as w:
        ...
    
    """
    block = widget.blockSignals(True)
    try:
        yield widget
    finally:
        widget.blockSignals(block)


class DBusItem(dbus.service.Object):
    """An exported DBus item for our application.
    
    Uses the class name as the DBus object name.
    Intended to be subclassed.
    
    """
    def __init__(self, serviceName, path=None):
        self.serviceName = serviceName
        if path is None:
            path = '/' + self.__class__.__name__
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(self.serviceName, bus)
        dbus.service.Object.__init__(self, bus_name, bytes(path))


class MainApp(DBusItem):
    """Our main application instance.
    
    Also exposes some methods to DBus. Instantiated only once.
    
    Emits four signals to Python others can connect to:
    activeChanged(Document)
    documentCreated(Document)
    documentMaterialized(Document)
    documentClosed(Document)
    
    """
    activeChanged = Signal()
    documentCreated = Signal()
    documentMaterialized = Signal()
    documentClosed = Signal()
    
    iface = DBUS_IFACE_PREFIX + "MainApp"
    defaultEncoding = 'UTF-8'
    defaultMode = None
    fileTypes = []
    
    def __init__(self, servicePrefix):
        # We manage our own documents.
        self.documents = []
        self.history = []       # latest shown documents

        # KApplication needs to be instantiated before any D-Bus stuff
        self.kapp = KApplication()
        
        # Here we can setup config() stuff before MainWindow and its tools 
        # are created.
        config = KGlobal.config().group("") # root group
        self.setupConfiguration(config)
        config.sync()
        
        # Set app-wide style sheet
        QDir.setSearchPaths('css', KGlobal.dirs().findDirs('appdata', 'css/'))
        stylesheet = KGlobal.dirs().findResource('appdata', 'css/style.css')
        if stylesheet:
            self.kapp.setStyleSheet(open(stylesheet).read())
        
        # DBus init
        serviceName = "{0}{1}".format(servicePrefix, os.getpid())
        DBusItem.__init__(self, serviceName, '/MainApp')

        # We support only one MainWindow.
        self.mainwin = self.createMainWindow()
        self.kapp.setTopWidget(self.mainwin)

        # Get our beloved editor :-)
        self.editor = KTextEditor.EditorChooser.editor()
        self.editor.readConfig()

        # restore session etc.
        self._sessionStartedFromCommandLine = False
        
    def setupConfiguration(self, config):
        """Opportunity to manipulate the root group of the global KConfig.
        
        This method is called after KApplication is created but before
        DBus init and Mainwindow creation.
        
        You can implement this method in a subclass; the default implementation
        does nothing.
        
        """
        pass
        
    @cacheresult
    def stateManager(self):
        return StateManager(self)

    def defaultDirectory(self):
        return ''

    def createMainWindow(self):
        import kateshell.mainwindow
        return kateshell.mainwindow.MainWindow(self)

    def createDocument(self, url="", encoding=None):
        return Document(self, url, encoding)
        
    def findDocument(self, url):
        """ Return the opened document or False. """
        if not isinstance(url, KUrl):
            url = KUrl(url)
        # we use string comparison, because sometimes percent encoding
        # issues make the same QUrls look different, esp when dragged
        # from KMail...
        url = url.toString()
        for d in self.documents:
            if d.url().toString() == url:
                return d
        return False
    
    @method(iface, in_signature='ss', out_signature='o')
    def openUrl(self, url, encoding=None):
        if not isinstance(url, KUrl):
            url = KUrl(url)
        # If no encoding given, set default or check if we can remember it
        if not encoding:
            encoding = self.defaultEncoding
            if self.keepMetaInfo() and not url.isEmpty():
                group = self.stateManager().groupForUrl(url)
                if group:
                    encoding = group.readEntry("encoding", "")
        # If there is only one document open and it is empty, nameless and
        # unmodified, use it.
        if (not url.isEmpty()
            and len(self.documents) == 1
            and not self.documents[0].isModified()
            and self.documents[0].url().isEmpty()):
            d = self.documents[0]
            d.openUrl(url, encoding)
        else:
            d = (not url.isEmpty() and self.findDocument(url)
                 or self.createDocument(url, encoding))
        return d

    @method(iface, in_signature='', out_signature='o')
    def new(self):
        return self.createDocument()

    def run(self, sender=None):
        """
        Last minute setup and enter the KDE event loop.
        At the very last, instantiates one empty doc if nothing loaded yet.
        """
        if self.kapp.isSessionRestored():
            self.mainwin.restore(1, False)
        elif (len(self.documents) == 0
              and not self._sessionStartedFromCommandLine):
            # restore named session?
            action = config("preferences").readEntry("default session", "")
            if action == "lastused":
                self.mainwin.sessionManager().restoreLastSession()
            elif action == "custom":
                session = config("preferences").readEntry("custom session", "")
                if session in self.mainwin.sessionManager().names():
                    self.mainwin.sessionManager().switch(session)
        if len(self.documents) == 0:
            self.createDocument().setActive()
        sys.excepthook = self.handleException
        self.mainwin.show()
        self.kapp.exec_()
        KGlobal.config().sync()
       
    @method(iface, in_signature='s', out_signature='b')
    def isOpen(self, url):
        """Returns true if the specified URL is opened."""
        if not isinstance(url, KUrl):
            url = KUrl(url)
        return bool(self.findDocument(url))
        
    @method(iface, in_signature='', out_signature='o')
    def activeDocument(self):
        """Returns the currently active document."""
        return self.history[-1]

    @method(iface, in_signature='', out_signature='')
    def back(self):
        """Sets the previous document active."""
        i = self.documents.index(self.activeDocument()) - 1
        self.documents[i].setActive()

    @method(iface, in_signature='', out_signature='')
    def forward(self):
        """Sets the next document active."""
        i = self.documents.index(self.activeDocument()) + 1
        i %= len(self.documents)
        self.documents[i].setActive()

    @method(iface, in_signature='', out_signature='b')
    def quit(self):
        """Quits the application. Returns True if succeeded."""
        return self.mainwin.close()

    @method(iface, in_signature='', out_signature='')
    def show(self):
        """Raises our mainwindow if minimized."""
        self.mainwin.setWindowState(
            self.mainwin.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
    
    @method(iface, in_signature='s', out_signature='b')
    def startSession(self, session):
        """Switch to the given session.
        
        Use "none" to switch to the empty session.
        If the session does not exist, it is created on the fly.
        Returns True if the switch succeeded.
        
        """
        self._sessionStartedFromCommandLine = True
        return self.mainwin.sessionManager().switch(session)
        
    @method(iface, in_signature='', out_signature='s')
    def currentSession(self):
        """Returns the name of the current session.
        
        Returns "none" if there is no active session.
        
        """
        return self.mainwin.sessionManager().current() or "none"
        
    def addDocument(self, doc):
        """Internal. Called when a new Document is created."""
        self.documents.append(doc)
        self.history.append(doc)
        self.documentCreated(doc)

    def removeDocument(self, doc):
        """Internal. Called when a Document is closed."""
        if doc in self.documents:
            # Was this the active document? Then activate previous active doc.
            if doc is self.activeDocument() and len(self.documents) > 1:
                self.history[-2].setActive()
            self.documents.remove(doc)
            self.history.remove(doc)
            # Create empty document if last closed
            self.documents or self.createDocument().setActive()

    @signal(iface, signature='o')
    def activeDocumentChanged(self, doc):
        self.history.remove(doc)
        self.history.append(doc)
        self.activeChanged(doc) # emit our signal

    @method(iface, in_signature='', out_signature='s')
    def programName(self):
        """Returns the name of the application."""
        return KGlobal.mainComponent().aboutData().programName()
        
    @method(iface, in_signature='', out_signature='s')
    def version(self):
        """Returns the version of our application."""
        return KGlobal.mainComponent().aboutData().version()

    def handleException(self, exctype, excvalue, exctb):
        """Called when a Python exception goes unhandled.
        
        Catches KeyboardInterrupt and shows a dialog for other errors.
        Also writes the traceback to stderr.
        
        """
        from traceback import format_exception
        sys.stderr.write(''.join(format_exception(exctype, excvalue, exctb)))
        
        if exctype != KeyboardInterrupt:
            from kateshell.exception import ExceptionDialog
            ExceptionDialog(self, exctype, excvalue, exctb)

    def keepMetaInfo(self):
        """Returns whether meta information about documents should be kept.
        
        For example the state of the view, cursor position, encoding etc.
        The default implementation returns False, reimplement this to return
        e.g. a user's configured setting.
        
        """
        return False
        
    @contextmanager
    def busyCursor(self, cursor=None):
        """Performs code with a busy cursor set for the application.
        
        The default cursor to use is the Qt.WaitCursor. Usage:
        
        with app.busyCursor():
            ...

        """
        if cursor is None:
            cursor = QCursor(Qt.WaitCursor)
        KApplication.setOverrideCursor(cursor)
        try:
            yield
        finally:
            KApplication.restoreOverrideCursor()


class Document(DBusItem):
    """A loaded text document.
    
    We support lazy document instantiation: only when a view is requested,
    we create the KTextEditor document and view.
    
    We emit these signals:
    urlChanged(doc)
    captionChanged(doc)
    statusChanged(doc)
    selectionChanged(doc)
    saved(doc, bool saveAs)
    closed(doc)
    
    """
    
    __instance_counter = 0
    iface = DBUS_IFACE_PREFIX + "Document"
    
    urlChanged = Signal()
    captionChanged = Signal()
    statusChanged = Signal()
    selectionChanged = Signal()
    saved = Signal()
    closed = Signal()
    
    # In this dict names and default values can be set for properties that are
    # saved by the state manager (if the user wants to keep state info)
    # This dict must be set in the class. The instance copies the values in
    # the metainfo dict. This dict can be manipulated, but only the entries with
    # keys that also appear in this metainfoDefaults dict are saved. The values
    # must be usable in KConfigGroup.readEntry and .writeEntry calls.
    metainfoDefaults = {}

    def __init__(self, app, url="", encoding=None):
        Document.__instance_counter += 1
        path = "/Document/{0}".format(Document.__instance_counter)
        DBusItem.__init__(self, app.serviceName, path)

        if not isinstance(url, KUrl):
            url = KUrl(url)

        self.app = app
        self.metainfo = self.metainfoDefaults.copy()
        self.doc = None         # this is going to hold the KTextEditor doc
        self.view = None        # this is going to hold the KTextEditor view
        self._url = url         # as long as no doc is really loaded, this
                                # is the url
        self._edited = False    # has this document been modified and saved?
        self._cursor = None     # line, col. None = not set.
        self._encoding = encoding or self.app.defaultEncoding # encoding [UTF-8]
        self._cursorTranslator = None   # for translating cursor positions
        
        self.app.addDocument(self)
        
    def materialize(self):
        """Really load the document, create doc and view etc."""
        if self.doc:
            return
        self.doc = self.app.editor.createDocument(self.app.mainwin)
        self.doc.setEncoding(self._encoding)
        self.view = self.doc.createView(self.app.mainwin)
        if not self._url.isEmpty():
            self.doc.openUrl(self._url)
        elif self.app.defaultMode:
            self.doc.setMode(self.app.defaultMode)

        # init the cursor translations (so that point and click keeps working
        # while the document changes)
        self.resetCursorTranslations()
        
        if self._cursor is not None:
            self.setCursorPosition(*self._cursor)
        
        QObject.connect(self.doc, SIGNAL("documentSavedOrUploaded(KTextEditor::Document*, bool)"), self.slotDocumentSavedOrUploaded)
        QObject.connect(self.doc, SIGNAL("documentUrlChanged(KTextEditor::Document*)"), self.slotDocumentUrlChanged)
        QObject.connect(self.doc, SIGNAL("completed()"), self.slotCompleted)
        QObject.connect(self.doc, SIGNAL("modifiedChanged(KTextEditor::Document*)"), self.slotModifiedChanged)
        QObject.connect(self.view, SIGNAL("cursorPositionChanged(KTextEditor::View*, const KTextEditor::Cursor&)"), self.slotViewStatusChanged)
        QObject.connect(self.view, SIGNAL("viewModeChanged(KTextEditor::View*)"), self.slotViewStatusChanged)
        QObject.connect(self.view, SIGNAL("informationMessage(KTextEditor::View*)"), self.slotViewStatusChanged)
        QObject.connect(self.view, SIGNAL("selectionChanged(KTextEditor::View*)"), self.slotSelectionChanged)
        
        # Allow for dropping urls on the view
        QObject.connect(self.view, SIGNAL("dropEventPass(QDropEvent *)"), self.app.mainwin.dropEvent)
        
        # delete some actions from the view before plugging in GUI
        # trick found in kateviewmanager.cpp
        for name in "file_save", "file_save_as":
            action = self.view.actionCollection().action(name)
            if action:
                sip.delete(action)
        
        # set default context menu
        self.view.setContextMenu(self.contextMenu())
        # read state information (view settings etc.)
        if self.app.keepMetaInfo():
            self.app.stateManager().loadState(self)
        # Let the world know ...
        self.app.documentMaterialized(self)
        self.viewCreated()
        
    # some slots, to avoid lambdas for Qt signals, not to be inherited
    def slotDocumentSavedOrUploaded(self, doc, saveAs):
        self.saved(self, saveAs)
        
    def slotDocumentUrlChanged(self):
        self.urlChanged(self)
        self.captionChanged(self)
        
    def slotCompleted(self):
        self.captionChanged(self)
        
    def slotModifiedChanged(self):
        if not self.isModified():
            self._edited = True
        self.captionChanged(self)
        
    def slotViewStatusChanged(self):
        self.statusChanged(self)
        
    def slotSelectionChanged(self):
        self.selectionChanged(self)
    
    def contextMenu(self):
        """Override this to set your own context menu."""
        return self.view.defaultContextMenu()
    
    def viewCreated(self):
        """Called when the view for this document is created.
        
        Override this in subclasses to do things after the KTextEditor.View
        for this document has materialized.
        """
        pass 
    
    def openUrl(self, url, encoding):
        """Internal. Opens a different url and re-init some stuff.
        
        (Only call this on a Document that has already materialized.)
        
        """
        self.materialize()
        self.setEncoding(encoding)
        if not self.doc.openUrl(url):
            self.slotDocumentUrlChanged() # otherwise signal is not emitted
        if self.app.keepMetaInfo():
            self.app.stateManager().loadState(self)
        self.resetCursorTranslations()
        
    @method(iface, in_signature='', out_signature='b')
    def save(self):
        """Saves the document, asking for a file name if necessary.
        
        Returns True if saving succeeded, otherwise False.
        
        """
        if self.doc:
            if self.url().isEmpty():
                return self.saveAs()
            else:
                return self.doc.save()
        return True
        
    @method(iface, in_signature='', out_signature='b')
    def saveAs(self):
        """Saves the document, always asking for a file name.
        
        Returns True if saving succeeded, otherwise False.
        
        """
        if self.doc:
            dlg = KEncodingFileDialog(
                self.app.mainwin.sessionManager().basedir() or
                self.app.defaultDirectory(),
                self.doc.encoding(),
                '\n'.join(self.app.fileTypes + ["*|" + i18n("All Files")]),
                i18n("Save File"),
                KEncodingFileDialog.Saving,
                self.app.mainwin)
            dlg.setSelection(self.url().url())
            dlg.setConfirmOverwrite(True)
            if not dlg.exec_():
                return False # Cancelled
            self.doc.setEncoding(dlg.selectedEncoding())
            return self.doc.saveAs(dlg.selectedUrl())
        return True
            
    @method(iface, in_signature='s', out_signature='')
    def setEncoding(self, encoding):
        """Sets the encoding for this document."""
        if self.doc:
            self.doc.setEncoding(encoding)
        else:
            self._encoding = encoding

    @method(iface, in_signature='', out_signature='s')
    def encoding(self):
        """Returns the encoding for this document."""
        if self.doc:
            return self.doc.encoding()
        else:
            return self._encoding
            
    def url(self):
        """Returns the KUrl of this document."""
        if self.doc:
            return self.doc.url()
        else:
            return self._url
            
    @method(iface, in_signature='', out_signature='s')
    def prettyUrl(self):
        """Returns a printable, pretty URL for this document."""
        return self.url().pathOrUrl()
        
    @method(iface, in_signature='', out_signature='s')
    def localPath(self):
        """Returns the local file path for the document."""
        return self.url().toLocalFile() or ""

    @method(iface, in_signature='', out_signature='s')
    def documentName(self):
        """Returns a printable name for this document.
        
        Normally this is the filename or "Untitled".
        
        """
        if self.doc:
            return self.doc.documentName() or ""
        else:
            return self.url().fileName() or i18n("Untitled")

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
        """Returns true if the document has already been modified and saved."""
        return self._edited
    
    @method(iface, in_signature='', out_signature='b')
    def isEmpty(self):
        """Returns True if the document is empty.
        
        Returns False if the document has not materialized yet.
        
        """
        if self.doc:
            return self.doc.isEmpty()
        return False # if not loaded, because we don't know it yet.

    @method(iface, in_signature='', out_signature='b')
    def isActive(self):
        """Returns True if this document is the active one."""
        return bool(self.doc) and self.app.activeDocument() is self

    @method(iface, in_signature='', out_signature='')
    def setActive(self):
        """Makes the document the active (shown) document."""
        if not self.isActive():
            self.materialize()
            self.app.activeDocumentChanged(self)
        self.view.setFocus()
        self.view.activateWindow()

    @method(iface, in_signature='iib', out_signature='')
    def setCursorPosition(self, line, column, translate=True):
        """Sets the cursor in this document.
        
        Lines start at 1, columns at 0.
        A TAB character counts as (max, depending on column) 8 characters.
        
        If translate is True, the cursor position is translated from the state
        saved by the current CursorTranslator to the current state of the
        document. This way, external references to positions in the document
        remain working, even if the document is edited, until the
        CursorTranslator is updated (which typically happens if a new build is
        started).
        
        """
        if self.view:
            line -= 1 # katepart numbers lines from zero
            if translate:
                cursor = self._cursorTranslator.cursor(line, column)
            else:
                column = resolvetabs_text(column, self.line(line))
                cursor = KTextEditor.Cursor(line, column)
            self.view.setCursorPosition(cursor)
        else:
            self._cursor = (line, column)

    @method(iface, in_signature='', out_signature='s')
    def text(self):
        """Returns the full text of the document."""
        return self.doc and self.doc.text() or ""
    
    @method(iface, in_signature='s', out_signature='b')
    def setText(self, text):
        """Set the given text as new document content."""
        self.materialize()
        if self.doc.setText(text):
            self.resetCursorTranslations()
            return True
        return False
        
    @method(iface, in_signature='', out_signature='i')
    def lines(self):
        """Returns the number of lines."""
        return self.doc and self.doc.lines() or 0
        
    def textLines(self):
        """Returns the full document text as a list of lines."""
        if self.doc:
            return [line or ""
                for line in self.doc.textLines(self.doc.documentRange())]
        else:
            return []
    
    @method(iface, in_signature='b', out_signature='b')
    def close(self, prompt=True):
        """Closes this document, returning True if closing succeeded."""
        if self.doc:
            if prompt and not self.queryClose():
                return False
            if not self.doc.closeUrl(False):
                return False # closing did not succeed, but that'd be abnormal
            if self.app.keepMetaInfo():
                self.app.stateManager().saveState(self)
        self.closed(self) # before we are really deleted
        self.aboutToClose()
        self.app.documentClosed(self)
        self._cursorTranslator = None
        self.view and sip.delete(self.view)
        self.doc and sip.delete(self.doc)
        self.app.removeDocument(self)
        self.remove_from_connection() # remove our exported D-Bus object
        return True

    def queryClose(self):
        """Ask user if document modified and saves if desired."""
        # Many stuff copied from KatePart
        if not self.doc or not self.isModified():
            return True
        res = KMessageBox.warningYesNoCancel(self.app.mainwin, i18n(
            "The document \"%1\" has been modified.\n"
            "Do you want to save your changes or discard them?",
            self.documentName()), i18n("Close Document"),
            KStandardGuiItem.save(), KStandardGuiItem.discard())
        if res == KMessageBox.Yes:
            self.save()
        elif res == KMessageBox.No:
            return True
        else: # cancel
            return False

    def aboutToClose(self):
        """Called just before a document is really closed.
        
        Implement this if you want to save some last minute state, etc.
        After calling this the view and document (if they have materialized)
        will be deleted.
        
        This method will also be called if the document never materialized.
        So check if self.view really is a View before you do something with it.
        
        """
        pass
    
    def viewActions(self):
        """Iterate over the View actions for which the state could be saved."""
        if self.view:
            for name in (
                "view_dynamic_word_wrap",
                "view_word_wrap_marker", "view_border", "view_line_numbers",
                "view_scrollbar_marks", "view_folding_markers"):
                action = self.view.actionCollection().action(name)
                if action:
                    yield name, action

    def readConfig(self, group):
        """This can be called by a StateManager after the document materialized.
        
        You can read stuff from the KConfigGroup group, to adjust settings for
        the loaded document and its view.
        
        """
        # load custom properties
        for name, default in self.metainfoDefaults.items():
            self.metainfo[name] = group.readEntry(name, default)
        # restore some options from the view menu
        for name, action in self.viewActions():
            if group.hasKey(name):
                value = group.readEntry(name, False)
                if value != action.isChecked():
                    action.trigger()
        # cursor position
        line = group.readEntry("line", 0)
        column = group.readEntry("column", 0)
        if line < self.doc.lines():
            self.view.setCursorPosition(KTextEditor.Cursor(line, column))
        # bookmarks
        markiface = self.doc.markInterface()
        if markiface:
            marks = group.readEntry("bookmarks", "")
            if re.match(r"\d+:\d+(,\d+:\d+)*$", marks):
                for m in marks.split(','):
                    line, mark = map(int, m.split(':'))
                    if line < self.doc.lines():
                        markiface.addMark(line, mark)

    def writeConfig(self, group):
        """This can be called by a StateManager, normally just before closing.
        
        You can write stuff to the KConfigGroup group, to save settings for the
        document and its view.
        
        """
        # save custom properties
        for name, default in self.metainfoDefaults.items():
            if self.metainfo[name] != default:
                group.writeEntry(name, self.metainfo[name])
            else:
                group.deleteEntry(name)
        # save some options in the view menu
        for name, action in self.viewActions():
            group.writeEntry(name, action.isChecked())
        # cursor position
        cursor = self.view.cursorPosition()
        group.writeEntry("line", cursor.line())
        group.writeEntry("column", cursor.column())
        # bookmarks
        # markInterface().marks() crashes so we use mark() instead...
        markiface = self.doc.markInterface()
        if markiface:
            marks = []
            for line in range(self.doc.lines()):
                m = markiface.mark(line)
                if m:
                    marks.append("{0}:{1}".format(line, m))
            group.writeEntry("bookmarks", ','.join(marks))
        # also save the encoding
        group.writeEntry("encoding", self.encoding())

    def line(self, lineNumber = None):
        """Returns the text of the given or current line."""
        if self.doc:
            if lineNumber is None:
                lineNumber = self.view.cursorPosition().line()
            return self.doc.line(lineNumber) or ""
    
    def textToCursor(self, line=None, column=None):
        """Returns the text from the start of the document to the given
        cursor position.
        
        If line and column are None, the current cursor position is used.
        If column is None, line is expected to be a KTextEditor.Cursor object.
        
        """
        if self.view:
            if line is None:
                line = self.view.cursorPosition()
            if column is None:
                column = line.column()
                line = line.line()
            return self.doc.text(KTextEditor.Range(0, 0, line, column)) or ""

    def selectionText(self):
        """Returns the selected text or an empty string."""
        if self.view and self.view.selection():
            return self.view.selectionText() or ""
    
    def selectionOrDocument(self):
        """Returns a tuple(text, start).
        
        If there is a selection, start is the position in the text the selection
        starts, and text is the document text from the (0, 0) to the end of the
        selection. If there is no selection, the whole document text is returned
        and start=0.
        
        """
        docRange = self.doc.documentRange()
        selRange = self.view.selectionRange()
        if self.view.selection() and selRange.start().position() != selRange.end().position():
            text = self.textToCursor(selRange.end())
            line, column = selRange.start().position()
            return text, cursorToPosition(line, column, text)
        return self.text(), 0
        
    def replaceSelectionWith(self, text, keepSelection=True):
        """Convenience method. Replaces the selection (if any) with text.
        
        If keepSelection is true, select the newly inserted text again.
        
        """
        v, d = self.view, self.doc
        selRange = v.selectionRange() # copy othw. crash in KDE 4.3 /PyQt 4.5.x.
        cur = v.selection() and selRange.start() or v.cursorPosition()
        line, col = cur.line(), cur.column()
        if v.selection():
            d.replaceText(selRange, text)
        else:
            v.insertText(text)
        if keepSelection:
            lines = text.count('\n')
            endline = line + lines
            if lines:
                endcol = len(text) - text.rfind('\n') - 1
            else:
                endcol = col + len(text)
            v.setSelection(KTextEditor.Range(line, col, endline, endcol))
        else:
            v.removeSelection()
    
    @contextmanager
    def editContext(self):
        """Context to perform operations on the document in one Undo-block.
        
        Usage:
        
        with doc.editContext():
            ...
        
        """
        self.doc.startEditing()
        try:
            yield
        finally:
            self.doc.endEditing()
        
    def resetCursorTranslations(self):
        """Clears the cursor translations that keep Point and Click
        working while the document changes.
        
        Call this when a build has succeeded and cursor positions produced
        by build errors or build output coincide with the current document text.
        
        """
        if self.doc:
            self._cursorTranslator = CursorTranslator(self)
    
    def kateModeVariables(self):
        """Returns a dict with katemoderc variables.
        
        The current mode is used. Returns None if there is no document mode
        active and there is no application default mode.
        
        """
        mode = self.doc and self.doc.mode() or self.app.defaultMode
        if mode:
            c = KConfig("katemoderc", KConfig.NoGlobals)
            v = c.group(mode).readEntry("Variables", "")
            return dict(re.findall(r"([a-z]+(?:-[a-z]+)*)\s+([^;]*)", v))
    
    #BUG: Reimplemented below as the variableInterface does not seem to work...
    #def kateVariable(self, varName):
        #"""
        #Returns the value of the kate variable varName, if set in the document
        #or in the modeline for the current document mode.
        #"""
        #if self.doc:
            #iface = self.doc.variableInterface()
            #if iface:
                #v = iface.variable(varName)
                #if v:
                    #return v
        #d = self.kateModeVariables()
        #if d:
            #return d.get(varName)
    
    def kateVariable(self, varName):
        """Returns the value of the kate variable varName.
        
        Looks in the document and in the modeline for the current document mode.
        Returns None if the variable is not set.
        """
        lines = self.textLines()
        del lines[10:-10] # only look at the first and last ten lines.
        for line in lines:
            if 'kate:' in line:
                m = re.search(r"[:;]\s*\b{0}\s+([^;]+)".format(varName), line)
                if m:
                    return m.group(1)
        d = self.kateModeVariables()
        if d:
            return d.get(varName)
        
    def tabWidth(self):
        """Returns the width of the tab character in this document."""
        v = self.kateVariable("tab-width")
        if v and v.isdigit():
            return int(v)
        group = KGlobal.config().group("Kate Document Defaults")
        return group.readEntry("Tab Width", 8)
        
    def indentationWidth(self):
        """Returns the indent-width for the current document."""
        v = self.kateVariable("indent-width")
        if v and v.isdigit():
            return int(v)
        group = KGlobal.config().group("Kate Document Defaults")
        return group.readEntry("Indentation Width", 2)
    
    def indentationSpaces(self):
        """Returns True if indent uses spaces, otherwise False."""
        v = self.kateVariable("space-indent") or self.kateVariable("replace-tabs")
        if v:
            return v in ('on', '1', 'yes', 'y', 'true')
        group = config("Kate Document Defaults")
        return bool(group.readEntry('Basic Config Flags', 0) & 0x2000000)

    
class StateManager(object):
    """Manages state and meta-info for documents.
    
    Asks Documents to save information like bookmarks and cursor position, etc.
    The information is saved in the 'metainfos' config file in the applications
    data directory.
    
    """
    def __init__(self, app):
        self.app = app
        self.metainfos = KConfig("metainfos", KConfig.NoGlobals, "appdata")
        
    def groupForUrl(self, url, create=False):
        """Returns a KConfigGroup for the given KUrl.
        
        Returns None if the group does not exist and create==False.
        
        """
        if not url.isEmpty():
            encodedurl = url.prettyUrl()
            if create or self.metainfos.hasGroup(encodedurl):
                return self.metainfos.group(encodedurl.encode('utf-8'))
            
    def loadState(self, doc):
        """Asks the Document to read its state from our config."""
        group = self.groupForUrl(doc.url())
        if group:
            last = group.readEntry("time", 0.0)
            # when it is a local file, only load the state when the
            # file was not modified later
            if not doc.localPath() or (
                    os.path.exists(doc.localPath()) and
                    os.path.getmtime(doc.localPath()) <= last):
                doc.readConfig(group)
            
    def saveState(self, doc):
        """Asks the Document to save its state to our config."""
        if doc.view and not doc.url().isEmpty():
            group = self.groupForUrl(doc.url(), True)
            group.writeEntry("time", time.time())
            doc.writeConfig(group)
            group.sync()
            
    def cleanup(self):
        """Purge entries that are not used for more than a month."""
        for g in self.metainfos.groupList():
            group = self.metainfos.group(g.encode('utf-8'))
            last = group.readEntry("time", 0.0)
            if (time.time() - last) / 86400 > 31:
                group.deleteGroup()
        self.metainfos.sync()


class CursorTranslator(object):
    """Translates cursor positions after a document is edited.
    
    This object makes a kind of snapshot of a document and makes it
    possible to translate cursor positions in that snapshot to the correct
    place in the current document.
    
    """
    def __init__(self, doc):
        """ doc should be a kateshell.app.Document instance """
        self.savedTabs = map(tabindices, doc.textLines())
        self.iface = doc.doc.smartInterface()
        if self.iface:
            self.revision = self.iface.currentRevision()
            
    def __del__(self):
        """ Remove our grip on the document. """
        if self.iface:
            self.iface.releaseRevision(self.revision)
        
    def cursor(self, line, column):
        """Translates a cursor position to the current document.
        
        Also resolves tabs (i.e. the column parameter is the virtual position).
        Returns a KTextEditor.Cursor instance.
        
        """
        if line < len(self.savedTabs) and self.savedTabs[line]:
            column = resolvetabs_indices(column, self.savedTabs[line])
        cursor = KTextEditor.Cursor(line, column)
        if self.iface:
            # Just because KDE 4.5 does a qFatal if useRevision is called in the
            # main thread, and the Python KDE4 bindings not yet provide the new
            # MovingInterface stuff, we need to create a background thread just
            # to translate cursors from a certain document revision.
            @anonymousThread
            def translateCursor(cursor):
                self.iface.smartMutex().lock()
                self.iface.useRevision(self.revision)
                cursor = self.iface.translateFromRevision(cursor,
                    KTextEditor.SmartCursor.MoveOnInsert)
                self.iface.clearRevision()
                self.iface.smartMutex().unlock()
                return cursor
            cursor = translateCursor(cursor)
        return cursor


class _AnonymousThread(QThread):
    """Runs a function in an anonymous QThread.
    
    Exceptions are re-raised in the main thread.
    
    """
    def __init__(self, func, args, kwargs):
        super(_AnonymousThread, self).__init__()
        self.func = lambda: func(*args, **kwargs)
        self._result = None
        self._exc_info = None
        self.start()
        self.wait()
    
    def run(self):
        try:
            self._result = self.func()
        except:
            self._exc_info = sys.exc_info()
            sys.exc_clear()
    
    def result(self):
        """Returns a tuple (result, exception)."""
        return self._result, self._exc_info


def anonymousThread(func):
    """Returns a wrapper for a func to run it in an anonymous QThread.
    
    When called, waits for the function to complete and returns its result.
    
    """
    def wrapper(*args, **kwargs):
        result, exc_info = _AnonymousThread(func, args, kwargs).result()
        if exc_info:
            raise exc_info[1], None, exc_info[2]
        return result
    return wrapper


def tabindices(text):
    """Returns a list of positions in text at which a tab character is found.
    
    If no tab character is found, returns None.
    
    """
    result = []
    tab = text.find('\t')
    while tab != -1:
        result.append(tab)
        tab = text.find('\t', tab + 1)
    return result or None

def resolvetabs_text(column, text):
    """Translates virtual column to the character column in a text string.
    
    Assumes tab stops are on 8 character positions.
    Parses text for tab stops and resolves column (a virtual position)
    to point to the correct character position in the text.
    
    """
    return resolvetabs_indices(column, tabindices(text))

def resolvetabs_indices(column, indices):
    """Translates virtual column to the character index in a text.

    Assumes tab stops are on 8 character positions.
    indices should be a list of tabstops (see the tabindices function).
    
    """
    if not indices or column < indices[0]:
        return column
    charcol, realcol = 0, 0
    # TODO: this loop can probably be optimized
    while True:
        if charcol in indices:
            realcol = realcol + 8 & -8
        else:
            realcol += 1
        if realcol > column:
            return charcol
        charcol += 1
        
def cursorToPosition(line, column, text):
    """Returns the character position in text of a cursor with line and column.
    
    Line and column both start with 0.
    Returns -1 if the position falls outside the text.
    
    """
    pos = 0
    for i in range(line):
        pos = text.find('\n', pos) + 1
        if not pos:
            return -1
    new = text.find('\n', pos)
    if new == -1:
        new = len(text)
    pos += column
    if pos > new:
        return -1
    return pos

