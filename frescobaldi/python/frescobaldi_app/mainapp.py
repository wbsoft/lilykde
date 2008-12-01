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

    def openUrl(self, url, encoding=None):
        # The URL can be python string, dbus string or QString
        url = unicode(url)
        nav = False
        if url.startswith("textedit:"):
            m = re.match(r"textedit:/{,2}(/[^/].*):(\d+):(\d+):(\d+)$", url)
            if m:
                # We have a valid textedit:/ uri.
                path, (line, char, col) = m.group(1), map(int, m.group(2,3,4))
                url = "file://" + path
                nav = True
            else:
                # We can't open malformed textedit urls
                url = ""
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
        PDFTool(self)
        QuickInsertTool(self)

    def setupActions(self):
        super(MainWindow, self).setupActions()
        RhythmActions(self)
        

class RhythmActions(object):
    """
    Container containing actions for editing rhythms and their implementations
    """
    def __init__(self, win):
        def lazy(name):
            """ Lazy-load lilypond module only when action requested """
            def func():
                v, d = win.view(), win.view().document()
                if v.selection():
                    text = unicode(v.selectionText())
                    import ly.duration
                    # call the relevant module function and get the result
                    result = getattr(ly.duration, name)(text)
                    # TODO: keep selection on newly inserted text
                    d.startEditing()
                    v.removeSelectionText()
                    v.insertText(result)
                    d.endEditing()
                else:
                    pass  # TODO warn that text must be selected.
            return func
        win.act('durations_double', i18n("Double durations"), lazy("doubleDurations"),
            tooltip=i18n("Double all the durations in the selection."))
        win.act('durations_halve', i18n("Halve durations"), lazy("halveDurations"),
            tooltip=i18n("Halve all the durations in the selection."))
        win.act('durations_dot', i18n("Dot durations"), lazy("dotDurations"),
            tooltip=i18n("Add a dot to all the durations in the selection."))
        win.act('durations_undot', i18n("Undot durations"), lazy("undotDurations"),
            tooltip=i18n("Remove one dot from all the durations in the selection."))
        win.act('durations_remove_scaling', i18n("Remove scaling"), lazy("removeScaling"),
            tooltip=i18n("Remove all scaling (*n/m) from the durations in the "
                         "selection."))
        win.act('durations_remove', i18n("Remove durations"), lazy("removeDurations"),
            tooltip=i18n("Remove all durations from the selection."))
        win.act('durations_implicit', i18n("Make implicit"), lazy("makeImplicit"),
            tooltip=i18n("Make durations implicit (remove repeated durations)."))
        win.act('durations_explicit', i18n("Make explicit"), lazy("makeExplicit"),
            tooltip=i18n("Make durations explicit (add duration to every note, "
                         "even if it is the same as the preceding note)."))

    
class KonsoleTool(kateshell.mainwindow.KPartTool):
    """ A tool embedding a Konsole """
    _partlibrary = "libkonsolepart"
    
    def __init__(self, mainwin):
        self._sync = False
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "konsole", i18n("Terminal"), "terminal",
            dock=kateshell.mainwindow.Bottom)
        listeners[mainwin.app.activeChanged].append(self.sync)
            
    def partFactory(self):
        w = super(KonsoleTool, self).partFactory()
        if self.part:
            d = self.mainwin.currentDocument()
            url = d and d.url() or os.getcwd()
            self.openUrl(url)
        return w

    def show(self):
        super(KonsoleTool, self).show()
        if self.part:
            self.part.widget().setFocus()
        
    def hide(self):
        super(KonsoleTool, self).hide()
        self.mainwin.view().setFocus()

    def sync(self, doc):
        if (self.part and self._sync
            and doc and doc.doc and not doc.doc.url().isEmpty()):
            # FIXME This does not work currently.
            self.openUrl(doc.doc.url().directory())

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


class PDFTool(kateshell.mainwindow.KPartTool):
    _partlibrary = "okularpart"
    def __init__(self, mainwin):
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "pdf", i18n("PDF Preview"), "application-pdf",
            dock=kateshell.mainwindow.Right)
        listeners[mainwin.app.activeChanged].append(self.sync)
            
    def sync(self, doc):
        pass
    
    def contextMenu(self):
        m = super(PDFTool, self).contextMenu()
        if self.part:
            m.addSeparator()
            a = m.addAction(i18n("Show PDF Navigation Panel"))
            a.setCheckable(True)
            a.setChecked(self.part.actionCollection().action(
                "show_leftpanel").isChecked())
            QObject.connect(a, SIGNAL("triggered()"), lambda:
                self.part.actionCollection().action("show_leftpanel").toggle())
            a = m.addAction(i18n("Show PDF minibar"))
            a.setCheckable(True)
            w = self._okularMiniBar()
            a.setChecked(w.isVisibleTo(w.parent()))
            QObject.connect(a, SIGNAL("triggered()"), self.toggleMiniBar)
        return m
    
    def openUrl(self, url):
        self.show()
        super(PDFTool, self).openUrl(url)

    def _okularMiniBar(self):
        """ get the okular miniBar """
        return self.part.widget().findChild(QWidget, "miniBar").parent()
        
    def toggleMiniBar(self):
        w = self._okularMiniBar()
        if w.isVisibleTo(w.parent()):
            w.hide()
        else:
            w.show()


class QuickInsertTool(kateshell.mainwindow.Tool):
    def __init__(self, mainwin):
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "quickinsert", i18n("Quick Insert"), "document-properties",
            dock=kateshell.mainwindow.Left,
            factory=self.factory)
            
    def factory(self):
        import frescobaldi_app.lqi
        return frescobaldi_app.lqi.ToolBox(self)

