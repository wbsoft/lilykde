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

import os, sip, weakref

from PyQt4.QtCore import QEvent, QTimer, Qt, SLOT, pyqtSignature
from PyQt4.QtGui import (
    QAction, QActionGroup, QDialog, QKeySequence, QLabel, QPixmap, QSplitter,
    QStackedWidget, QTabBar, QVBoxLayout, QWidget)
from PyKDE4.kdecore import KGlobal, KPluginLoader, KToolInvocation, KUrl, i18n
from PyKDE4.kdeui import (
    KAction, KActionCollection, KActionMenu, KDialog, KEditToolBar, KHBox,
    KIcon, KKeySequenceWidget, KMenu, KMessageBox, KMultiTabBar, KShortcut,
    KShortcutsDialog, KShortcutsEditor, KStandardAction, KStandardGuiItem,
    KToggleFullScreenAction, KVBox)
from PyKDE4.kparts import KParts
from PyKDE4.ktexteditor import KTextEditor
from PyKDE4.kio import KEncodingFileDialog

from signals import Signal


# Easily get our global config
def config(group="kateshell"):
    return KGlobal.config().group(group)


Top = KMultiTabBar.Top
Right = KMultiTabBar.Right
Bottom = KMultiTabBar.Bottom
Left = KMultiTabBar.Left


class MainWindow(KParts.MainWindow):
    """
    An editor main window.
    
    Emits the following (Python) signals:
    - currentDocumentChanged(Document) if the active document changes or its url.
    - aboutToClose() when the window will be closed.
    """
    def __init__(self, app):
        KParts.MainWindow.__init__(self)
        self.app = app
        self._currentDoc = None
        self.docks = {}
        self.tools = {}
        self.currentDocumentChanged = Signal()
        self.aboutToClose = Signal()
        
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
        s.setSizes((100, 400, 400))
        
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
        self.show()
        app.documentCreated.connect(self.addToRecentFiles)
        app.documentMaterialized.connect(self.addDocument)
        app.activeChanged.connect(self.setCurrentDocument)
        app.documentClosed.connect(self.removeDocument)
        
    def setupActions(self):
        self.act('file_new', KStandardAction.New, self.newDocument)
        self.act('file_open', KStandardAction.Open, self.openDocument)
        self.act('file_close', KStandardAction.Close,
            lambda: self.app.activeDocument().close())
        self.act('file_save', KStandardAction.Save,
            lambda: self.app.activeDocument().save())
        self.act('file_save_as', KStandardAction.SaveAs,
            lambda: self.app.activeDocument().saveAs())
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
        menu = a.menu()
        def populate():
            menu.clear()
            for tool in self.tools.itervalues():
                menu.addSeparator()
                menu.addAction(tool.action())
                tool.addMenuActions(menu)
        menu.aboutToShow.connect(populate)

    def setupTools(self):
        """
        Implement this to create the Tool instances. This is called before the
        ui.rc file s loaded, so the user can configure the keyboard shortcuts
        for the tools.
        """
        pass
    
    def setupGeneratedMenus(self):
        """ This should setup menus that are generated on show. """
        # Set up the documents menu so that it shows all open documents.
        docMenu = self.factory().container("documents", self)
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
        docMenu.aboutToShow.connect(populateDocMenu)
        
    def act(self, name, texttype, func,
            icon=None, tooltip=None, whatsthis=None, key=None):
        """ Create an action and add it to own actionCollection """
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
        """
        Decorator to add a function to an action.
        The name of the function becomes the name of the action.
        """
        def decorator(func):
            self.act(func.func_name, texttype, func, icon, tooltip, whatsthis, key)
            return func
        return decorator
        
    def onSelAction(self, texttype, icon=None, tooltip=None, whatsthis=None, key=None,
                    warn=True, keepSelection=True):
        """
        Decorator to add a function that is run on selected text to an action.
        The name of the function becomes the name of the action.
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
        self.viewStack.addWidget(doc.view)
        
    def removeDocument(self, doc):
        self.viewStack.removeWidget(doc.view)
        if doc is self._currentDoc:
            self.guiFactory().removeClient(doc.view)
            self._currentDoc = None
    
    def view(self):
        if self._currentDoc:
            return self._currentDoc.view
    
    def currentDocument(self):
        return self._currentDoc
    
    def slotUrlChanged(self, doc=None):
        self.addToRecentFiles(doc)
        self.currentDocumentChanged(doc or self._currentDoc)

    def updateCaption(self):
        doc = self.currentDocument()
        name = self.showPath.isChecked() and doc.prettyUrl() or doc.documentName()
        if len(name) > 72:
            name = '...' + name[-69:]
        if doc.isModified():
            self.setCaption("{0} [{1}]".format(name, i18n("modified")))
            self.sb_modified.setPixmap(KIcon("document-save").pixmap(16))
        else:
            self.setCaption(name)
            self.sb_modified.setPixmap(QPixmap())
    
    def updateStatusBar(self):
        doc = self.currentDocument()
        pos = doc.view.cursorPositionVirtual()
        line, col = pos.line()+1, pos.column()
        self.sb_linecol.setText(i18n("Line: %1 Col: %2", line, col))
        self.sb_insmode.setText(doc.view.viewMode())

    def updateSelection(self):
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
        """ Opens a window to edit the keyboard shortcuts """
        dlg = KShortcutsDialog(KShortcutsEditor.AllActions,
            KShortcutsEditor.LetterShortcutsDisallowed, self)
        for name, collection in self.allActionCollections():
            dlg.addCollection(collection, name)
        dlg.configure()
    
    def allActionCollections(self):
        """
        Yields all KActionCollections that need to be checked if the user
        wants to alter a keyboard shortcut.
        
        Each item is a two-tuple (name, KActionCollection).
        """
        yield KGlobal.mainComponent().aboutData().programName(), self.actionCollection()
        if self.view():
            yield None, self.view().actionCollection()
            
    def editToolbars(self):
        """ Opens a window to edit the toolbar(s) """
        conf = config("MainWindow")
        self.saveMainWindowSettings(conf)
        dlg = KEditToolBar(self.guiFactory(), self)
        def newToolbarConfig():
            self.applyMainWindowSettings(conf)
            self.setupGeneratedMenus()
        dlg.newToolbarConfig.connect(newToolbarConfig)
        dlg.exec_()

    def newDocument(self):
        """ Create a new empty document """
        self.app.createDocument().setActive()
        
    def openDocument(self):
        """ Open an existing document. """
        res = KEncodingFileDialog.getOpenUrlsAndEncoding(
            self.app.defaultEncoding,
            self.currentDocument().url().url() or self.app.defaultDirectory(),
            '\n'.join(self.app.fileTypes + ["*|" + i18n("All Files")]),
            self, i18n("Open File"))
        docs = [self.app.openUrl(url, res.encoding)
                for url in res.URLs if not url.isEmpty()]
        if docs:
            docs[-1].setActive()
    
    def addToRecentFiles(self, doc=None):
        """ Add url of document to recently opened files. """
        doc = doc or self.currentDocument()
        if doc:
            url = doc.url()
            if not url.isEmpty() and url not in self.openRecent.urls():
                self.openRecent.addUrl(url)
    
    @pyqtSignature("KUrl")
    def slotOpenRecent(self, url):
        """ Called by the open recent files action """
        self.app.openUrl(url).setActive()

    def queryClose(self):
        """ Quit the application, also called by closing the window """
        # First, close the modified documents, if any. (This way, if the user
        # cancels the first close dialog, all documents are still there.)
        unmodified = []
        for d in self.app.history[::-1]: # iterate over a copy, current first
            if d.isModified():
                d.setActive()
                if not d.close(True):
                    return False # cancelled
            else:
                unmodified.append(d)
        # Then close the unmodified documents. We keep this list ourselves,
        # because MainApp always creates a new document if the last one is
        # closed. This way we at least prevent app from creating a new document
        # twice.
        for d in unmodified:
            d.close(False)
        # save some settings
        self.saveSettings()
        self.aboutToClose()
        return True
        
    def loadSettings(self):
        """ Load some settings from our configfile. """
        self.openRecent.loadEntries(config("recent files"))
        self.showPath.setChecked(config().readEntry("show full path", False))
        self.showTabs.setChecked(config().readEntry("show tabs", True))
        self.viewTabs.setVisible(self.showTabs.isChecked())

    def saveSettings(self):
        """ Store settings in our configfile. """
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
    """
    The tab bar above the document editor view, used to switch
    documents.
    """
    def __init__(self, mainwin):
        QTabBar.__init__(self)
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
        
    def contextMenuEvent(self, ev):
        """ Called when the right mouse button is clicked on the tab bar. """
        tab = self.tabAt(ev.pos())
        if tab == -1:
            return
        menu = KMenu()
        self.addMenuActions(menu, self.docs[tab])
        menu.exec_(ev.globalPos())

    def addMenuActions(self, menu, doc):
        """
        Populate the menu with actions relevant for the document.
        """
        g = KStandardGuiItem.save()
        a = menu.addAction(g.icon(), g.text())
        a.triggered.connect(doc.save)
        g = KStandardGuiItem.saveAs()
        a = menu.addAction(g.icon(), g.text())
        a.triggered.connect(doc.saveAs)
        menu.addSeparator()
        g = KStandardGuiItem.close()
        a = menu.addAction(g.icon(), g.text())
        a.triggered.connect(doc.close)
        

class TabBar(KMultiTabBar):
    """
    Our own tabbar with some nice defaults.
    """
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
        tab.setToolTip("<b>{0}</b><br/>{1}".format(tool.title(),
            i18n("Right-click for tab options")))
        tab.setContextMenuPolicy(Qt.CustomContextMenu)
        tab.clicked.connect(tool.toggle)
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
    """
    A dock where tools can be added to.
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
        """
        Only to be called by tool.show().
        Call tool.show() to make it active.
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
        """
        Only to be called by tool.hide().
        Call tool.hide() to make it inactive.
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
    """
    A QDialog that (re)docks itself when closed.
    """
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
    """
    A Tool, that can be docked or undocked in/from the MainWindow.
    Can be subclassed.
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
        """
        Called when our action is triggered.
        Default behaviour is to toggle the visibility of our tool.
        Override this to implement other behaviour when our action is called
        (e.g. focus instead of hide).
        """
        self.toggle()
        
    def materialize(self):
        if self.widget is None:
            self.widget = self.factory()
    
    def factory(self):
        """
        Should return this Tool's widget when it must become visible.
        I you didn't supply a widget on init, you must override this method.
        """
        return QWidget()
        
    def delete(self):
        """ Completely remove our tool """
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
        """ Hide our tool """
        if self._docked:
            self._active = False
            self._dock.hideTool(self)
            view = self.mainwin.view()
            if view:
                view.setFocus()

    def toggle(self):
        if self._docked:
            if self._active:
                self.hide()
            else:
                self.show()

    def isActive(self):
        return self._active
    
    def isDocked(self):
        return self._docked
        
    def setDock(self, place):
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
        """
        Show a popup menu to manipulate this tool.
        """
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
        """
        Use this to add your own actions to a tool menu.
        """
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
        """
        You can implement this in your subclass to read additional config data.
        """
        pass
    
    def writeConfig(self, conf):
        """
        You can implement this in your subclass to write additional config data.
        """
        pass
    
    def help(self):
        KToolInvocation.invokeHelp(self.helpAnchor, self.helpAppName)


class KPartTool(Tool):
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
    """
    Manages user-defined keyboard shortcuts.
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
        """
        Should return the widget where the actions should be added to.
        """
        pass
        
    def client(self):
        """
        Should return the object that can further process our actions.
        
        Most times this will be a kateshell.shortcut.ShortcutClientBase instance.
        
        It should have the following methods:
        - actionTriggered(name)
        - populateAction(name, action)
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
            action.triggered.connect(lambda: self.client().actionTriggered(name))
        return action
    
    def actionCollection(self):
        """
        Returns the action collection, fully populated with texts and
        icons.
        """
        for action in self._collection.actions()[:]:
            if action.shortcut().isEmpty():
                self.removeShortcut(action.objectName())
            else:
                self.client().populateAction(action.objectName(), action)
        return self._collection


