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

import glob, os, re, sip
import HTMLParser

from PyQt4.QtCore import QEvent, QObject, Qt, QUrl, QVariant, SIGNAL
from PyQt4.QtGui import QGridLayout, QStackedWidget, QToolBar, QWidget
from PyQt4.QtWebKit import QWebPage, QWebView

from PyKDE4.kdecore import KGlobal, KUrl, i18n
from PyKDE4.kdeui import KAction, KIcon, KMenu, KLineEdit, KStandardGuiItem
from PyKDE4.kio import KIO, KRun
from PyKDE4.ktexteditor import KTextEditor

from signals import Signal

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
        layout = QGridLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toolBar = QToolBar(self)
        layout.addWidget(self.toolBar, 0, 0)
        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack, 1, 0, 1, 2)
        
        # WebView
        self.view = QWebView(self.stack)
        self.stack.addWidget(self.view)
        
        # Kate Editor part is loaded on demand
        self.doc = None
        self.edit = None # we create the views later because of scrollbar issues
        
        # Toolbar, buttons
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
        
        # search text entry
        self.search = KLineEdit()
        self.toolBar.addWidget(self.search)
        self.search.setClearButtonShown(True)
        self.search.setClickMessage(i18n("Search..."))
        
        # signals
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
        
        QObject.connect(self.search, SIGNAL("textEdited(QString)"), self.slotSearch)
        QObject.connect(self.search, SIGNAL("returnPressed()"), self.slotSearch)
        
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
    
    def keyPressEvent(self, ev):
        if ev.text() == "/":
            self.search.setFocus()
        elif ev.key() == Qt.Key_Escape:
            # focus ourselves
            if self.stack.currentWidget() == self.edit:
                self.edit.setFocus()
            else:
                self.view.setFocus()
        else:
            QWidget.keyPressEvent(self, ev)
            
    def createEditView(self):
        if self.doc is None:
            editor = KTextEditor.EditorChooser.editor()
            editor.readConfig()
            self.doc = editor.createDocument(self)
            self.doc.setMode('LilyPond')
            self.doc.setEncoding('UTF-8')
            self.doc.setReadWrite(False)
            QObject.connect(self.doc, SIGNAL("completed()"), self.slotCompleted)
        self.edit = self.doc.createView(self)
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
        
    def openUrl(self, url):
        # handle .ly urls and load them read-only in KatePart
        if self.edit:
            sip.delete(self.edit)
            self.edit = None
        if url.path().endsWith('.ly'):
            self.createEditView()
            self.stack.addWidget(self.edit)
            self.doc.openUrl(KUrl(url))
            self.stack.setCurrentWidget(self.edit)
            self.forward.setEnabled(False)
            self.back.setEnabled(True)
            self.disableLinkActions()
        else:
            self.view.load(url)

    def updateActions(self):
        self.search.clear()
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
            self.search.clear()
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
                self.search.clear()
    
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

    def slotSearch(self):
        text = self.search.text()
        if self.stack.currentWidget() == self.view:
            self.view.page().findText(text, QWebPage.FindWrapsAroundDocument)
        elif self.edit:
            iface = self.doc.searchInterface()
            if text == "":
                self.edit.removeSelection()
            elif iface:
                docRange = self.doc.documentRange()
                if self.edit.selection():
                    selRange = self.edit.selectionRange()
                    if text == self.edit.selectionText():
                        cursor = selRange.end()
                    else:
                        cursor = selRange.start()
                else:
                    cursor = self.edit.cursorPosition()
                for searchRange in (
                        KTextEditor.Range(cursor, docRange.end()),
                        KTextEditor.Range(docRange.start(), cursor)):
                    r = iface.searchText(searchRange, text)[0]
                    if r.isValid():
                        self.edit.setCursorPosition(r.start())
                        self.edit.setSelection(r)
                        return


class HtmlParser(HTMLParser.HTMLParser):
    """
    Slightly altered from HTMLParser: feeds entityrefs to handle_data.
    """
    def handle_entityref(self, name):
        char = {
            'gt': '>',
            'lt': '<',
            'amp': '&',
            }.get(name)
        if char:
            self.handle_data(char)


class HeaderParser(HtmlParser):
    """
    Parses just the header or a piece of HTML. Subclass this.
    """
    def __init__(self, html):
        HtmlParser.__init__(self)
        self._finished = False
        # Don't feed the whole document, just quit when the
        # HTML header is parsed.
        try:
            while html and not self._finished:
                self.feed(html[:1024])
                html = html[1024:]
        except HTMLParser.HTMLParseError:
            pass
        
    def handle_endtag(self, tag):
        if tag == 'head':
            self._finished = True
        

class RellinksParser(HeaderParser):
    """
    Parses a string of HTML for the <link rel=...> tags in the HTML header.
    The dictionary with links is returned by the links() method.
    """
    def __init__(self, html, url):
        self._url = url
        self._links = {}
        HeaderParser.__init__(self, html)

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


class HttpEquivParser(HeaderParser):
    """
    Parses a piece of HTML, looking for META HTTP-EQUIV tag.
    """
    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            a = dict(attrs)
            http_equiv = a.get('http-equiv', '')
            content = a.get('content', '')
            if http_equiv and content:
                self.handle_http_equiv(http_equiv, content)

    def handle_http_equiv(self, http_equiv, content):
        """ Reimplement to do something with the META HTTP-EQUIV tag. """
        pass


class RedirectionParser(HttpEquivParser):
    """
    Parses a piece of HTML, looking for META HTTP-EQUIV redirects.
    """
    def __init__(self, html):
        self._redir = None
        HttpEquivParser.__init__(self, html)
        
    def handle_http_equiv(self, http_equiv, content):
        if http_equiv == "refresh" and '=' in content:
            self._redir = content.split('=', 1)[1].strip()
            self._finished = True # stop asap

    def redirection(self):
        """ Returns the redirection if found, else None. """
        return self._redir
            

class HtmlEncodingParser(HttpEquivParser):
    """
    Parses HTML and stores it in the right encoding.
    """
    def __init__(self, html, defaultEncoding='UTF-8'):
        self._encoding = defaultEncoding
        HttpEquivParser.__init__(self, html)
        self._html = html.decode(self._encoding, 'replace')
        
    def handle_http_equiv(self, http_equiv, content):
        if http_equiv == "Content-Type":
            m = re.search(r'\bcharset\s*=\s*(\S+)', content)
            if m:
                self._encoding = m.group(1)
                self._finished = True
                    
    def html(self):
        return self._html


class IndexParser(HtmlParser):
    """
    This class parses a LilyPond index. It supports the different types
    of HTML pages of LilyPond 2.10, 2.12 and 2.13.
    
    Subclass this for different indexes.
    """
    
    # html classname of the table or ul that forms the index.
    indexClass = ''
    
    def __init__(self, html):
        HtmlParser.__init__(self)
        self._parsing = False
        self._tableTag = None
        self.items = {}
        self.initLine()
        self.feed(html)
    
    def initLine(self):
        self._anchors = []
        self._titles = [None]
        
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self._parsing:
            if attrs.get('class') == self.indexClass:
                self._parsing = True
                self._tableTag = tag
            return
        elif tag == 'a' and 'href' in attrs:
            self._anchors.append(attrs['href'])
            self._titles.append('')
    
    def handle_data(self, data):
        if self._titles[-1] is not None:
            self._titles[-1] += data
    
    def handle_endtag(self, tag):
        if not self._parsing:
            return
        elif tag == self._tableTag:
            self._parsing = False
        elif tag == 'a':
            self._titles.append(None)
        elif tag in ('li', 'tr'):
            # end a line of items.
            if len(self._titles) == 5:
                code = self._titles[1].strip()
                # don't store index entries with spaces, we won't use them
                if " " not in code:
                    title = self._titles[3].strip()
                    self.items.setdefault(code, []).append((
                        code, self._anchors[0],
                        title, self._anchors[1]))
            self.initLine()
            

class NotationReferenceIndexParser(IndexParser):
    indexClass = 'index-ky'
    
class LearningManualIndexParser(IndexParser):
    indexClass = 'index-cp'
    

class HtmlLoader(object):
    """
    Tries to load an url using KIO and follows HTTP and HTML redirects.
    Sends the done(self) Python signal if done.
    """
    def __init__(self, url):
        self.done = Signal()
        self._html = None
        self.startJob(url)
    
    def startJob(self, url):
        self._url = KUrl(url)
        self._data = ''
        self._job = KIO.get(KUrl(url), KIO.NoReload, KIO.HideProgressInfo)
        QObject.connect(self._job, SIGNAL("data(KIO::Job*, QByteArray)"), self.slotData)
        QObject.connect(self._job, SIGNAL("redirection(KIO::Job*, KUrl)"), self.slotRedirection)
        QObject.connect(self._job, SIGNAL("result(KJob*)"), self.slotResult)
        self._job.start()
    
    def slotData(self, job, data):
        self._data += data
    
    def slotRedirection(self, job, url):
        self._data = ''
        self._url = KUrl(url)
        
    def slotResult(self, job):
        redir = RedirectionParser(str(self._data)).redirection()
        if redir:
            self.startJob(KUrl(self.resolveUrl(redir)))
        else:
            self.done(self)
        
    def url(self):
        return self._url
    
    def resolveUrl(self, url):
        return KUrl(self._url.resolved(KUrl(url)))
    
    def html(self):
        if self._html is None:
            self._html = HtmlEncodingParser(str(self._data)).html()
        return self._html

    def error(self):
        """
        Returns True if there was an error.
        Only call this after done(self) has been called.
        """
        return self._job.error() or self._job.isErrorPage()


class HtmlMultiLoader(object):
    """
    Loads the first URL of a list that succeeds.
    Calls done() when done with the correct Loader or with None.
    """
    def __init__(self, urls):
        self._urls = urls
        self.done = Signal()
        self.loadNext()
        
    def loadNext(self):
        if self._urls:
            self._loader = HtmlLoader(self._urls.pop(0))
            self._loader.done.connect(self.loaded)
        else:
            self.done(None)
            
    def loaded(self, loader):
        if loader.error():
            self.loadNext()
        else:
            self.done(loader)
        

class Index(object):
    """
    Encapsulates a loading, loaded or failed-to-load LilyPond help index.
    It expects a HtmlLoader that is loading the documentation start page,
    and a Tool that is the help browser tool (see kateshell/mainwindow).
    The attribute loaded = None: pending, True: loaded, False: failed.
    
    To be subclassed.
    """
    
    urls = []
    
    def __init__(self, loader, tool):
        self.loaded = None
        self.loadFinished = Signal()
        self._loader = loader
        self.tool = tool
        loader.done.connect(self._initialLoaderDone)
        
    def _initialLoaderDone(self, loader):
        if not loader.error():
            self._loader = HtmlMultiLoader(map(loader.resolveUrl, self.urls))
            self._loader.done.connect(self._multiLoadDone)
        else:
            self.loaded = False
            self.loadFinished(False)
            
    def _multiLoadDone(self, loader):
        if loader:
            self.url = loader.url()
            self.loaded = bool(self.parse(loader.html()))
        else:
            self.loaded = False # failed
        self.loadFinished(self.loaded)
        
    def parse(self, html):
        """
        Implement this to parse the loaded html.
        Should return True if the parsing succeeded and the results are usable.
        """
        return False
    
    def menuTitle(self):
        """
        Implement this to return a meaningful title for the menu.
        """
        pass
    
    def addMenuActionsWhenLoaded(self, menu, *args):
        if self.loaded is False:
            return # not available
        title = self.menuTitle()
        if title:
            menu.addTitle(title)
        if self.loaded:
            self.loadingAction = None
            self.addMenuActions(menu, *args)
        else:
            self.loadingAction = menu.addAction(i18n("Loading..."))
            def addHelp(success):
                try:
                    if success:
                        self.addMenuActions(menu, *args)
                        sip.delete(self.loadingAction)
                    else:
                        self.loadingAction.setText(i18n("Not available"))
                except RuntimeError:
                    pass # underlying C/C++ object has been deleted
            self.loadFinished.connect(addHelp)
    
    def addMenuActions(self, menu, *args):
        """ Implement this in your subclass. """
        pass
    
    def addMenuSeparator(self, menu):
        """
        Add a separator. Use this instead of menu.addSeparator, because
        different indexes may add entries asynchroneously to the same menu.
        """
        a = KAction(menu)
        a.setSeparator(True)
        menu.insertAction(self.loadingAction, a)
        
    def addMenuUrl(self, menu, title, url):
        """
        Adds an action to the menu with an url relative
        to the current command index. The Url opens in the help browser.
        
        Only call this if the loading was successful!
        """
        a = KAction(title, menu)
        menu.insertAction(self.loadingAction, a) 
        QObject.connect(a, SIGNAL("triggered()"),
            lambda: self.tool.openUrl(self.url.resolved(KUrl(url))))


class NotationReferenceIndex(Index):
    urls = (
        'user/lilypond/LilyPond-command-index',
        'user/lilypond/LilyPond-command-index.html',
        # from 2.13 on the url scheme changed slightly
        'notation/LilyPond-command-index',
        'notation/LilyPond-command-index.html',
        )
    
    def parse(self, html):
        try:
            self.items = NotationReferenceIndexParser(html).items
            return True
        except HTMLParser.HTMLParseError:
            return False
    
    def menuTitle(self):
        return i18n("Notation Reference")
        
    def addMenuActions(self, menu, text, column):
        tokens = []
        for m in re.finditer(
                r"(\\?("
                r"[a-z][A-Za-z]*(-[A-Za-z]+)*"
                r"|[-!',./:<=>?[()]"
                r"))(?![A-Za-z])", text):
            if m.start() <= column <= m.end():
                tokens.extend(m.group(1, 2))
                break
        for token in tokens:
            if token in self.items:
                for command, command_url, section, section_url in self.items[token]:
                    # each entry has cmdname, direct url, section title, section url
                    self.addMenuUrl(menu, command, command_url)
                    self.addMenuUrl(menu, section, section_url)
                    self.addMenuSeparator(menu)
                break
        self.addMenuUrl(menu, i18n("LilyPond Command Index"), self.url)
        
            
class LearningManualIndex(Index):
    urls = (
        'user/lilypond-learning/LilyPond-index',
        'user/lilypond-learning/LilyPond-index.html',
        # from 2.13 on the url scheme changed slightly
        'learning/LilyPond-index',
        'learning/LilyPond-index.html',
        )
    
    def parse(self, html):
        try:
            self.items = LearningManualIndexParser(html).items
            return True
        except HTMLParser.HTMLParseError:
            return False
    
    def menuTitle(self):
        return i18n("Learning Manual")
        
    def addMenuActions(self, menu, text, column):
        tokens = []
        for m in re.finditer(
                r"(\\?("
                r"[A-Za-z]+(-[A-Za-z]+)*" # also allow starting capitals
                r"|[-!',./:<=>?[()]"
                r"))(?![A-Za-z])", text):
            if m.start() <= column <= m.end():
                tokens.extend(m.group(1, 2))
                break
        for token in tokens:
            if token in self.items:
                for command, command_url, section, section_url in self.items[token]:
                    # each entry has cmdname, direct url, section title, section url
                    self.addMenuUrl(menu, command, command_url)
                    self.addMenuUrl(menu, section, section_url)
                    self.addMenuSeparator(menu)
                break
        self.addMenuUrl(menu, i18n("Learning Manual Index"), self.url)
        
            
class DocFinder(object):
    """
    Find and pre-parse LilyPond documentation.
    """
    def __init__(self, tool):
        loader = HtmlLoader(KUrl(docHomeUrl()))
        self.commandIndex = NotationReferenceIndex(loader, tool)
        self.learningIndex = LearningManualIndex(loader, tool)
            
    def addHelpMenu(self, contextMenu, text, column):
        if (self.commandIndex.loaded is False
            and self.learningIndex.loaded is False):
            return # no docs available
        menu = KMenu(i18n("LilyPond &Help"), contextMenu)
        menu.setIcon(KIcon("lilydoc"))
        contextMenu.addMenu(menu)
        self.learningIndex.addMenuActionsWhenLoaded(menu, text, column)
        self.commandIndex.addMenuActionsWhenLoaded(menu, text, column)



# Easily get our global config
def config(group="preferences"):
    return KGlobal.config().group(group)
    
  