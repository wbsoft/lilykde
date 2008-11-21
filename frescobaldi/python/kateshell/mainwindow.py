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


Top = KMultiTabBar.Top
Right = KMultiTabBar.Right
Bottom = KMultiTabBar.Bottom
Left = KMultiTabBar.Left


class MainWindow(KParts.MainWindow):
    def __init__(self, app):
        super(MainWindow, self).__init__()
        self.app = app
        self._currentDoc = None
        self.docks = {}

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
        
        tab_top = TabBar(Top, v)
        s1 = QSplitter(Qt.Vertical, v)
        
        self.docks[Top] = Dock(s1, tab_top, "go-up", i18n("Top Sidebar"))
        s1.addWidget(self.docks[Top])
        self.viewPlace = QStackedWidget(s1)
        s1.addWidget(self.viewPlace)
        self.docks[Bottom] = Dock(s1, tab_bottom, "go-down", i18n("Bottom Sidebar"))
        s1.addWidget(self.docks[Bottom])
       
        self.resize(500,400) # FIXME: save window size and set reasonable default
        self.show()
        listeners[app.activeChanged].append(self.showDoc)
        listeners[app.activeChanged].append(self.updateCaption)
        listeners[app.activeChanged].append(self.updateStatusBar)


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
        
        #self.setXMLFile("frescobaldiui.rc")
        self.createShellGUI(True)

        # Documents menu
        self.docMenu = self.factory().container("documents", self)
        self.docGroup = QActionGroup(self.docMenu)
        self.docGroup.setExclusive(True)
        QObject.connect(self.docMenu, SIGNAL("aboutToShow()"),
            self.populateDocMenu)
        QObject.connect(self.docGroup, SIGNAL("triggered(QAction*)"),
            lambda a: a.doc.setActive())
        
        # test
        Tool(self, "test", i18n("Test"), "document-properties")
        

    def showDoc(self, doc):
        if self._currentDoc:
            listeners[self._currentDoc.updateCaption].remove(self.updateCaption)
            listeners[self._currentDoc.updateStatus].remove(self.updateStatusBar)
            self.guiFactory().removeClient(self._currentDoc.view)
        self._currentDoc = doc
        self.guiFactory().addClient(doc.view)
        self.viewPlace.setCurrentWidget(doc.view)
        listeners[doc.updateCaption].append(self.updateCaption)
        listeners[doc.updateStatus].append(self.updateStatusBar)
        doc.view.setFocus()

    def addDoc(self, doc):
        self.viewPlace.addWidget(doc.view)
        
    def removeDoc(self, doc):
        self.viewPlace.removeWidget(doc.view)
        if doc is self._currentDoc:
            self.guiFactory().removeClient(doc.view)
            self._currentDoc = None
    
    def view(self):
        if self._currentDoc:
            return self._currentDoc.view

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
            self.app.defaultEncoding, QString(),
            '\n'.join(self.app.fileTypes + ["*|%s" % i18n("All Files")]),
            self, i18n("Open File"))
        for url in res.URLs:
            if url != '':
                self.app.openUrl(url.url(), res.encoding)

    def queryClose(self):
        """ Quit the application, also called by closing the window """
        for d in self.app.documents[:]: # iterate over a copy
            if d.isModified():
                d.setActive()
            if not d.close(True):
                return False
        return True


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
        self._tabs = {}
        self._id = 0    # to number tabs 
        
    def addTool(self, tool):
        self._id += 1
        self.appendTab(tool.icon(), self._id, tool.title())
        self._tabs[tool] = self._id
        tab = self.tab(self._id)
        tab.setFocusPolicy(Qt.NoFocus)
        QObject.connect(tab, SIGNAL("clicked()"), tool.toggle)
        tab.installEventFilter(self)

    def removeTool(self, tool):
        self.removeTab(self._tabs[tool])
        del self._tabs[tool]
        
    def showTool(self, tool):
        self.tab(self._tabs[tool]).setState(True)
        
    def hideTool(self, tool):
        self.tab(self._tabs[tool]).setState(False)
        
    def updateState(self, tool):
        tab = self.tab(self._tabs[tool])
        tab.setIcon(tool.icon())
        tab.setText(tool.title())

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.ContextMenu:
            for tool, _id in self._tabs.iteritems():
                if obj is self.tab(_id):
                    tool.contextMenu().popup(ev.globalPos())
                    return True
        return False


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
        self.tools = []          # a list of the tools we host
        self._currentTool = None # the currently active tool, if any
        self.hide() # by default

    def addTool(self, tool):
        """ Add a tool to our tabbar, save dock and tabid in the tool """
        if tool.widget:
            QStackedWidget.addWidget(self, tool.widget)
        self.tabbar.addTool(tool)
        self.tools.append(tool)
        if tool.isActive():
            self.showTool(tool)

    def removeTool(self, tool):
        if tool not in self.tools:
            return
        if tool.widget:
            QStackedWidget.removeWidget(self, tool.widget)
        self.tabbar.removeTool(tool)
        self.tools.remove(tool)
        if tool is self._currentTool:
            self._currentTool = None
            self.hide()
        
    def showTool(self, tool):
        """
        Only to be called by tool.show().
        Call tool.show() to make it active.
        """
        if tool not in self.tools or tool is self._currentTool:
            return
        if not tool.widget:
            tool.materialize()
            QStackedWidget.addWidget(self, tool.widget)
        QStackedWidget.setCurrentWidget(self, tool.widget)
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
        self.tool = tool
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        if tool.dialogSize:
            self.resize(*tool.dialogSize)
        tool.widget.setParent(self)
        self.updateState()
    
    def show(self):
        QDialog.show(self)
        if self.tool.dialogPos:
            self.move(*self.tool.dialogPos)
        
    def done(self, r):
        self.tool.dialogSize = self.width(), self.height()
        self.tool.dialogPos = self.x(), self.y()
        self.tool.dock()
        QDialog.done(self, r)

    def updateState(self):
        title = KDialog.makeStandardCaption(self.tool.title(), self,
            KDialog.HIGCompliantCaption)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(self.tool.icon()))

    def keyPressEvent(self, e):
        if e.key() != Qt.Key_Escape:
            QDialog.keyPressEvent(self, e)


class Tool(object):
    """
    A Tool, that can be docked or undocked in/from the MainWindow.
    Can be subclassed.
    """
    allowedPlaces = Top, Right, Bottom, Left

    __instances = []
    
    def __init__(self, mainwin, name,
            title="", icon="", dock=Right,
            widget=None, factory=QWidget):
        self._active = False
        self._docked = True
        self._dock = None
        self._dialog = None
        self.dialogSize = None
        self.dialogPos = None

        self.mainwin = mainwin
        self.name = name
        self.widget = widget
        self.factory = factory
        self.setTitle(title)
        self.setIcon(icon)
        self.setDock(dock)
        Tool.__instances.append(self)
        
    def delete(self):
        """ Completely remove our tool """
        if self._docked:
            self._dock.removeTool(self)
            self._dock = None
        else:
            self._dialog.done(0)
        if self.widget:
            sip.delete(self.widget)
            self.widget = None
        if self._dialog:
            sip.delete(self._dialog)
            self._dialog = None
        Tool.__instances.remove(self)

    def show(self):
        """ Bring our tool into view. """
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
            self.mainwin.view().setFocus()

    def toggle(self):
        if self._docked:
            if self._active:
                self.hide()
            else:
                self.show()

    def isActive(self):
        return self._active
        
    def materialize(self):
        if self.widget is None:
            self.widget = self.factory()
    
    def setDock(self, place):
        dock = self.mainwin.docks.get(place, self.dock)
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
            self._dialog = DockDialog(self)
        self._dialog.show()

    def dock(self):
        """ Dock and close the dialog window """
        if self._docked:
            return
        self._docked = True
        self._dock.addTool(self)
        
    def icon(self):
        return self._icon
        
    def setIcon(self, icon):
        self._icon = icon and KIcon(icon).pixmap(16) or KIcon()
        self.updateState()

    def title(self):
        return self._title
    
    def setTitle(self, title):
        self._title = title
        self.updateState()
            
    def updateState(self):
        if self._docked:
            if self._dock:
                self._dock.updateState(self)
        else:
            self._dialog.updateState()
            
    def contextMenu(self):
        """
        Return a popup menu to manipulate this tool
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
                QObject.connect(a, SIGNAL("triggered()"),
                    lambda place=place: self.setDock(place))
            m.addSeparator()
        a = m.addAction(KIcon("tab-detach"), i18n("Undock"))
        QObject.connect(a, SIGNAL("triggered()"), self.undock)
        
        return m
        
