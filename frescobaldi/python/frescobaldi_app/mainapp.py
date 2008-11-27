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

import os, re, sip
from dbus.service import method

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kparts import KParts

import kateshell.app, kateshell.mainwindow
from kateshell.mainwindow import listeners


class MainApp(kateshell.app.MainApp):
    """ A Frescobaldi application instance """
    
    defaultEncoding = 'UTF-8'
    defaultHighlightingMode = "LilyPond"
    fileTypes = ["*.ly *.ily *.lyi|%s" % i18n("LilyPond files")]
    
    def __init__(self, servicePrefix):
        kateshell.app.MainApp.__init__(self, servicePrefix)
        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = self.serviceName + '/MainApp'
        print "TEXTEDIT_DBUS_PATH=%s" % os.environ["TEXTEDIT_DBUS_PATH"]#DEBUG

    def openUrl(self, url, encoding=None):
        # The URL can be python string, dbus string or QString
        url = unicode(url)
        nav = False
        if url.startswith("textedit:"):
            m = re.match(r"textedit:(/[^/].*):(\d+):(\d+):(\d+)$", url)
            if m:
                # We have a valid textedit:/ uri.
                # (KDE deletes the first two slashes)
                path, (line, char, col) = m.group(1), map(int, m.group(2,3,4))
                url = "file://" + path
                nav = True
            else:
                url = re.sub("^textedit", "file", url)
        d = kateshell.app.MainApp.openUrl(self, url, encoding)
        if nav:
            d.setCursorPosition(line, col)
        return d

    @method("org.lilypond.TextEdit", in_signature='s', out_signature='b')
    def openTextEditUrl(self, url):
        """
        To be called by ktexteditservice (part of lilypond-kde4).
        Opens the specified textedit:// URL.
        """
        return bool(self.openUrl(url))

    def createMainWindow(self):
        """ use our own MainWindow """
        return MainWindow(self)

    def createDocument(self, url="", encoding=None):
        return Document(self, url, encoding)


class Document(kateshell.app.Document):
    """ Our own Document type with LilyPond-specific features """
    def hasUpdated(self, ext):
        """
        return true if this document has one or more LilyPond-generated
        outputs with the given extension that are up-to-date.
        """
        return True # FIXME implement
    

class MainWindow(kateshell.mainwindow.MainWindow):
    """ Our customized Frescobaldi MainWindow """
    def __init__(self, app):
        kateshell.mainwindow.MainWindow.__init__(self, app)
        
        KonsoleTool(self)
        self.pdfTool = PDFTool(self)
        self.pdfTool.openUrl(KUrl("file:///home/kde4dev/test.pdf")) #DEBUG
        

class KonsoleTool(kateshell.mainwindow.Tool):
    """ A tool embedding a Konsole """
    def __init__(self, mainwin):
        self.part = None
        self._sync = False
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "konsole", i18n("Terminal"), "terminal",
            dock=kateshell.mainwindow.Bottom,
            factory = self.konsoleWidgetFactory)
        listeners[mainwin.app.activeChanged].append(self.sync)
            
    def konsoleWidgetFactory(self):
        if self.part:
            return
        factory = KPluginLoader("libkonsolepart").factory()
        self.part = factory.create(self.mainwin)
        if self.mainwin.currentDocument() and self.mainwin.currentDocument().url():
            url = self.mainwin.currentDocument().url()
        else:
            url = os.getcwd()
        self.part.openUrl(KUrl(url))
        QObject.connect(self.part, SIGNAL("destroyed()"), self.slotDestroyed)
        return self.part.widget()

    def show(self):
        kateshell.mainwindow.Tool.show(self)
        self.part.widget().setFocus()
        
    def hide(self):
        kateshell.mainwindow.Tool.hide(self)
        self.mainwin.view().setFocus()

    def sync(self, doc):
        if (self.part and self._sync
            and doc and doc.doc and not doc.doc.url().isEmpty()):
            # FIXME This does not work currently.
            self.part.openUrl(KUrl(doc.doc.url().directory()))

    def contextMenu(self):
        m = super(KonsoleTool, self).contextMenu()
        m.addSeparator()
        a = m.addAction(i18n("S&ynchronize Terminal with Current Document"))
        a.setCheckable(True)
        a.setChecked(self._sync)
        QObject.connect(a, SIGNAL("triggered()"), self.toggleSync)
        return m
        
    def toggleSync(self):
        self._sync = not self._sync

    def slotDestroyed(self):
        self.part = None
        self.widget = None
        if not sip.isdeleted(self.mainwin):
            if self._docked:
                self.hide()
            elif self._dialog:
                self._active = False
                self._dialog.done(0)
        
        
class PDFTool(kateshell.mainwindow.Tool):
    def __init__(self, mainwin):
        self.part = None
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "pdf", i18n("PDF Preview"), "application-pdf",
            dock=kateshell.mainwindow.Right,
            factory = self.okularWidgetFactory)
        listeners[mainwin.app.activeChanged].append(self.sync)
            
    def okularWidgetFactory(self):
        if self.part:
            return
        factory = KPluginLoader("okularpart").factory()
        self.part = factory.create(self.mainwin)
        return self.part.widget()
    
    def sync(self, doc):
        pass
    
    def openUrl(self, url):
        self.show()
        self.part.openUrl(url)
        