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

import itertools, os, re, sip, weakref

from PyQt4.QtCore import QEvent, QTimer, Qt, SLOT, pyqtSignature
from PyQt4.QtGui import (
    QAction, QActionGroup, QDialog, QKeySequence, QLabel, QPixmap, QSplitter,
    QStackedWidget, QTabBar, QVBoxLayout, QWidget)
from PyKDE4.kdecore import (
    KConfig, KGlobal, KPluginLoader, KToolInvocation, KUrl, i18n)
from PyKDE4.kdeui import (
    KAcceleratorManager, KAction, KActionCollection, KActionMenu, KDialog,
    KEditToolBar, KHBox, KIcon, KKeySequenceWidget, KMenu, KMessageBox,
    KMultiTabBar, KShortcut, KShortcutsDialog, KShortcutsEditor,
    KStandardAction, KStandardGuiItem, KToggleFullScreenAction, KVBox)
from PyKDE4.kparts import KParts
from PyKDE4.ktexteditor import KTextEditor
from PyKDE4.kio import KEncodingFileDialog

from signals import Signal

import kateshell.app
from kateshell.app import cacheresult, naturalsort

# Easily get our global config
def config(group="kateshell"):
    return KGlobal.config().group(group)


Top = KMultiTabBar.Top
Right = KMultiTabBar.Right
Bottom = KMultiTabBar.Bottom
Left = KMultiTabBar.Left


def addAccelerators(actions):
    """Adds accelerators to the list of actions.
    
    Actions that have accelerators are skipped, but the accelerators they use
    are recorded. This can be used for e.g. menus that are created on the fly,
    and not picked up by KAcceleratorManager.
    
    """
    todo, used = [], []
    for a in actions:
        if a.text():
            m = re.search(r'&(\w)', a.text())
            used.append(m.group(1).lower()) if m else todo.append(a)
    for a in todo:
        text = a.text()
        for m in itertools.chain(re.finditer(r'\b\w', text),
                                 re.finditer(r'\B\w', text)):
            if m.group().lower() not in used:
                used.append(m.group().lower())
                a.setText(text[:m.start()] + '&' + text[m.start():])
                break


class MainWindow(KParts.MainWindow):
    """An editor main window.
    
    Emits the following (Python) signals:
    - currentDocumentChanged(Document) if the active document changes or its url.
    - aboutToClose() when the window will be closed.
    
    """
    currentDocumentChanged = Signal()
    aboutToClose = Signal()
    
    def __init__(self, app):
        KParts.MainWindow.__init__(self)
        self.app = app
        self._currentDoc = None
        self.docks = {}
        self.tools = {}
        
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
        
        tab_bottom = TabBar(Bottom, sb)
        sb.addWidget(tab_bottom, 0)

        # window layout
        h = KHBox(self)
        self.setCentralWidget(h)
        tab_left = TabBar(Left, h)
        s = QSplitter(Qt.Horizontal, h)
        tab_right = TabBar(Right, h)

        self.docks[Left] = Dock(s, tab_left, "go-previous", i18n("Left Sidebar"))
        s.addWidget(self.docks[Left])
        v = KVBox(s)
        s.addWidget(v)
        self.docks[Right] = Dock(s, tab_right, "go-next", i18n("Right Sidebar"))
        s.addWidget(self.docks[Right])
        
        s.setStretchFactor(0, 0)
        s.setStretchFactor(1, 1)
        s.setStretchFactor(2, 1)
        s.setChildrenCollapsible(False)
        s.setSizes((100, 400, 600))
        
        tab_top = TabBar(Top, v)
        s1 = QSplitter(Qt.Vertical, v)
        
        self.docks[Top] = Dock(s1, tab_top, "go-up", i18n("Top Sidebar"))
        s1.addWidget(self.docks[Top])
        # tabbar and editor view widget stack together in one widget
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.viewTabs = self.createViewTabBar()
        layout.addWidget(self.viewTabs)
        self.viewStack = QStackedWidget()
        layout.addWidget(self.viewStack)
        s1.addWidget(w)
        self.docks[Bottom] = Dock(s1, tab_bottom, "go-down", i18n("Bottom Sidebar"))
        s1.addWidget(self.docks[Bottom])

        s1.setStretchFactor(0, 0)
        s1.setStretchFactor(1, 1)
        s1.setStretchFactor(2, 0)
        s1.setChildrenCollapsible(False)
        
        # Set some reasonable default sizes for top and bottom dock, to
        # prevent the embedded terminal taking up a too large default space.
        s1.setSizes((140, 200, 140))
        
        self.viewStack.setMinimumSize(200, 100)

        self._selectionActions = []
        self.setupActions() # Let subclasses add more actions
        self.setupTools()   # Initialize the tools before loading ui.rc
        self.setStandardToolBarMenuEnabled(True)
        self.createShellGUI(True) # ui.rc is loaded automagically
        
        if not self.initialGeometrySet():
            self.resize(700, 480)
        
        self.setupGeneratedMenus()
        self.setAutoSaveSettings()
        self.loadSettings()
        self.setAcceptDrops(True)
        app.documentCreated.connect(self.addToRecentFiles)
        app.documentMaterialized.connect(self.addDocument)
        app.activeChanged.connect(self.setCurrentDocument)
        app.documentClosed.connect(self.removeDocument)
        self.sessionManager().sessionChanged.connect(self.updateCaption)
        
    def setupActions(self):
        self.act('file_new', KStandardAction.New, self.newDocument)
        self.act('file_open', KStandardAction.Open, self.openDocument)
        self.act('file_close', KStandardAction.Close,
            lambda: self.app.activeDocument().close())
        self.act('file_save', KStandardAction.Save,
            lambda: self.app.activeDocument().save())
        self.act('file_save_as', KStandardAction.SaveAs,
            lambda: self.app.activeDocument().saveAs())
        self.act('file_close_other', i18n("Close Other Documents"),
            self.closeOtherDocuments)
        self.act('file_quit', KStandardAction.Quit, self.app.quit)
        self.act('doc_back', KStandardAction.Back, self.app.back)
        self.act('doc_forward', KStandardAction.Forward, self.app.forward)
        self.showPath = self.act('options_show_full_path', i18n("Show Path"),
            self.updateCaption)
        self.showPath.setCheckable(True)
        self.showTabs = self.act('options_show_tabs', i18n("Show Document Tabs"),
            lambda: self.viewTabs.setVisible(self.showTabs.isChecked()))
        self.showTabs.setCheckable(True)
        
        # full screen
        a = self.actionCollection().addAction(KStandardAction.FullScreen, 'fullscreen')
        a.toggled.connect(lambda t: KToggleFullScreenAction.setFullScreen(self, t))
        # recent files.
        self.openRecent = KStandardAction.openRecent(
            self, SLOT("slotOpenRecent(KUrl)"), self)
        self.actionCollection().addAction(
            self.openRecent.objectName(), self.openRecent)
        self.act('options_configure_toolbars', KStandardAction.ConfigureToolbars,
            self.editToolbars)
        self.act('options_configure_keys', KStandardAction.KeyBindings,
            self.editKeys)
        
        # tool views submenu
        a = KActionMenu(i18n("&Tool Views"), self)
        self.actionCollection().addAction('options_toolviews', a)
        def makefunc(action):
            def populate():
                menu = action.menu()
                menu.clear()
                for tool in self.tools.itervalues():
                    menu.addSeparator()
                    menu.addAction(tool.action())
                    tool.addMenuActions(menu)
            return populate
        a.menu().aboutToShow.connect(makefunc(a))
        
        # sessions menu
        @self.onAction(i18n("New..."), "document-new")
        def sessions_new():
            self.sessionManager().new()
            
        @self.onAction(KStandardGuiItem.save().text(), "document-save")
        def sessions_save():
            self.sessionManager().save()
            
        @self.onAction(i18n("Manage Sessions..."), "view-choose")
        def sessions_manage():
            self.sessionManager().manage()
            
        
    def setupTools(self):
        """Implement this to create the Tool instances.
        
        This is called before the ui.rc file is loaded, so the user can
        configure the keyboard shortcuts for the tools.
        """
        pass
    
    def xmlGuiContainer(self, name):
        """Returns the XMLGUI container with name.
        
        If not present, the local ui.rc file is probably erroneous,
        inform the user via a message box.
        
        """
        obj = self.factory().container(name, self)
        if obj:
            return obj
        else:
            KMessageBox.error(self, i18n(
                "Could not find the XMLGUI container \"%1\".\n\n"
                "Probably the local ui.rc file contains errors. "
                "It is recommended to delete this file because elements in the "
                "user interface will be missing. "
                "This is the full path of the file:\n\n%2\n",
                name, os.path.join(
                    KGlobal.dirs().saveLocation('appdata'),
                    self.xmlFile())))
                
    def setupGeneratedMenus(self):
        """This should setup menus that are generated on show.
        
        The generated menus that are setup here must be rebound to the XMLGUI if
        the toolbars are reconfigured by the user, that's why they must be setup
        in this method. This method is called again if the user changes the
        toolbars.
        
        """
        # Set up the documents menu so that it shows all open documents.
        docMenu = self.xmlGuiContainer("documents")
        if docMenu:
            docGroup = QActionGroup(docMenu)
            docGroup.setExclusive(True)
            docGroup.triggered.connect(lambda a: a.doc().setActive())
                
            def populateDocMenu():
                for a in docGroup.actions():
                    sip.delete(a)
                for d in self.app.documents:
                    a = KAction(d.documentName(), docGroup)
                    a.setCheckable(True)
                    a.doc = weakref.ref(d)
                    icon = d.documentIcon()
                    if icon:
                        a.setIcon(KIcon(icon))
                    if d is self._currentDoc:
                        a.setChecked(True)
                    docGroup.addAction(a)
                    docMenu.addAction(a)
                addAccelerators(docMenu.actions())
            docMenu.setParent(docMenu.parent()) # BUG: SIP otherwise looses outer scope
            docMenu.aboutToShow.connect(populateDocMenu)
        
        # sessions menu
        sessMenu = self.xmlGuiContainer("sessions")
        if sessMenu:
            sessGroup = QActionGroup(sessMenu)
            sessGroup.setExclusive(True)
                
            def populateSessMenu():
                for a in sessGroup.actions():
                    sip.delete(a)
                
                sm = self.sessionManager()
                sessions = sm.names()
                current = sm.current()
                
                if not sessions:
                    return
                # "No Session" action
                a = KAction(i18n("No Session"), sessGroup)
                a.setCheckable(True)
                if not current:
                    a.setChecked(True)
                else:
                    a.triggered.connect(lambda: sm.switch(None))
                sessGroup.addAction(a)
                sessMenu.addAction(a)
                sessGroup.addAction(sessMenu.addSeparator())
                # other sessions:
                for name in sessions:
                    a = KAction(name, sessGroup)
                    a.setCheckable(True)
                    if name == current:
                        a.setChecked(True)
                    a.triggered.connect((lambda name: lambda: sm.switch(name))(name))
                    sessGroup.addAction(a)
                    sessMenu.addAction(a)
                addAccelerators(sessMenu.actions())
            sessMenu.setParent(sessMenu.parent()) # BUG: SIP otherwise looses outer scope
            sessMenu.aboutToShow.connect(populateSessMenu)
        
    @cacheresult
    def sessionManager(self):
        return self.createSessionManager()
        
    def createSessionManager(self):
        """Override this to return a different session manager."""
        return SessionManager(self)
    
    def act(self, name, texttype, func,
            icon=None, tooltip=None, whatsthis=None, key=None):
        """Create an action and add it to own actionCollection."""
        if isinstance(texttype, KStandardAction.StandardAction):
            a = self.actionCollection().addAction(texttype, name)
        else:
            a = self.actionCollection().addAction(name)
            a.setText(texttype)
        a.triggered.connect(func)
        if icon: a.setIcon(KIcon(icon))
        if tooltip: a.setToolTip(tooltip)
        if whatsthis: a.setWhatsThis(whatsthis)
        if key: a.setShortcut(KShortcut(key))
        return a
        
    def selAct(self, *args, **kwargs):
        a = self.act(*args, **kwargs)
        self._selectionActions.append(a)
        return a

    def onAction(self, texttype, icon=None, tooltip=None, whatsthis=None, key=None):
        """Decorator to add a function to an action.
        
        The name of the function becomes the name of the action.
        
        """
        def decorator(func):
            self.act(func.func_name, texttype, func, icon, tooltip, whatsthis, key)
            return func
        return decorator
        
    def onSelAction(self, texttype, icon=None, tooltip=None, whatsthis=None, key=None,
                    warn=True, keepSelection=True):
        """Decorator to add a function that is run on the selection to an action.
        
        The name of the function becomes the name of the action.
        If there is no selection, the action is automatically disabled.
        
        """
        def decorator(func):
            def selfunc():
                doc = self.currentDocument()
                if doc:
                    text = doc.selectionText()
                    if text:
                        result = func(text)
                        if result is not None:
                            doc.replaceSelectionWith(result, keepSelection)
                    elif warn:
                        KMessageBox.sorry(self, i18n("Please select some text first."))
            self.selAct(func.func_name, texttype, selfunc, icon, tooltip, whatsthis, key)
            return func
        return decorator
        
    def setCurrentDocument(self, doc):
        """Called when the application makes a different Document active."""
        if self._currentDoc:
            self._currentDoc.urlChanged.disconnect(self.slotUrlChanged)
            self._currentDoc.captionChanged.disconnect(self.updateCaption)
            self._currentDoc.statusChanged.disconnect(self.updateStatusBar)
            self._currentDoc.selectionChanged.disconnect(self.updateSelection)
            self.guiFactory().removeClient(self._currentDoc.view)
        self._currentDoc = doc
        self.guiFactory().addClient(doc.view)
        self.viewStack.setCurrentWidget(doc.view)
        doc.urlChanged.connect(self.slotUrlChanged)
        doc.captionChanged.connect(self.updateCaption)
        doc.statusChanged.connect(self.updateStatusBar)
        doc.selectionChanged.connect(self.updateSelection)
        self.updateCaption()
        self.updateStatusBar()
        self.updateSelection()
        self.currentDocumentChanged(doc) # emit our signal

    def addDocument(self, doc):
        """Internal. Add Document to our viewStack."""
        self.viewStack.addWidget(doc.view)
        
    def removeDocument(self, doc):
        """Internal. Remove Document from our viewStack."""
        self.viewStack.removeWidget(doc.view)
        if doc is self._currentDoc:
            self.guiFactory().removeClient(doc.view)
            self._currentDoc = None
    
    def view(self):
        """Returns the current view or None if none."""
        if self._currentDoc:
            return self._currentDoc.view
    
    def currentDocument(self):
        """Returns the current Document or None if none."""
        return self._currentDoc
    
    def slotUrlChanged(self, doc=None):
        """Called when the url of the current Document changes."""
        self.addToRecentFiles(doc)
        self.currentDocumentChanged(doc or self._currentDoc)

    def updateCaption(self):
        """Called when the window title needs to be redisplayed."""
        session = self.sessionManager().current()
        caption = "{0}: ".format(session) if session else ""
        doc = self.currentDocument()
        if doc:
            name = (self.showPath.isChecked() and doc.prettyUrl() or
                    doc.documentName())
            if len(name) > 72:
                name = '...' + name[-69:]
            caption += name
            if doc.isModified():
                caption += " [{0}]".format(i18n("modified"))
                self.sb_modified.setPixmap(KIcon("document-save").pixmap(16))
            else:
                self.sb_modified.setPixmap(QPixmap())
        self.setCaption(caption)
        
    def updateStatusBar(self):
        """Called when the status bar needs to be redisplayed."""
        doc = self.currentDocument()
        pos = doc.view.cursorPositionVirtual()
        line, col = pos.line()+1, pos.column()
        self.sb_linecol.setText(i18n("Line: %1 Col: %2", line, col))
        self.sb_insmode.setText(doc.view.viewMode())

    def updateSelection(self):
        """Called when the selection changes."""
        doc = self.currentDocument()
        enable = doc.view.selection() and not doc.view.selectionRange().isEmpty()
        for a in self._selectionActions:
            a.setEnabled(enable)
        if doc.view.blockSelection():
            text, tip = i18n("BLOCK"), i18n("Block selection mode")
        else:
            text, tip = i18n("LINE"), i18n("Line selection mode")
        self.sb_selmode.setText(" {0} ".format(text))
        self.sb_selmode.setToolTip(tip)

    def editKeys(self):
        """Opens a window to edit the keyboard shortcuts."""
        with self.app.busyCursor():
            dlg = KShortcutsDialog(KShortcutsEditor.AllActions,
                KShortcutsEditor.LetterShortcutsDisallowed, self)
            for name, collection in self.allActionCollections():
                dlg.addCollection(collection, name)
        dlg.configure()
    
    def allActionCollections(self):
        """Iterator over KActionCollections.
        
        Yields all KActionCollections that need to be checked if the user
        wants to alter a keyboard shortcut.
        
        Each item is a two-tuple (name, KActionCollection).
        
        """
        yield KGlobal.mainComponent().aboutData().programName(), self.actionCollection()
        if self.view():
            yield None, self.view().actionCollection()
            
    def editToolbars(self):
        """Opens a window to edit the toolbar(s)."""
        conf = config("MainWindow")
        self.saveMainWindowSettings(conf)
        dlg = KEditToolBar(self.guiFactory(), self)
        def newToolbarConfig():
            self.applyMainWindowSettings(conf)
            self.setupGeneratedMenus()
        dlg.newToolbarConfig.connect(newToolbarConfig)
        dlg.setModal(True)
        dlg.show()

    def newDocument(self):
        """Create a new empty document."""
        self.app.createDocument().setActive()
        
    def openDocument(self):
        """Open an existing document."""
        res = KEncodingFileDialog.getOpenUrlsAndEncoding(
            self.app.defaultEncoding,
            self.currentDocument().url().url()
            or self.sessionManager().basedir() or self.app.defaultDirectory(),
            '\n'.join(self.app.fileTypes + ["*|" + i18n("All Files")]),
            self, i18n("Open File"))
        docs = [self.app.openUrl(url, res.encoding)
                for url in res.URLs if not url.isEmpty()]
        if docs:
            docs[-1].setActive()
    
    def addToRecentFiles(self, doc=None):
        """Add url of document to recently opened files."""
        doc = doc or self.currentDocument()
        if doc:
            url = doc.url()
            if not url.isEmpty() and url not in self.openRecent.urls():
                self.openRecent.addUrl(url)
    
    @pyqtSignature("KUrl")
    def slotOpenRecent(self, url):
        """Called by the open recent files action."""
        self.app.openUrl(url).setActive()

    def queryClose(self):
        """Called when the user wants to close the MainWindow.
        
        Returns True if the application may quit.
        
        """
        if self.app.kapp.sessionSaving():
            sc = self.app.kapp.sessionConfig()
            self.saveDocumentList(sc.group("documents"))
            self.sessionManager().saveProperties(sc.group("session"))
        # just ask, cancel at any time will keep all documents.
        for d in self.app.history[::-1]: # iterate over a copy, current first
            if d.isModified():
                d.setActive()
                if not d.queryClose():
                    return False # cancelled
        # Then close the documents
        self.currentDocumentChanged.clear() # disconnect all tools etc.
        self.aboutToClose()
        for d in self.app.history[:]: # iterate over a copy
            d.close(False)
        # save some settings
        self.saveSettings()
        return True
    
    def closeOtherDocuments(self):
        """Close all documents except the current document."""
        # iterate over a copy, current first, except current document
        docs = self.app.history[-2::-1]
        for d in docs:
            if d.isModified():
                if not d.queryClose():
                    return # cancelled
        for d in docs:
            d.close(False)
    
    def readGlobalProperties(self, conf):
        """Called on session restore, loads the list of open documents."""
        self.loadDocumentList(conf.group("documents"))
        self.sessionManager().readProperties(conf.group("session"))
        
    def saveDocumentList(self, cg):
        """Stores the list of documents to the given KConfigGroup."""
        urls = [d.url().url() for d in self.viewTabs.docs] # order of tabs
        d = self.currentDocument()
        current = self.viewTabs.docs.index(d) if d else -1
        cg.writePathEntry("urls", urls)
        cg.writeEntry("active", current)
        cg.sync()
        
    def loadDocumentList(self, cg):
        """Loads the documents mentioned in the given KConfigGroup."""
        urls = cg.readPathEntry("urls", [])
        active = cg.readEntry("active", 0)
        if any(urls):
            docs = [self.app.openUrl(KUrl(url)) for url in urls]
            if docs:
                if active < 0 or active >= len(docs):
                    active = len(docs) - 1
                docs[active].setActive()
    
    def loadSettings(self):
        """Load some settings from our configfile."""
        self.openRecent.loadEntries(config("recent files"))
        self.showPath.setChecked(config().readEntry("show full path", False))
        self.showTabs.setChecked(config().readEntry("show tabs", True))
        self.viewTabs.setVisible(self.showTabs.isChecked())

    def saveSettings(self):
        """Store settings in our configfile."""
        self.openRecent.saveEntries(config("recent files"))
        config().writeEntry("show full path", self.showPath.isChecked())
        config().writeEntry("show tabs", self.showTabs.isChecked())
        # also all the tools:
        for tool in self.tools.itervalues():
            tool.saveSettings()
        # also the main editor object:
        self.app.editor.writeConfig()
        # write them back
        config().sync()

    def createViewTabBar(self):
        return ViewTabBar(self)

    def dragEnterEvent(self, event):
        event.setAccepted(KUrl.List.canDecode(event.mimeData()))
        
    def dropEvent(self, event):
        if KUrl.List.canDecode(event.mimeData()):
            urls = KUrl.List.fromMimeData(event.mimeData())
            docs = map(self.app.openUrl, urls)
            if docs:
                docs[-1].setActive()


class ViewTabBar(QTabBar):
    """The tab bar above the document editor view."""
    def __init__(self, mainwin):
        QTabBar.__init__(self)
        KAcceleratorManager.setNoAccel(self)
        self.mainwin = mainwin
        self.docs = []
        # get the documents to create their tabs.
        for doc in mainwin.app.documents:
            self.addDocument(doc)
            if doc.isActive():
                self.setCurrentDocument(doc)
        mainwin.app.documentCreated.connect(self.addDocument)
        mainwin.app.documentClosed.connect(self.removeDocument)
        mainwin.app.documentMaterialized.connect(self.setDocumentStatus)
        self.currentChanged.connect(self.slotCurrentChanged)
        mainwin.currentDocumentChanged.connect(self.setCurrentDocument)
        try:
            self.setTabsClosable
            self.tabCloseRequested.connect(self.slotTabCloseRequested)
        except AttributeError:
            pass
        try:
            self.setMovable
            self.tabMoved.connect(self.slotTabMoved)
        except AttributeError:
            pass
        self.readSettings()
        
    def readSettings(self):
        # closeable? only in Qt >= 4.6
        try:
            self.setTabsClosable(config("tab bar").readEntry("close button", True))
        except AttributeError:
            pass
        
        # expanding? only in Qt >= 4.5
        try:
            self.setExpanding(config("tab bar").readEntry("expanding", False))
        except AttributeError:
            pass
        
        # movable? only in Qt >= 4.5
        try:
            self.setMovable(config("tab bar").readEntry("movable", True))
        except AttributeError:
            pass
        
    def addDocument(self, doc):
        if doc not in self.docs:
            self.docs.append(doc)
            self.blockSignals(True)
            self.addTab('')
            self.blockSignals(False)
            self.setDocumentStatus(doc)
            doc.urlChanged.connect(self.setDocumentStatus)
            doc.captionChanged.connect(self.setDocumentStatus)

    def removeDocument(self, doc):
        if doc in self.docs:
            index = self.docs.index(doc)
            self.docs.remove(doc)
            self.blockSignals(True)
            self.removeTab(index)
            self.blockSignals(False)

    def setDocumentStatus(self, doc):
        if doc in self.docs:
            index = self.docs.index(doc)
            self.setTabIcon(index, KIcon(doc.documentIcon() or "text-plain"))
            self.setTabText(index, doc.documentName())
    
    def setCurrentDocument(self, doc):
        """ Raise the tab belonging to this document."""
        if doc in self.docs:
            index = self.docs.index(doc)
            self.blockSignals(True)
            self.setCurrentIndex(index)
            self.blockSignals(False)

    def slotCurrentChanged(self, index):
        """ Called when the user clicks a tab. """
        self.docs[index].setActive()
    
    def slotTabCloseRequested(self, index):
        """ Called when the user clicks the close button. """
        self.docs[index].close()
    
    def slotTabMoved(self, index_from, index_to):
        """ Called when the user moved a tab. """
        doc = self.docs.pop(index_from)
        self.docs.insert(index_to, doc)
        
    def contextMenuEvent(self, ev):
        """ Called when the right mouse button is clicked on the tab bar. """
        tab = self.tabAt(ev.pos())
        if tab >= 0:
            menu = KMenu()
            self.addMenuActions(menu, self.docs[tab])
            menu.exec_(ev.globalPos())

    def addMenuActions(self, menu, doc):
        """ Populate the menu with actions relevant for the document. """
        g = KStandardGuiItem.save()
        a = menu.addAction(g.icon(), g.text())
        a.triggered.connect(lambda: doc.save())
        g = KStandardGuiItem.saveAs()
        a = menu.addAction(g.icon(), g.text())
        a.triggered.connect(lambda: doc.saveAs())
        menu.addSeparator()
        g = KStandardGuiItem.close()
        a = menu.addAction(g.icon(), g.text())
        a.triggered.connect(lambda: doc.close())


class TabBar(KMultiTabBar):
    """Our own tabbar with some nice defaults."""
    def __init__(self, orientation, parent, maxSize=18):
        KMultiTabBar.__init__(self, orientation, parent)
        self.setStyle(KMultiTabBar.KDEV3ICON)
        if maxSize:
            if orientation in (KMultiTabBar.Bottom, KMultiTabBar.Top):
                self.setMaximumHeight(maxSize)
            else:
                self.setMaximumWidth(maxSize)
        self._tools = []
        
    def addTool(self, tool):
        self._tools.append(tool)
        self.appendTab(tool.icon().pixmap(16), tool._id, tool.title())
        tab = self.tab(tool._id)
        tab.setFocusPolicy(Qt.NoFocus)
        tab.setToolTip(u"<b>{0}</b><br/>{1}".format(tool.title(),
            i18n("Right-click for tab options")))
        tab.setContextMenuPolicy(Qt.CustomContextMenu)
        tab.clicked.connect(tool.toggle)
        tab.setParent(tab.parent()) # BUG: otherwise SIP looses outer scope
        tab.customContextMenuRequested.connect(
            lambda pos: tool.showContextMenu(tab.mapToGlobal(pos)))

    def removeTool(self, tool):
        self._tools.remove(tool)
        self.removeTab(tool._id)
        
    def showTool(self, tool):
        self.tab(tool._id).setState(True)
        
    def hideTool(self, tool):
        self.tab(tool._id).setState(False)
        
    def updateState(self, tool):
        tab = self.tab(tool._id)
        tab.setIcon(tool.icon())
        tab.setText(tool.title())


class Dock(QStackedWidget):
    """A dock where tools can be added to.
    
    Hides itself when there are no tools visible.
    When it receives a tool, a button is created in the associated tabbar.
    
    """
    def __init__(self, parent, tabbar, icon, title):
        QStackedWidget.__init__(self, parent)
        self.tabbar = tabbar
        self.title = title
        self.icon = icon and KIcon(icon) or KIcon()
        self._tools = []          # a list of the tools we host
        self._currentTool = None # the currently active tool, if any
        self.hide() # by default

    def addTool(self, tool):
        """ Add a tool to our tabbar, save dock and tabid in the tool """
        self.tabbar.addTool(tool)
        self._tools.append(tool)
        if tool.isActive():
            self.showTool(tool)

    def removeTool(self, tool):
        """ Remove a tool from our dock. """
        self.tabbar.removeTool(tool)
        self._tools.remove(tool)
        if tool is self._currentTool:
            self._currentTool = None
            self.hide()
        
    def showTool(self, tool):
        """Internal: only to be called by tool.show().
        
        Use tool.show() to make a tool active.
        
        """
        if tool not in self._tools or tool is self._currentTool:
            return
        if self.indexOf(tool.widget) == -1:
            self.addWidget(tool.widget)
        self.setCurrentWidget(tool.widget)
        self.tabbar.showTool(tool)
        cur = self._currentTool
        self._currentTool = tool
        if cur:
            cur.hide()
        else:
            self.show()
            
    def hideTool(self, tool):
        """Internal: only to be called by tool.hide().
        
        Use tool.hide() to make a tool inactive.
        
        """
        self.tabbar.hideTool(tool)
        if tool is self._currentTool:
            self._currentTool = None
            self.hide()
        
    def currentTool(self):
        return self._currentTool
        
    def updateState(self, tool):
        self.tabbar.updateState(tool)


class DockDialog(QDialog):
    """A QDialog that (re)docks itself when closed."""
    def __init__(self, tool):
        QDialog.__init__(self, tool.mainwin)
        QVBoxLayout(self).setContentsMargins(0, 0, 0, 0)
        self.tool = tool
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.updateState()
    
    def show(self):
        # Take the widget by adding it to our layout
        self.layout().addWidget(self.tool.widget)
        if self.tool.dialogSize:
            self.resize(self.tool.dialogSize)
        QDialog.show(self)
        if self.tool.dialogPos:
            self.move(self.tool.dialogPos)
        
    def done(self, r):
        self.tool.dialogSize = self.size()
        self.tool.dialogPos = self.pos()
        self.tool.dock()
        QDialog.done(self, r)

    def updateState(self):
        title = KDialog.makeStandardCaption(self.tool.title(), self,
            KDialog.HIGCompliantCaption)
        self.setWindowTitle(title)
        self.setWindowIcon(self.tool.icon())

    def keyPressEvent(self, e):
        if e.key() != Qt.Key_Escape:
            QDialog.keyPressEvent(self, e)


class Tool(object):
    """A Tool, that can be docked or undocked in/from the MainWindow.
    
    Intended to be subclassed.
    
    """
    allowedPlaces = Top, Right, Bottom, Left
    defaultHeight = 300
    defaultWidth = 500
    
    helpAnchor, helpAppName = "", ""

    __instance_counter = 0
    
    def __init__(self, mainwin, name,
            title="", icon="", key="", dock=Right,
            widget=None):
        self._id = Tool.__instance_counter
        self._active = False
        self._docked = True
        self._dock = None
        self._dialog = None
        self.dialogSize = None
        self.dialogPos = None
        self.mainwin = mainwin
        self.name = name
        mainwin.tools[name] = self
        action = KAction(mainwin, triggered=self.slotAction) # action to toggle our view
        mainwin.actionCollection().addAction("tool_" + name, action)
        if key:
            action.setShortcut(KShortcut(key))
        self.widget = widget
        self.setTitle(title)
        self.setIcon(icon)
        self.setDock(dock)
        Tool.__instance_counter += 1
        self.loadSettings()
    
    def action(self):
        return self.mainwin.actionCollection().action("tool_" + self.name)
    
    def slotAction(self):
        """Called when our action is triggered.
        
        Default behaviour is to toggle the visibility of our tool.
        Override this to implement other behaviour when our action is called
        (e.g. focus instead of hide).
        
        """
        self.toggle()
        
    def materialize(self):
        """If not yet done, calls self.factory() to get the widget of our tool.
        
        The widget is stored in the widget instance attribute.
        Use this to make tools 'lazy': only instantiate the widget and load
        other modules if needed as soon as the user wants to show the tool.
        
        """
        if self.widget is None:
            with self.mainwin.app.busyCursor():
                self.widget = self.factory()
    
    def factory(self):
        """Should return this Tool's widget when it must become visible.
        
        I you didn't supply a widget on init, you must override this method.
        
        """
        return QWidget()
        
    def delete(self):
        """Completely remove the tool.
        
        Its association with the mainwindow is removed, and it will be
        garbage collected as soon as the last reference to it is lost.
        
        """
        if not self._docked:
            self.dock()
        self._dock.removeTool(self)
        if self.widget:
            sip.delete(self.widget)
        if self._dialog:
            sip.delete(self._dialog)
        sip.delete(self.action())
        del self._dock, self.widget, self._dialog
        del self.mainwin.tools[self.name]

    def show(self):
        """ Bring our tool into view. """
        self.materialize()
        if self._docked:
            self._active = True
            self._dock.showTool(self)
        else:
            self._dialog.raise_()
            
    def hide(self):
        """ Hide our tool. """
        if self._docked:
            self._active = False
            self._dock.hideTool(self)
            view = self.mainwin.view()
            if view:
                view.setFocus()

    def toggle(self):
        """ Toggle visibility if docked. """
        if self._docked:
            if self._active:
                self.hide()
            else:
                self.show()

    def isActive(self):
        """ Returns True if the tool is currently the active one in its dock."""
        return self._active
    
    def isDocked(self):
        """ Returns True if the tool is docked. """
        return self._docked
        
    def setDock(self, place):
        """ Puts the tool in one of the four places.
        
        place is one of (KMultiTabBar).Top, Right, Bottom, Left
        
        """
        dock = self.mainwin.docks.get(place, self._dock)
        if dock is self._dock:
            return
        if self._docked:
            if self._dock:
                self._dock.removeTool(self)
            dock.addTool(self)
        self._dock = dock
            
    def undock(self):
        """ Undock our widget """
        if not self._docked:
            return
        self._dock.removeTool(self)
        self.materialize()
        self._docked = False
        if not self._dialog:
            size = self._dock.size()
            if size.height() <= 0:
                size.setHeight(self.defaultHeight)
            if size.width() <= 0:
                size.setWidth(self.defaultWidth)
            self.dialogSize = size
            self._dialog = DockDialog(self)
        self._dialog.show()
        self.widget.show()

    def dock(self):
        """ Dock and hide the dialog window """
        if self._docked:
            return
        self._dialog.hide()
        self._docked = True
        self._dock.addTool(self)
        
    def icon(self):
        return self._icon
        
    def setIcon(self, icon):
        self._icon = icon and KIcon(icon) or KIcon()
        self.action().setIcon(self._icon)
        self.updateState()

    def title(self):
        return self._title
    
    def setTitle(self, title):
        self._title = title
        self.action().setText(self._title)
        self.updateState()
            
    def updateState(self):
        if self._docked:
            if self._dock:
                self._dock.updateState(self)
        else:
            self._dialog.updateState()
            
    def showContextMenu(self, globalPos):
        """Show a popup menu to manipulate this tool."""
        m = KMenu(self.mainwin)
        places = [place for place in Left, Right, Top, Bottom
            if place in self.allowedPlaces
            and self.mainwin.docks.get(place, self._dock) is not self._dock]
        if places:
            m.addTitle(KIcon("transform-move"), i18n("Move To"))
            for place in places:
                dock = self.mainwin.docks[place]
                a = m.addAction(dock.icon, dock.title)
                a.triggered.connect((lambda place: lambda: self.setDock(place))(place))
            m.addSeparator()
        a = m.addAction(KIcon("tab-detach"), i18n("Undock"))
        a.triggered.connect(self.undock)
        self.addMenuActions(m)
        if self.helpAnchor or self.helpAppName:
            m.addSeparator()
            a = m.addAction(KIcon("help-contextual"), KStandardGuiItem.help().text())
            a.triggered.connect(self.help)
        m.aboutToHide.connect(m.deleteLater)
        m.popup(globalPos)

    def addMenuActions(self, menu):
        """Use this to add your own actions to a tool menu."""
        pass
    
    def config(self):
        """ Return a suitable configgroup for our settings. """
        return config("tool_" + self.name)

    def loadSettings(self):
        """ Do not override this method, use readConfig instead. """
        conf = self.config()
        self.readConfig(conf)

    def saveSettings(self):
        """ Do not override this method, use writeConfig instead. """
        conf = self.config()
        self.writeConfig(conf)
        
    def readConfig(self, conf):
        """Implement this in your subclass to read additional config data."""
        pass
    
    def writeConfig(self, conf):
        """Implement this in your subclass to write additional config data."""
        pass
    
    def help(self):
        """Invokes Help on our tool.
        
        See the helpAnchor and helpAppName attributes.
        
        """
        KToolInvocation.invokeHelp(self.helpAnchor, self.helpAppName)


class KPartTool(Tool):
    """A Tool where the widget is loaded via the KParts system."""
    
    # set this to the library name you want to load
    _partlibrary = ""
    # set this to the name of the app containing this part
    _partappname = ""
    
    def __init__(self, mainwin, name, title="", icon="", key="", dock=Right):
        self.part = None
        self.failed = False
        Tool.__init__(self, mainwin, name, title, icon, key, dock)
    
    def factory(self):
        if self.part:
            return
        factory = KPluginLoader(self._partlibrary).factory()
        if factory:
            part = factory.create(self.mainwin)
            if part:
                self.part = part
                part.destroyed.connect(self.slotDestroyed, Qt.DirectConnection)
                QTimer.singleShot(0, self.partLoaded)
                return part.widget()
        self.failed = True
        return QLabel("<center><p>{0}</p><p>{1}</p></center>".format(
            i18n("Could not load %1", self._partlibrary),
            i18n("Please install %1", self._partappname or self._partlibrary)))

    def partLoaded(self):
        """ Called when part is loaded. Use this to apply settings, etc."""
        pass
    
    def delete(self):
        if self.part:
            self.part.destroyed.disconnect(self.slotDestroyed)
        super(KPartTool, self).delete()
        
    def slotDestroyed(self):
        self.part = None
        self.failed = False
        self.widget = None
        if not sip.isdeleted(self.mainwin):
            if self._docked:
                self.hide()
            elif self._dialog:
                self._active = False
                self._dialog.done(0)
        
    def openUrl(self, url):
        """ Expects KUrl."""
        if self.part:
            self.part.openUrl(url)


class UserShortcutManager(object):
    """Manages user-defined keyboard shortcuts.
    
    Keyboard shortcuts can be loaded without loading the module they belong to.
    If a shortcut is triggered, the module is loaded on demand and the action
    triggered.

    You should subclass this base class and implement the widget() and client()
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
            if group.readEntry(key, ""):
                self.addAction(key)
        self._collection.readSettings()
    
    def widget(self):
        """Should return the widget where the actions should be added to."""
        pass
        
    def client(self):
        """Should return the object that can further process our actions.
        
        Most times this will be a kateshell.shortcut.ShortcutClientBase instance.
        
        It should have the following methods:
        - actionTriggered(name)
        - populateAction(name, action)
        
        """
        pass
        
    def addAction(self, name):
        """(Internal) Create a new action with name name.
        
        If existing, return the existing action.
        
        """
        action = self._collection.action(name)
        if not action:
            action = self._collection.addAction(name)
            action.setShortcutContext(self.shortcutContext)
            action.triggered.connect(lambda: self.client().actionTriggered(name))
        return action
    
    def actionCollection(self):
        """Returns the action collection, populated with texts and icons."""
        for action in self._collection.actions()[:]:
            if action.shortcut().isEmpty():
                sip.delete(action)
            else:
                self.client().populateAction(action.objectName(), action)
        return self._collection


class SessionManager(object):
    """Manages sessions (basically lists of open documents).
    
    Sessions are stored in the appdata/sessions configfile, with each session
    in its own group.
    
    """
    sessionChanged = Signal()
    sessionAdded = Signal()
    
    def __init__(self, mainwin):
        self.mainwin = mainwin
        mainwin.aboutToClose.connect(self.shutdown)
        self._current = None
        self.sessionConfig = None
        self.reConfig()
        
    def reConfig(self):
        """Destroys and recreate the sessions KConfig object.
        
        Intended as a workaround for BUG 192266 in bugs.KDE.org.
        Otherwise deleting sessions does not work well.
        Call this after using deleteGroup.
        """
        if self.sessionConfig:
            self.sessionConfig.sync()
            sip.delete(self.sessionConfig)
        self.sessionConfig = KConfig("sessions", KConfig.NoGlobals, "appdata")
        
    def config(self, session=None):
        """Returns the config group for the named or current session.
        
        If session=False or 0, returns always the root KConfigGroup.
        If session=None (default), returns the group for the current session,
        if the current session is None, returns the root group.
        
        """
        if session:
            return self.sessionConfig.group(session)
        if session is None and self._current:
            return self.sessionConfig.group(self._current)
        return self.sessionConfig.group(None)
        
    def manage(self):
        """Opens the Manage Sessions dialog."""
        self.managerDialog().show()
        
    @cacheresult
    def managerDialog(self):
        return self.createManagerDialog()
        
    def createManagerDialog(self):
        """Override this to return a subclass of ManagerDialog."""
        import kateshell.sessions
        return kateshell.sessions.ManagerDialog(self)
        
    @cacheresult
    def editorDialog(self):
        """Returns a dialog to edit properties of the session."""
        return self.createEditorDialog()
    
    def createEditorDialog(self):
        """Override this to return a subclass of EditorDialog."""
        import kateshell.sessions
        return kateshell.sessions.EditorDialog(self)

    def switch(self, name):
        """Switches to the given session.
        
        Use None or "none" for the no-session state.
        If the given session does not exist, it is created from the current
        setup.
        
        """
        if name == "none":
            name = None
        self.autoSave()
        
        if name:
            if self.config(False).hasGroup(name):
                # existing group, close all the documents
                docs = self.mainwin.app.history[:] # copy
                for d in docs[::-1]: # in reversed order
                    if not d.queryClose():
                        return False
                for d in docs:
                    d.close(False)
                self.mainwin.loadDocumentList(self.config(name))
            else:
                # this group did not exist, create it
                self.addSession(name)
        self._current = name
        self.sessionChanged()
        return True
    
    def names(self):
        """Returns a list of names of all sessions."""
        names = self.sessionConfig.groupList()
        names.sort(key=naturalsort)
        return names
        
    def current(self):
        """Returns the name of the current session, or None if none."""
        return self._current
    
    def save(self):
        """Saves the current session."""
        if self._current is None:
            self.new()
        else:
            self.mainwin.saveDocumentList(self.config())
    
    def autoSave(self):
        """Saves the current session if the session wants to be autosaved."""
        if self._current and self.config().readEntry("autosave", True):
            self.save()
        self.config().sync()
    
    def shutdown(self):
        """Called on application exit."""
        self.config(False).writeEntry("lastused", self.current() or "none")
        self.autoSave()
        
    def restoreLastSession(self):
        """Restores the last saved session."""
        name = self.config(False).readEntry("lastused", "none")
        if name != "none":
            self.switch(name)
        
    def saveProperties(self, conf):
        """Save our state in a session group of QSessionManager."""
        conf.writeEntry("name", self._current or "none")
        conf.sync()
    
    def readProperties(self, conf):
        """Restore our state from a QSessionManager session group."""
        name = conf.readEntry("name", "none")
        self._current = None if name == "none" else name
        if self._current:
            self.sessionChanged()
    
    def new(self):
        """Prompts for a name for a new session.
        
        If the user enters a name and accepts the dialog, the session is
        created and switched to.
        
        """
        name = self.editorDialog().edit()
        if name:
            # switch there with the current document list
            self.mainwin.saveDocumentList(self.config(name))
            self._current = name
            self.sessionChanged()
            self.sessionAdded()

    def deleteSession(self, name):
        """Deletes the named session."""
        if name == self._current:
            self._current = None
            self.sessionChanged()
        self.config(name).deleteGroup()
        self.reConfig()
    
    def renameSession(self, old, new):
        """Renames a session.
        
        The document list is taken over but not the other settings.
        Both names must be valid session names, and old must exist.
        
        """
        oldConfig = self.config(old)
        newConfig = self.config(new)
        newConfig.writePathEntry("urls", oldConfig.readPathEntry("urls", []))
        newConfig.writeEntry("active", oldConfig.readEntry("active", 0))
        
        if old == self._current:
            self._current = new
            self.sessionChanged()
        self.config(old).deleteGroup()
        self.reConfig()
            
    def addSession(self, name):
        """Adds the named session, with the current document list."""
        if not self.config(False).hasGroup(name):
            self.mainwin.saveDocumentList(self.config(name))
        
    def basedir(self):
        """Returns the configured base directory for this session, if any."""
        if self._current:
            return self.config().readPathEntry("basedir", "")

