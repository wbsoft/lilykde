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

"""
A browser tool for the LilyPond documentation.
"""

import glob, os, sip
import HTMLParser

from PyQt4.QtCore import QObject, Qt, QUrl, QVariant, SIGNAL
from PyQt4.QtGui import QStackedWidget, QToolBar, QVBoxLayout, QWidget
from PyQt4.QtWebKit import QWebPage, QWebView

from PyKDE4.kdecore import KGlobal, KUrl, i18n
from PyKDE4.kdeui import KIcon, KMenu, KShortcut, KStandardAction, KStandardGuiItem
from PyKDE4.kio import KRun
from PyKDE4.ktexteditor import KTextEditor


docPrefixes = (
    '/usr/local/share/doc',
    '/usr/local/doc',
    '/usr/share/doc',
    '/usr/doc',
    )

docLocations = (
    'packages/lilypond*/html',
    'packages/lilypond*',
    'lilypond*/html',
    'lilypond*',
    )

def docHomeUrl():
    """
    Returns the configured or found url (as a string) where the LilyPond
    documentation is to be found.
    """
    url = config().readEntry("lilypond documentation", QVariant('')).toString()
    return unicode(url or findLocalDocIndex() or "http://lilypond.org/doc")

def findLocalDocIndex():
    """
    Tries to find LilyPond documentation in the local file system.
    """
    for p in docPrefixes:
        for l in docLocations:
            path = os.path.join(p, l, 'Documentation', 'index.html')
            files = glob.glob(path)
            if files:
                return files[-1]


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
        #self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        g = KStandardGuiItem.back()
        self.back = self.toolBar.addAction(g.icon(), g.text())
        self.back.setEnabled(False)
        g = KStandardGuiItem.forward()
        self.forward = self.toolBar.addAction(g.icon(), g.text())
        self.forward.setEnabled(False)
        self.home = self.toolBar.addAction(KIcon("go-home"), i18n("Home"))
        self.textLarger = self.toolBar.addAction(KIcon("zoom-in"), i18n("Larger text"))
        self.textSmaller = self.toolBar.addAction(KIcon("zoom-out"), i18n("Smaller text"))
        
        self.toolBar.addSeparator()
        
        # rellinks
        self.linkActions = {}   # all rellinks with their actions
        self.rellinks = {}      # links for the current view
        for name, icon, title in (
                # name, icon, default title
                ('start', 'arrow-left-double', i18n("First Page")),
                ('prev', 'arrow-left', i18n("Previous")),
                ('up', 'arrow-up', i18n("Up one level")),
                ('next', 'arrow-right', i18n("Next")),
                ('contents', 'view-table-of-contents-ltr', i18n("Table of contents")),
                ('index', 'arrow-right-double', i18n("Index")),
            ):
            self.linkActions[name] = a = self.toolBar.addAction(KIcon(icon), title)
            a.setEnabled(False)
            QObject.connect(a, SIGNAL("triggered()"), lambda name=name: self.slotRellink(name))

        # signals
        QObject.connect(self.doc, SIGNAL("completed()"), self.slotCompleted)
        QObject.connect(self.back, SIGNAL("triggered()"), self.slotBack)
        QObject.connect(self.forward, SIGNAL("triggered()"), self.slotForward)
        QObject.connect(self.home, SIGNAL("triggered()"), self.slotHome)
        QObject.connect(self.textLarger, SIGNAL("triggered()"), self.slotLarger)
        QObject.connect(self.textSmaller, SIGNAL("triggered()"), self.slotSmaller)
        
        QObject.connect(self.view, SIGNAL("urlChanged(QUrl)"), self.updateActions)
        QObject.connect(self.view, SIGNAL("loadFinished(bool)"), self.slotLoadFinished)
        self.view.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        QObject.connect(self.view.page(), SIGNAL("linkClicked(QUrl)"), self.openUrl)
        self.view.page().setForwardUnsupportedContent(True)
        QObject.connect(self.view.page(), SIGNAL("unsupportedContent(QNetworkReply*)"),
            self.slotUnsupported)
        
        # context menu:
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        QObject.connect(self.view, SIGNAL("customContextMenuRequested(QPoint)"),
            self.slotShowContextMenu)
        
        # load initial view.
        self.editFontSize = 0
        styleSheet = KGlobal.dirs().findResource("appdata", "lilydoc.css")
        if styleSheet:
            self.view.page().settings().setUserStyleSheetUrl(QUrl(styleSheet))
        self.stack.setCurrentWidget(self.view)
        self.slotHome()

    def openUrl(self, url):
        # handle .ly urls and load them read-only in KatePart
        if self.edit:
            sip.delete(self.edit)
            self.edit = None
        if url.path().endsWith('.ly'):
            self.edit = self.doc.createView(self)
            self.stack.addWidget(self.edit)
            # remember the view font size
            if self.editFontSize != 0:
                a = self.edit.actionCollection().action(
                    self.editFontSize > 0 and 
                    "view_inc_font_sizes" or "view_dec_font_sizes")
                if a:
                    for dummy in range(abs(self.editFontSize)):
                        a.trigger()
            # make backspace go out
            a = self.edit.actionCollection().action("backspace")
            if a:
                QObject.connect(a, SIGNAL("triggered()"), self.slotBack)
            self.doc.openUrl(KUrl(url))
            self.stack.setCurrentWidget(self.edit)
            self.forward.setEnabled(False)
            self.disableLinkActions()
        else:
            self.view.load(url)

    def updateActions(self):
        self.back.setEnabled(self.view.history().canGoBack())
        self.forward.setEnabled(bool(
            self.view.history().canGoForward() or self.edit))
    
    def updateLinkActions(self):
        for name, action in self.linkActions.iteritems():
            enable = name in self.rellinks and self.rellinks[name][1].isValid()
            action.setEnabled(enable)
            action.setToolTip(enable and self.rellinks[name][0] or '')
    
    def disableLinkActions(self):
        for action in self.linkActions.itervalues():
            action.setEnabled(False)
            action.setToolTip('')
            
    def slotRellink(self, name):
        if name in self.rellinks:
            url = self.rellinks[name][1]
            if url.isValid():
                self.openUrl(url)
    
    def slotBack(self):
        if self.stack.currentWidget() == self.edit:
            self.stack.setCurrentWidget(self.view)
            self.forward.setEnabled(True)
            self.updateLinkActions()
            self.back.setEnabled(self.view.history().canGoBack())
        elif self.view.history().canGoBack():
            self.view.back()
        
    def slotForward(self):
        if self.stack.currentWidget() == self.view:
            if self.view.history().canGoForward():
                self.view.forward()
            elif self.edit:
                self.stack.setCurrentWidget(self.edit)
                self.disableLinkActions()
                self.back.setEnabled(True)
                self.forward.setEnabled(False)
    
    def slotHome(self):
        self.openUrl(QUrl(docHomeUrl()))
    
    def slotLoadFinished(self, success):
        # Called when the HTML doc has loaded.
        # Parse HTML and display link rel='' buttons
        if success:
            html = unicode(self.view.page().mainFrame().toHtml())
            self.rellinks = RellinksParser(html, self.view.url()).links()
            self.updateLinkActions()
    
    def slotCompleted(self):
        # called when the ktexteditor document has loaded.
        # we then jump to the start of the relevant snippet
        # looking for "% ly snippet"
        iface = self.doc.searchInterface()
        if iface:
            d = self.doc.documentRange()
            r = iface.searchText(d, "% ly snippet")[0]
            if r.isValid():
                self.edit.setCursorPosition(d.end())
                self.edit.setCursorPosition(r.start())
                
    def slotLarger(self):
        """ Enlarge text """
        if self.stack.currentWidget() == self.view:
            size = self.view.textSizeMultiplier()
            self.view.setTextSizeMultiplier(size * 1.1)
        elif self.edit:
            a = self.edit.actionCollection().action("view_inc_font_sizes")
            if a:
                a.trigger()
                self.editFontSize += 1
                
    def slotSmaller(self):
        """ Make text smaller """
        if self.stack.currentWidget() == self.view:
            size = self.view.textSizeMultiplier()
            self.view.setTextSizeMultiplier(size / 1.1)
        elif self.edit:
            a = self.edit.actionCollection().action("view_dec_font_sizes")
            if a:
                a.trigger()
                self.editFontSize -= 1
        
    def slotUnsupported(self, reply):
        """ Called when the webview opens a non-HTML document. """
        self.slotNewWindow(reply.url())
            
    def slotShowContextMenu(self, pos):
        hit = self.view.page().currentFrame().hitTestContent(pos)
        menu = KMenu()
        if hit.linkUrl().isValid():
            a = self.view.pageAction(QWebPage.CopyLinkToClipboard)
            a.setIcon(KIcon("edit-copy"))
            a.setText(i18n("Copy &Link"))
            menu.addAction(a)
            menu.addSeparator()
            a = menu.addAction(KIcon("window-new"), i18n("Open Link in &New Window"))
            QObject.connect(a, SIGNAL("triggered()"),
                lambda url=hit.linkUrl(): self.slotNewWindow(url))
        else:
            if hit.isContentSelected():
                a = self.view.pageAction(QWebPage.Copy)
                a.setIcon(KIcon("edit-copy"))
                a.setText(i18n("&Copy"))
                menu.addAction(a)
                menu.addSeparator()
            a = menu.addAction(KIcon("window-new"), i18n("Open Document in &New Window"))
            QObject.connect(a, SIGNAL("triggered()"),
                lambda url=self.view.url(): self.slotNewWindow(url))
        if len(menu.actions()):
            menu.exec_(self.view.mapToGlobal(pos))
    
    def slotNewWindow(self, url):
        """ Open url in new window """
        sip.transferto(KRun(KUrl(url), self), None) # C++ will delete it



class RellinksParser(HTMLParser.HTMLParser):
    """
    Parses a string of HTML for the <link rel=...> tags in the HTML header.
    The dictionary with links is returned by the links() method.
    """
    def __init__(self, html, url):
        HTMLParser.HTMLParser.__init__(self)
        self._url = url
        self._links = {}
        self._finished = False
        # Don't feed the whole document, just quit when the
        # HTML header is parsed.
        try:
            while html and not self._finished:
                self.feed(html[:1024])
                html = html[1024:]
        except HTMLParser.HTMLParseError:
            pass

    def links(self):
        """
        Returns the found links as a dictionary. The key is the rel attribute,
        the value a tuple (title, QUrl).
        """
        return self._links
        
    def handle_starttag(self, tag, attrs):
        if tag == 'link':
            get = dict(attrs).get
            rel, href, title = get('rel', ''), get('href', ''), get('title', '')
            url = self._url.resolved(QUrl(href))
            self._links[rel] = (title, url)
            
    def handle_endtag(self, tag):
        if tag == 'head':
            self._finished = True


# Easily get our global config
def config(group="preferences"):
    return KGlobal.config().group(group)
    
  