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
from PyKDE4.ktexteditor import KTextEditor

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
    def __init__(self, *args):
        super(Document, self).__init__(*args)
        self._job = None        # running LilyPond job
        
    def hasUpdated(self, ext):
        """
        return true if this document has one or more LilyPond-generated
        outputs with the given extension that are up-to-date.
        """
        return True # FIXME implement
    
    def isRunning(self):
        """
        Return True if there is a running LilyPond job.
        """
        return not self._job
        
    def runLilyPond(self, preview=True):
        """
        Start a LilyPond job. If preview=False, switch off point-and-click.
        """
        if self._job: return
        from frescobaldi_app.runlily import Ly2PDF
        self._job = Ly2PDF(self, preview)
        
    def abort(self):
        """
        Abort a running LilyPond job.
        """
        self._job and self._job.kill(2)


class MainWindow(kateshell.mainwindow.MainWindow):
    """ Our customized Frescobaldi MainWindow """
    def __init__(self, app):
        kateshell.mainwindow.MainWindow.__init__(self, app)

        KonsoleTool(self)
        LogTool(self)
        PDFTool(self)
        QuickInsertTool(self)

    def setupActions(self):
        super(MainWindow, self).setupActions()
        
        # Score wizard
        @self.onAction(i18n("Setup New Score..."), "text-x-lilypond")
        def lilypond_score_wizard():
            pass # TODO implement
        
        # run LilyPond actions
        @self.onAction(i18n("Run LilyPond (preview)"))
        def lilypond_run_preview():
            lilypond_run_publish(True)
            
        @self.onAction(i18n("Run LilyPond (publish)"))
        def lilypond_run_publish(preview=False):
            d = self.currentDocument()
            if d:
                if not d.isRunning():
                    d.runLilyPond(preview)
                else:
                    KMessageBox.sorry(self,
                        i18n("There is already a LilyPond job running "
                             "for this document."),
                        i18n("Already Running"))
            
        # actions and functionality for editing rhythms
        @self.onSelAction(i18n("Double durations"),
            tooltip=i18n("Double all the durations in the selection."))
        def durations_double(text):
            import ly.duration
            return ly.duration.doubleDurations(text)
            
        @self.onSelAction(i18n("Halve durations"),
            tooltip=i18n("Halve all the durations in the selection."))
        def durations_halve(text):
            import ly.duration
            return ly.duration.halveDurations(text)
            
        @self.onSelAction(i18n("Dot durations"),
            tooltip=i18n("Add a dot to all the durations in the selection."))
        def durations_dot(text):
            import ly.duration
            return ly.duration.dotDurations(text)
            
        @self.onSelAction(i18n("Undot durations"),
            tooltip=i18n("Remove one dot from all the durations in the selection."))
        def durations_undot(text):
            import ly.duration
            return ly.duration.undotDurations(text)
            
        @self.onSelAction(i18n("Remove scaling"),
            tooltip=i18n("Remove all scaling (*n/m) from the durations in the selection."))
        def durations_remove_scaling(text):
            import ly.duration
            return ly.duration.removeScaling(text)
            
        @self.onSelAction(i18n("Remove durations"),
            tooltip=i18n("Remove all durations from the selection."))
        def durations_remove(text):
            import ly.duration
            return ly.duration.removeDurations(text)
            
        @self.onSelAction(i18n("Make implicit"),
            tooltip=i18n("Make durations implicit (remove repeated durations)."))
        def durations_implicit(text):
            import ly.duration
            return ly.duration.makeImplicit(text)
            
        @self.onSelAction(i18n("Make explicit"),
            tooltip=i18n("Make durations explicit (add duration to every note, "
                         "even if it is the same as the preceding note)."))
        def durations_explicit(text):
            import ly.duration
            return ly.duration.makeExplicit(text)
            
        self._savedRhythms = set() # for the completionObject
            
        @self.onSelAction(i18n("Apply rhythm..."),
            tooltip=i18n("Apply an entered rhythm to the selected music."))
        def durations_apply_rhythm(text):
            d = KDialog(self)
            d.setCaption(i18n("Apply Rhythm"))
            d.setButtons(KDialog.ButtonCode(KDialog.Ok | KDialog.Apply | KDialog.Cancel))
            d.setModal(True)
            v = KVBox(d)
            d.setMainWidget(v)
            QLabel(i18n("Enter a rhythm:"), v)
            edit = KLineEdit(v)
            edit.completionObject().setItems(list(self._savedRhythms))
            edit.setFocus()
            edit.setToolTip(i18n(
                "Enter a rhythm using space separated duration values "
                "(e.g. 8. 16 8 4 8)"))
            def applyTheRhythm():
                rhythm = unicode(edit.text())
                self._savedRhythms.add(rhythm)
                import ly.duration
                self.replaceSelectionWith(ly.duration.applyRhythm(text, rhythm))
            QObject.connect(d, SIGNAL("applyClicked()"), applyTheRhythm)
            QObject.connect(d, SIGNAL("okClicked()"), applyTheRhythm)
            d.show()

        # Setup lyrics hyphen and de-hyphen action
        @self.onSelAction(i18n("Hyphenate Lyrics Text"), keepSelection=False)
        def lyrics_hyphen(text):
            import frescobaldi_app.hyphen
            return frescobaldi_app.hyphen.hyphenate(text, self)
            
        @self.onSelAction(i18n("Remove hyphenation"), keepSelection=False)
        def lyrics_dehyphen(text):
            return text.replace(' -- ', '')


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


class LogTool(kateshell.mainwindow.Tool):
    def __init__(self, mainwin):
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "log", i18n("LilyPond Log"), "help-about",
            dock=kateshell.mainwindow.Bottom,
            widget=QStackedWidget())
        self.logs = {}
        listeners[mainwin.app.activeChanged].append(self.showLog)
        
    def showLog(self, doc):
        if doc in self.logs:
            self.widget.setCurrentWidget(self.logs[doc])
            
    def createLog(self, doc):
        if doc not in self.logs:
            from frescobaldi_app.runlily import LogWidget
            self.logs[doc] = LogWidget(self, doc)
        return self.logs[doc]

