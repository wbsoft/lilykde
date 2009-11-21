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

import os, re, sip, sys, time, weakref, dbus, dbus.service, dbus.mainloop.qt
from dbus.service import method, signal

from signals import Signal

from PyQt4.QtCore import QObject, Qt, QVariant, SIGNAL
from PyKDE4.kdecore import i18n, KConfig, KGlobal, KUrl
from PyKDE4.kdeui import (
    KActionCollection, KApplication, KGuiItem, KMessageBox, KStandardGuiItem)
from PyKDE4.kio import KEncodingFileDialog
from PyKDE4.ktexteditor import KTextEditor

from kateshell import DBUS_IFACE_PREFIX
from kateshell.mainwindow import MainWindow


# Make the Qt mainloop the default one
dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)


def lazymethod(func):
    """
    A decorator that only performs the method call the first time,
    caches the return value, and returns that next time.
    The argments tuple should be hashable.
    """
    cache = weakref.WeakKeyDictionary()
    def loader(obj, *args):
        if args not in cache.setdefault(obj, {}):
            cache[obj][args] = func(obj, *args)
        return cache[obj][args]
    return loader


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
    
    Emits three signals to Python others can connect to:
    activeChanged(Document)
    documentCreated(Document)
    documentMaterialized(Document)
    documentClosed(Document)
    """
    iface = DBUS_IFACE_PREFIX + "MainApp"
    defaultEncoding = 'UTF-8'
    defaultMode = None
    fileTypes = []
    
    def __init__(self, servicePrefix):
        # others can connect to our events
        self.activeChanged = Signal()
        self.documentCreated = Signal()
        self.documentMaterialized = Signal()
        self.documentClosed = Signal()

        # make it easy to connect more error handlers
        self.excepthook = Signal()
        self.excepthook.connect(sys.excepthook)
        sys.excepthook = self.excepthook
        
        # We manage our own documents.
        self.documents = []
        self.history = []       # latest shown documents

        # KApplication needs to be instantiated before any D-Bus stuff
        self.kapp = KApplication()
        
        # DBus init
        serviceName = "%s%d" % (servicePrefix, os.getpid())
        DBusItem.__init__(self, serviceName, '/MainApp')

        # We support only one MainWindow.
        self.mainwin = self.createMainWindow()
        self.kapp.setTopWidget(self.mainwin)

        # Get our beloved editor :-)
        self.editor = KTextEditor.EditorChooser.editor()
        self.editor.readConfig()

        # restore session etc.
        
    @lazymethod
    def stateManager(self):
        return StateManager(self)

    def defaultDirectory(self):
        return ''

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
        if not isinstance(url, KUrl):
            url = KUrl(url)
        # If no encoding given, set default or check if we can remember it
        if not encoding:
            encoding = self.defaultEncoding
            if not url.isEmpty():
                if self.keepMetaInfo():
                    group = self.stateManager().groupForUrl(url)
                    if group:
                        encoding = group.readEntry("encoding", QVariant('')).toString()
        # If there is only one document open and it is empty, nameless and
        # unmodified, close it.
        close0 = (not url.isEmpty() and len(self.documents) == 1
            and not self.documents[0].isModified()
            and self.documents[0].url().isEmpty()
            and self.documents[0].isEmpty())
        d = (not url.isEmpty() and self.findDocument(url)
            or self.createDocument(url, encoding))
        if close0:
            self.documents[0].close()
        return d

    @method(iface, in_signature='', out_signature='o')
    def new(self):
        return self.createDocument()

    def run(self, sender=None):
        """
        Last minute setup and enter the KDE event loop.
        At the very last, instantiates one empty doc if nothing loaded yet.
        """
        if len(self.documents) == 0:
            self.createDocument().setActive()
        self.excepthook.connect(self.showException)
        self.kapp.exec_()
        KGlobal.config().sync()
       
    @method(iface, in_signature='s', out_signature='b')
    def isOpen(self, url):
        """
        Returns true is the specified URL is opened by the current application
        """
        if not isinstance(url, KUrl):
            url = KUrl(url)
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

    @method(iface, in_signature='', out_signature='')
    def show(self):
        """ Raises our mainwindow if minimized """
        self.mainwin.setWindowState(
            self.mainwin.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
    
    def addDocument(self, doc):
        self.documents.append(doc)
        self.history.append(doc)
        self.documentCreated(doc)

    def removeDocument(self, doc):
        if doc in self.documents:
            # Was this the active document? Then activate previous active doc.
            if doc is self.activeDocument() and len(self.documents) > 1:
                self.history[-2].setActive()
            self.documents.remove(doc)
            self.history.remove(doc)
            self.documentClosed(doc)
            # Create empty document if last closed
            self.documents or self.createDocument().setActive()

    @signal(iface, signature='o')
    def activeDocumentChanged(self, doc):
        self.history.remove(doc)
        self.history.append(doc)
        self.activeChanged(doc) # emit our signal

    @method(iface, in_signature='', out_signature='s')
    def programName(self):
        """
        Returns the name of the application
        """
        return unicode(KGlobal.mainComponent().aboutData().programName())
        
    @method(iface, in_signature='', out_signature='s')
    def version(self):
        """
        Returns the version of our app.
        """
        return unicode(KGlobal.mainComponent().aboutData().version())

    def showException(self, exctype, excvalue, exctb):
        """
        Called when a Python exception goes unhandled
        """
        import kateshell.exception
        kateshell.exception.showException(self, exctype, excvalue, exctb)

    def keepMetaInfo(self):
        """
        Returns whether meta information about documents should be kept
        (e.g. state of view, cursor position, encoding etc.)
        
        The default is to return False, reimplement this to return e.g.
        a user's configured setting.
        """
        return False


class Document(DBusItem):
    """
    A loaded (LilyPond) text document.
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

    def __init__(self, app, url="", encoding=None):
        Document.__instance_counter += 1
        path = "/Document/%d" % Document.__instance_counter
        DBusItem.__init__(self, app.serviceName, path)

        if not isinstance(url, KUrl):
            url = KUrl(url)

        self.app = app

        self.doc = None         # this is going to hold the KTextEditor doc
        self.view = None        # this is going to hold the KTextEditor view
        self._url = url         # as long as no doc is really loaded, this
                                # is the url
        self._edited = False    # has this document been modified and saved?
        self._cursor = None     # line, col. None = not set.
        self._encoding = encoding or self.app.defaultEncoding # encoding [UTF-8]
        self._cursorTranslator = None   # for translating cursor positions
        
        self.urlChanged = Signal()
        self.captionChanged = Signal()
        self.statusChanged = Signal()
        self.selectionChanged = Signal()
        self.saved = Signal()
        self.closed = Signal()
        
        self.app.addDocument(self)
        
    def materialize(self):
        """ Really load the document, create doc and view etc. """
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
        
        QObject.connect(self.doc,
            SIGNAL("documentSavedOrUploaded(KTextEditor::Document*, bool)"),
            self.slotDocumentSavedOrUploaded)
        QObject.connect(self.doc,
            SIGNAL("documentUrlChanged(KTextEditor::Document*)"),
            self.slotDocumentUrlChanged)
        QObject.connect(self.doc,
            SIGNAL("completed()"),
            self.slotCompleted)
        QObject.connect(self.doc,
            SIGNAL("modifiedChanged(KTextEditor::Document*)"),
            self.slotModifiedChanged)
        for s in (
            "cursorPositionChanged(KTextEditor::View*, const KTextEditor::Cursor&)",
            "viewModeChanged(KTextEditor::View*)",
            "informationMessage(KTextEditor::View*)"):
            QObject.connect(self.view, SIGNAL(s), self.slotViewStatusChanged)
        for s in ("selectionChanged(KTextEditor::View*)",):
            QObject.connect(self.view, SIGNAL(s), self.slotSelectionChanged)
        
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
        """
        Override this to set your own context menu.
        """
        return self.view.defaultContextMenu()
    
    def viewCreated(self):
        """
        Override this in subclasses to do things after the KTextEditor.View
        for this document has materialized.
        """
        pass 
    
    @method(iface, in_signature='', out_signature='b')
    def save(self):
        if self.doc:
            if self.url().isEmpty():
                return self.saveAs()
            else:
                return self.doc.save()
        return True
        
    @method(iface, in_signature='', out_signature='b')
    def saveAs(self):
        if self.doc:
            dlg = KEncodingFileDialog(
                self.app.defaultDirectory(),
                self.doc.encoding(),
                '\n'.join(self.app.fileTypes + ["*|%s" % i18n("All Files")]),
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
            
    def openUrl(self, url):
        if not isinstance(url, KUrl):
            url = KUrl(url)
        self._url = url
        if self.doc:
            self.doc.openUrl(url)
    
    @method(iface, in_signature='s', out_signature='')
    def setEncoding(self, encoding):
        if self.doc:
            self.doc.setEncoding(encoding)
        else:
            self._encoding = encoding

    @method(iface, in_signature='', out_signature='s')
    def encoding(self):
        if self.doc:
            return str(self.doc.encoding())
        else:
            return self._encoding
            
    def url(self):
        """ Returns the KUrl of this document """
        if self.doc:
            return self.doc.url()
        else:
            return self._url
            
    @method(iface, in_signature='', out_signature='s')
    def prettyUrl(self):
        """Returns a printable, pretty URL for this document."""
        return unicode(self.url().pathOrUrl())
        
    @method(iface, in_signature='', out_signature='s')
    def localPath(self):
        return unicode(self.url().toLocalFile())

    @method(iface, in_signature='', out_signature='s')
    def documentName(self):
        if self.doc:
            return self.doc.documentName()
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
        return bool(self.doc) and self.app.activeDocument() is self

    @method(iface, in_signature='', out_signature='')
    def setActive(self):
        """ Make the document the active (shown) document """
        if not self.isActive():
            self.materialize()
            self.app.activeDocumentChanged(self)
        self.view.setFocus()

    @method(iface, in_signature='iib', out_signature='')
    def setCursorPosition(self, line, column, translate=True):
        """
        Sets the cursor in this document. Lines start at 1, columns at 0.
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
        """
        Returns the document text.
        """
        if self.doc:
            return unicode(self.doc.text())
        else:
            return ''
    
    @method(iface, in_signature='s', out_signature='b')
    def setText(self, text):
        """
        Set the given text as new document content.
        """
        self.materialize()
        if self.doc.setText(text):
            self.resetCursorTranslations()
            return True
        return False
        
    @method(iface, in_signature='', out_signature='i')
    def lines(self):
        """
        Returns the number of lines.
        """
        return self.doc and self.doc.lines() or 0
        
    def textLines(self):
        """
        Returns the full document text as a list of lines.
        """
        if self.doc:
            return map(unicode, self.doc.textLines(self.doc.documentRange()))
        else:
            return []
    
    @method(iface, in_signature='b', out_signature='b')
    def close(self, prompt=True):
        """Closes this document, returning true if closing succeeded."""
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
        """ Ask user if document modified and saves if desired. """
        # Many stuff copied from KatePart
        if not self.doc or not self.isModified():
            return True
        res = KMessageBox.warningYesNoCancel(self.app.mainwin, i18n(
            "The document \"%1\" has been modified.\n"
            "Do you want to save your changes or discard them?",
            self.documentName()), i18n("Close Document"),
            KStandardGuiItem.save(), KStandardGuiItem.discard())
        if res == KMessageBox.Yes:
            if self.url().isEmpty():
                self.saveAs()
            else:
                self.save()
            return self.doc.waitSaveComplete()
        elif res == KMessageBox.No:
            return True
        else: # cancel
            return False

    def aboutToClose(self):
        """
        Implement this if you want to save some last minute state, etc.
        After calling this the view and document (if they have materialized)
        will be deleted.
        This method will also be called if the document never materialized.
        So check if self.view really is a View before you do something with it.
        """
        pass
    
    def viewActions(self):
        """
        Iterate over the View actions for which the state could be saved.
        """
        if self.view:
            for name in (
                "view_dynamic_word_wrap",
                "view_word_wrap_marker", "view_border", "view_line_numbers",
                "view_scrollbar_marks", "view_folding_markers"):
                action = self.view.actionCollection().action(name)
                if action:
                    yield name, action

    def readConfig(self, group):
        """
        This can be called by a state manager. You can read stuff from
        the KConfigGroup group, to adjust settings for the loaded document
        and its view.
        """
        # restore some options from the view menu
        for name, action in self.viewActions():
            if group.hasKey(name):
                value = group.readEntry(name, QVariant(False)).toBool()
                if value != action.isChecked():
                    action.trigger()
        # cursor position
        line, okline = group.readEntry("line", QVariant(0)).toInt()
        column, okcolumn = group.readEntry("column", QVariant(0)).toInt()
        if okline and okcolumn and line < self.doc.lines():
            self.view.setCursorPosition(KTextEditor.Cursor(line, column))
        # bookmarks
        markiface = self.doc.markInterface()
        if markiface:
            marks = str(group.readEntry("bookmarks", QVariant("")).toString())
            if re.match(r"\d+:\d+(,\d+:\d+)*$", marks):
                for m in marks.split(','):
                    line, mark = map(int, m.split(':'))
                    if line < self.doc.lines():
                        markiface.addMark(line, mark)

    def writeConfig(self, group):
        """
        This can be called by a state manager. You can write stuff to
        the KConfigGroup group, to save settings for the document and its view.
        """
        # save some options in the view menu
        for name, action in self.viewActions():
            group.writeEntry(name, QVariant(action.isChecked()))
        # cursor position
        cursor = self.view.cursorPosition()
        group.writeEntry("line", QVariant(cursor.line()))
        group.writeEntry("column", QVariant(cursor.column()))
        # bookmarks
        # markInterface().marks() crashes so we use mark() instead...
        markiface = self.doc.markInterface()
        if markiface:
            marks = []
            for line in range(self.doc.lines()):
                m = markiface.mark(line)
                if m:
                    marks.append("%d:%d" % (line, m))
            group.writeEntry("bookmarks", ','.join(marks))
        # also save the encoding
        group.writeEntry("encoding", QVariant(self.encoding()))

    def line(self, lineNumber = None):
        """
        Returns the text of the given or current line.
        """
        if self.doc:
            if lineNumber is None:
                lineNumber = self.view.cursorPosition().line()
            return unicode(self.doc.line(lineNumber))
    
    def textToCursor(self, line=None, column=None):
        """
        Returns the text from the start of the document to the given
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
            return unicode(self.doc.text(KTextEditor.Range(0, 0, line, column)))

    def selectionText(self):
        """
        Returns the selected text or None.
        """
        if self.view and self.view.selection():
            return unicode(self.view.selectionText())
    
    def selectionOrDocument(self):
        """
        Returns a tuple(text, start).
        
        If there is a selection, start is the position in the text the selection
        starts, and text is the document text from the (0, 0) to the end of the
        selection. If there is no selection, the whole document text is returned
        and start = 0.
        """
        docRange = self.doc.documentRange()
        selRange = self.view.selectionRange()
        if self.view.selection() and selRange.start().position() != selRange.end().position():
            text = self.textToCursor(selRange.end())
            line, column = selRange.start().position()
            return text, cursorToPosition(line, column, text)
        return self.text(), 0
        
    def replaceSelectionWith(self, text, keepSelection=True):
        """
        Convenience method. Replaces the selection (if any) with text.
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

    def resetCursorTranslations(self):
        """
        Clears the cursor translations that keep Point and Click
        working while the document changes.
        Call this when the PDF output document has been updated by
        a succesful LilyPond run (for example).
        """
        if self.doc:
            self._cursorTranslator = CursorTranslator(self)
    
    def kateModeVariables(self):
        """
        Returns a dict with the katemoderc variables for the mode
        of the current document, if available.
        """
        mode = self.doc and self.doc.mode() or self.app.defaultMode
        if mode:
            c = KConfig("katemoderc", KConfig.NoGlobals)
            v = unicode(c.group(mode).readEntry("Variables", QVariant("")).toString())
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
                #v = unicode(iface.variable(varName))
                #if v:
                    #return v
        #d = self.kateModeVariables()
        #if d:
            #return d.get(varName)
    
    def kateVariable(self, varName):
        """
        Returns the value of the kate variable varName, if set in the document
        or in the modeline for the current document mode.
        """
        lines = self.textLines()
        del lines[10:-10] # only look at the first and last ten lines.
        for line in lines:
            if 'kate:' in line:
                m = re.search(r"[:;]\s*\b%s\s+([^;]+)" % varName, line)
                if m:
                    return m.group(1)
        d = self.kateModeVariables()
        if d:
            return d.get(varName)
        
    def tabWidth(self):
        """
        Returns the width of the tab character, valid for the current document.
        """
        v = self.kateVariable("tab-width")
        if v and v.isdigit():
            return int(v)
        group = KGlobal.config().group("Kate Document Defaults")
        res, ok = group.readEntry("Tab Width", QVariant(8)).toInt()
        if ok:
            return res
        
    def indentationWidth(self):
        """
        Returns the indent-width for the current document.
        """
        v = self.kateVariable("indent-width")
        if v and v.isdigit():
            return int(v)
        group = KGlobal.config().group("Kate Document Defaults")
        res, ok = group.readEntry("Indentation Width", QVariant(2)).toInt()
        if ok:
            return res
    
    def indentationSpaces(self):
        """
        Returns True if indent uses spaces, otherwise False.
        """
        v = self.kateVariable("space-indent")
        if v:
            return v in ('on', '1', 'yes', 'y', 'true')
        group = KGlobal.config().group("Kate Document Defaults")
        flags, ok = group.readEntry('Basic Config Flags', QVariant(0)).toInt()
        return bool(ok and flags & 0x2000000)

    
class UserShortcuts(object):
    """
    Manages user-defined keyboard shortcuts.
    Keyboard shortcuts can be loaded without loading the module they belong to.
    If a shortcut is triggered, the module is loaded on demand and the action
    triggered.

    You should subclass this base class and implement the widget() and target()
    methods.
    """

    # which config group to store our shortcuts
    configGroup = "user shortcuts"
    
    # the shortcut type to use
    shortcutContext = Qt.WidgetWithChildrenShortcut
    
    def __init__(self, mainwin):
        self.mainwin = mainwin
        self._collection = KActionCollection(self.widget())
        self._collection.setConfigGroup(self.configGroup)
        self._collection.addAssociatedWidget(self.widget())
        # load the shortcuts
        group = KGlobal.config().group(self.configGroup)
        for key in group.keyList():
            if group.readEntry(key, QVariant("")).toString():
                self.addAction(key)
        self._collection.readSettings()
    
    def widget(self):
        """
        Should return the widget where the actions should be added to.
        """
        pass
        
    def target(self):
        """
        Should return the object that can further process our actions.
        It should have the following methods:
        - actionTriggered(name)
        - populateAction(action)
        """
        pass
        
    def addAction(self, name):
        """
        (Internal) Create a new action with name name.
        If existing, return the existing action.
        """
        action = self._collection.action(name)
        if not action:
            action = self._collection.addAction(name)
            action.setShortcutContext(self.shortcutContext)
            QObject.connect(action, SIGNAL("triggered()"),
                lambda: self.actionTriggered(name))
        return action
    
    def actionTriggered(self, name):
        self.target().actionTriggered(name)

    def shortcuts(self):
        """
        Returns the list of names we have non-empty shortcuts for.
        """
        return [action.objectName()
            for action in self._collection.actions()
            if not action.shortcut().isEmpty()]
                
    def shortcut(self, name):
        """
        Returns the shortcut for action, if existing.
        """
        action = self._collection.action(name)
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
        if not shortcut.isEmpty():
            action = self.addAction(name)
            action.setShortcut(shortcut)
            self._collection.writeSettings(None, True, action)
        else:
            self.removeShortcut(name)
    
    def removeShortcut(self, name):
        """
        Deletes the given action if existing.
        """
        action = self._collection.action(name)
        if action:
            sip.delete(action)
            KGlobal.config().group(self.configGroup).deleteEntry(name)
            
    def actionCollection(self):
        """
        Returns the action collection, fully populated with texts and
        icons.
        """
        for action in self._collection.actions()[:]:
            if action.shortcut().isEmpty():
                self.removeShortcut(action.objectName())
            else:
                self.target().populateAction(action)
        return self._collection

    def shakeHands(self, names):
        """
        Deletes all actions not in names, and returns a list of the names
        we have valid actions for.
        """
        result = []
        for action in self._collection.actions()[:]:
            if action.objectName() not in names:
                self.removeShortcut(action.objectName()) 
            elif not action.shortcut().isEmpty():
                result.append(action.objectName())
        return result
        

class StateManager(object):
    """
    Manages state and meta-info for documents, like bookmarks
    and cursor position, etc.
    """
    def __init__(self, app):
        self.app = app
        self.metainfos = KConfig("metainfos", KConfig.NoGlobals, "appdata")
        
    def groupForUrl(self, url):
        if not url.isEmpty() and self.metainfos.hasGroup(url.prettyUrl()):
            return self.metainfos.group(url.prettyUrl())
            
    def loadState(self, doc):
        group = self.groupForUrl(doc.url())
        if group:
            last = group.readEntry("time", QVariant(0.0)).toDouble()[0]
            # when it is a local file, only load the state when the
            # file was not modified later
            if not doc.localPath() or (
                    os.path.exists(doc.localPath()) and
                    os.path.getmtime(doc.localPath()) <= last):
                doc.readConfig(group)
            
    def saveState(self, doc):
        if doc.view and not doc.url().isEmpty():
            group = self.metainfos.group(doc.url().prettyUrl())
            group.writeEntry("time", QVariant(time.time()))
            doc.writeConfig(group)
            group.sync()
            
    def cleanup(self):
        """ Purge entries that are not used for more than a month. """
        for g in self.metainfos.groupList():
            last = self.metainfos.group(g).readEntry("time", QVariant(0.0)).toDouble()[0]
            if (time.time() - last) / 86400 > 31:
                self.metainfos.deleteGroup(g)
        self.metainfos.sync()


class CursorTranslator(object):
    """
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
        """
        Translates a cursor position to the current document.
        Also resolves tabs (i.e. the column parameter is the virtual position).
        Returns a KTextEditor.Cursor instance.
        """
        if line < len(self.savedTabs) and self.savedTabs[line]:
            column = resolvetabs_indices(column, self.savedTabs[line])
        cursor = KTextEditor.Cursor(line, column)
        if self.iface:
            self.iface.smartMutex().lock()
            self.iface.useRevision(self.revision)
            cursor = self.iface.translateFromRevision(cursor,
                KTextEditor.SmartCursor.MoveOnInsert)
            self.iface.clearRevision()
            self.iface.smartMutex().unlock()
        return cursor


def tabindices(text):
    """
    Returns a list of positions in text at which a tab character is found.
    If no tab character is found, returns None.
    """
    result = []
    tab = text.find('\t')
    while tab != -1:
        result.append(tab)
        tab = text.find('\t', tab + 1)
    return result or None

def resolvetabs_text(column, text):
    """
    Parses text for tab stops and resolves column (a virtual position)
    to point to the correct character position in the text.
    """
    return resolvetabs_indices(column, tabindices(text))

def resolvetabs_indices(column, indices):
    """
    Uses the tabstops in indices (a list with the indices of tabstops in a text)
    to translate a virtual cursor position to the correct character index.
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
    """
    Returns the character position in text of a cursor with line and column.
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

