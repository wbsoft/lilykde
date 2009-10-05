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

import os, sip

from PyQt4.QtCore import QObject, Qt, QUrl, SIGNAL
from PyQt4.QtGui import QStackedWidget, QToolBar, QVBoxLayout, QWidget
from PyQt4.QtWebKit import QWebPage, QWebView

from PyKDE4.kdecore import KUrl, i18n
from PyKDE4.kdeui import KIcon, KStandardGuiItem
from PyKDE4.ktexteditor import KTextEditor


docPrefixes = (
    '/usr/local/share/doc',
    '/usr/local/doc',
    '/usr/share/doc',
    '/usr/doc',
    )
docLocations = (
    'packages/lilypond/html',
    'packages/lilypond',
    'lilypond/html',
    'lilypond',
    )

def findLocalDocIndex():
    for p in docPrefixes:
        for l in docLocations:
            i = os.path.join(p, l, 'Documentation', 'index.html')
            if os.path.exists(i):
                return i
    return "http://lilypond.org/doc"


class LilyDoc(QWidget):
    def __init__(self, tool):
        QWidget.__init__(self)
        self.mainwin = tool.mainwin
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toolBar = QToolBar(self)
        layout.addWidget(self.toolBar)
        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)
        
        # WebView
        self.view = QWebView(self.stack)
        self.stack.addWidget(self.view)
        
        # Kate Editor part
        self._editor = KTextEditor.EditorChooser.editor()
        self._editor.readConfig()
        self.doc = self._editor.createDocument(self)
        self.doc.setMode('LilyPond')
        self.doc.setEncoding('UTF-8')
        self.doc.setReadWrite(False)
        self.edit = None # we create the views later because of scrollbar issues
        
        # Toolbar, buttons
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        g = KStandardGuiItem.back()
        self.back = self.toolBar.addAction(g.icon(), g.text())
        self.back.setEnabled(False)
        g = KStandardGuiItem.forward()
        self.forward = self.toolBar.addAction(g.icon(), g.text())
        self.forward.setEnabled(False)
        self.home = self.toolBar.addAction(KIcon("go-home"), i18n("Home"))
        
        # signals
        QObject.connect(self.doc, SIGNAL("completed()"), self.slotCompleted)
        QObject.connect(self.back, SIGNAL("triggered()"), self.slotBack)
        QObject.connect(self.forward, SIGNAL("triggered()"), self.slotForward)
        QObject.connect(self.home, SIGNAL("triggered()"), self.slotHome)
        
        self.view.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        QObject.connect(self.view.page(), SIGNAL("linkClicked(QUrl)"), self.openUrl)
        
        # load initial view.
        self.homeUrl = QUrl(findLocalDocIndex())
        self.stack.setCurrentWidget(self.view)
        self.view.load(self.homeUrl)

    def openUrl(self, url):
        # handle .ly urls and load them read-only in KatePart
        if self.edit:
            sip.delete(self.edit)
            self.edit = None
        if url.path().endsWith('.ly'):
            self.edit = self.doc.createView(self)
            self.stack.addWidget(self.edit)
            self.doc.openUrl(KUrl(url))
            self.stack.setCurrentWidget(self.edit)
        else:
            self.view.load(url)
        self.back.setEnabled(True)
        self.forward.setEnabled(False)

    def slotBack(self):
        if self.stack.currentWidget() == self.edit:
            self.stack.setCurrentWidget(self.view)
        elif self.view.history().canGoBack():
            self.view.back()
        self.back.setEnabled(self.view.history().canGoBack())
        self.forward.setEnabled(True)
        
    def slotForward(self):
        if self.stack.currentWidget() == self.view:
            if self.view.history().canGoForward():
                self.view.forward()
                self.back.setEnabled(True)
                self.forward.setEnabled(bool(
                    self.view.history().canGoForward() or self.edit))
            elif self.edit:
                self.stack.setCurrentWidget(self.edit)
                self.back.setEnabled(True)
                self.forward.setEnabled(False)
    
    def slotHome(self):
        self.openUrl(self.homeUrl)
        
    def slotCompleted(self):
        # called when the ktexteditor document has loaded.
        # we then jump to the start of the relevant snippet
        # looking for "% ly snippet"
        iface = self.doc.searchInterface()
        if iface:
            r = iface.searchText(self.doc.documentRange(), "% ly snippet")[0]
            if r.isValid():
                self.edit.setCursorPosition(r.start())
                
                
            
        