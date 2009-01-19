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

import glob, os, re, sip
from dbus.service import method

from PyQt4.QtCore import QDate, QObject, QString, QTimer, QVariant, Qt, SIGNAL
from PyQt4.QtGui import QLabel, QStackedWidget, QWidget
from PyKDE4.kdecore import KConfig, KGlobal, KUrl, i18n
from PyKDE4.kdeui import (
    KDialog, KIcon, KLineEdit, KMessageBox, KStandardAction, KVBox)
from PyKDE4.kparts import KParts
from PyKDE4.ktexteditor import KTextEditor

import kateshell.app, kateshell.mainwindow
from kateshell.mainwindow import listeners

# Constants ...
# find specially formatted variables in a LilyPond source document
_variables_re = re.compile(r'^%%([a-z]+(?:-[a-z]+)*):[ \t]*(.+?)[ \t]*$', re.M)


def lazy(func):
    """
    A decorator that only performs the function call the first time,
    caches the return value, and returns that next time.
    The argments tuple should be hashable.
    """
    cache = {}
    def loader(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return loader


class MainApp(kateshell.app.MainApp):
    """ A Frescobaldi application instance """
    
    defaultEncoding = 'UTF-8'
    defaultHighlightingMode = "LilyPond"
    
    def __init__(self, servicePrefix):
        kateshell.app.MainApp.__init__(self, servicePrefix)
        # just set now because we are translated
        self.fileTypes = ["*.ly *.ily *.lyi|%s" % i18n("LilyPond files")]
        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = self.serviceName + '/MainApp'
        os.environ["FRESCOBALDI_PID"] = str(os.getpid())
        self.metainfos = KConfig("metainfos", KConfig.NoGlobals, "appdata")
        
    def openUrl(self, url, encoding=None):
        # The URL can be python string, dbus string or QString or KUrl
        if not isinstance(url, KUrl):
            url = KUrl(url)
        nav = False
        if url.protocol() == "textedit":
            parts = unicode(url.path()).rsplit(":", 3)
            if len(parts) > 2:
                # We have a valid textedit:/ uri.
                url = KUrl.fromPath(parts[0].encode('latin1').decode("utf-8"))
                line, char = map(int, parts[1:3])
                nav = True
            else:
                # We can't open malformed textedit urls
                url = KUrl()
        d = kateshell.app.MainApp.openUrl(self, url, encoding)
        if nav:
            d.setCursorPosition(line, char)
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

    def createDocument(self, url=None, encoding=None):
        return Document(self, url, encoding)

    def defaultDirectory(self):
        return config().readPathEntry("default directory", "")
        

class Document(kateshell.app.Document):
    """ Our own Document type with LilyPond-specific features """
    def documentIcon(self):
        if self in self.app.mainwin.jobs:
            return "run-lilypond"
        return super(Document, self).documentIcon()
    
    def viewCreated(self):
        super(Document, self).viewCreated()
        # delete some actions from the view before plugging in GUI
        # trick found in kateviewmanager.cpp
        for name in "set_confdlg", "editor_options":
            action = self.view.actionCollection().action(name)
            if action:
                sip.delete(action)
        self.loadState()
        
    def aboutToClose(self):
        self.saveState()
        
    def viewActions(self):
        """
        Iterate over the View actions for which the state could be saved.
        """
        if self.view:
            for name in (
                "view_word_wrap_marker", "view_border", "view_line_numbers",
                "view_scrollbar_marks"):
                action = self.view.actionCollection().action(name)
                if action:
                    yield name, action

    def loadState(self):
        if (not self.url().isEmpty() and 
            self.app.metainfos.hasGroup(self.url().prettyUrl())):
            group = self.app.metainfos.group(self.url().prettyUrl())
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
            marks = str(group.readEntry("bookmarks", ""))
            if re.match(r"\d+:\d+(,\d+:\d+)*$", marks):
                markiface = self.doc.markInterface()
                for m in marks.split(','):
                    line, mark = map(int, m.split(':'))
                    if line < self.doc.lines():
                        markiface.addMark(line, mark)
            
    def saveState(self):
        if self.view and not self.url().isEmpty():
            group = self.app.metainfos.group(self.url().prettyUrl())
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
            marks = []
            for line in range(self.doc.lines()):
                m = markiface.mark(line)
                if m:
                    marks.append("%d:%d" % (line, m))
            group.writeEntry("bookmarks", ','.join(marks))
            group.writeEntry("date", QVariant(QDate.currentDate()))
            group.sync()
            
    def variables(self):
        """
        Returns a dictionary with variables put in specially formatted LilyPond
        comments, like:
        %%varname: value
        (double percent at start of line, varname, colon and value)
        Varname should consist of lowercase letters, and may contain (but not
        end or start with) single hyphens.
        """
        if not self.doc:
            return {}
        return dict(_variables_re.findall(self.text()))
    
    def updatedFiles(self):
        """
        Returns a function that can list updated files based on extension.
        """
        return updatedFiles(self.localPath())
            

class MainWindow(kateshell.mainwindow.MainWindow):
    """ Our customized Frescobaldi MainWindow """
    def __init__(self, app):
        kateshell.mainwindow.MainWindow.__init__(self, app)

        KonsoleTool(self)
        LogTool(self)
        PDFTool(self)
        QuickInsertTool(self)
        RumorTool(self)
        
        self.jobs = {}
        listeners[app.activeChanged].append(self.updateJobActions)
        
        # Generated files actions:
        self.generatedFilesMenu = self.factory().container(
            "lilypond_actions", self)
        QObject.connect(self.generatedFilesMenu, SIGNAL("aboutToShow()"),
            self.populateGeneratedFilesMenu)
            
    @lazy
    def actionManager(self):
        """
        Returns the ActionManager, managing actions that can be performed
        on files creating by LilyPond.
        """
        import frescobaldi_app.actions
        return frescobaldi_app.actions.ActionManager(self)
        
    @lazy
    def scoreWizard(self):
        import frescobaldi_app.scorewiz
        return frescobaldi_app.scorewiz.ScoreWizard(self)
    
    @lazy
    def applyRhythmDialog(self):
        return ApplyRhythmDialog(self)
        
    def setupActions(self):
        super(MainWindow, self).setupActions()
        
        # LilyPond runner toolbar icon
        @self.onAction(i18n("LilyPond"), "run-lilypond")
        def lilypond_runner():
            d = self.currentDocument()
            if d:
                if d in self.jobs:
                    self.abortLilyPondJob(d)
                else:
                    lilypond_run_preview()

        # Score wizard
        @self.onAction(i18n("Setup New Score..."), "text-x-lilypond", key="Ctrl+Shift+N")
        def lilypond_score_wizard():
            self.scoreWizard().show()
        
        # run LilyPond actions
        @self.onAction(i18n("Run LilyPond (preview)"), "run-lilypond", key="Ctrl+M")
        def lilypond_run_preview():
            lilypond_run_publish(True)
            
        @self.onAction(i18n("Run LilyPond (publish)"), "run-lilypond")
        def lilypond_run_publish(preview=False):
            d = self.currentDocument()
            if not d:
                return
            elif d in self.jobs:
                return KMessageBox.sorry(self,
                    i18n("There is already a LilyPond job running "
                            "for this document."),
                    i18n("Already Running"))
            elif d.url().isEmpty():
                return KMessageBox.sorry(self, i18n(
                    "Your document currently has no filename, "
                    "please save first."))
            elif not d.url().protocol() == "file":
                return KMessageBox.sorry(self, i18n(
                    "Sorry, support for remote files is not yet implemented.\n"
                    "Please save your document to a local file."))
            if d.isModified():
                if config().readEntry("save on run", QVariant(False)).toBool():
                    d.save()
                else:
                    return KMessageBox.sorry(self, i18n(
                        "Your document has been modified, "
                        "please save first."))
            self.createLilyPondJob(d, preview)
        
        @self.onAction(i18n("Interrupt LilyPond Job"), "process-stop")
        def lilypond_abort():
            d = self.currentDocument()
            if d:
                self.abortLilyPondJob(d)
            
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
            
        @self.onSelAction(i18n("Apply rhythm..."),
            tooltip=i18n("Apply an entered rhythm to the selected music."))
        def durations_apply_rhythm(text):
            self.applyRhythmDialog().edit(text)
        
        # Setup lyrics hyphen and de-hyphen action
        @self.onSelAction(i18n("Hyphenate Lyrics Text"), keepSelection=False, key="Ctrl+L")
        def lyrics_hyphen(text):
            import frescobaldi_app.hyphen
            return frescobaldi_app.hyphen.hyphenate(text, self)
            
        @self.onSelAction(i18n("Remove hyphenation"), keepSelection=False)
        def lyrics_dehyphen(text):
            return text.replace(' -- ', '')
            
        # Other actions
        @self.onAction(i18n("Insert LilyPond version"), key="Ctrl+Shift+V")
        def version_insert():
            import frescobaldi_app.version
            frescobaldi_app.version.insertVersion(self)
            
        @self.onAction(i18n("Update with convert-ly"))
        def version_convert_ly():
            import frescobaldi_app.version
            frescobaldi_app.version.convertLy(self)

        @self.onAction(i18n("Open Current Folder"), "document-open-folder")
        def file_open_current_folder():
            self.actionManager().openDirectory()
    
        @self.onAction(i18n("Email..."), "mail-send")
        def actions_email():
            self.actionManager().email(self.currentDocument().updatedFiles())
            
        # Settings
        @self.onAction(KStandardAction.Preferences)
        def settings_configure():
            import frescobaldi_app.settings
            frescobaldi_app.settings.SettingsDialog(self).show()
            
    def createLilyPondJob(self, doc, preview=True):
        if doc not in self.jobs:
            from frescobaldi_app.runlily import LyDoc2PDF
            # get a LogWidget
            log = self.tools["log"].createLog(doc)
            if config().readEntry("always show log", QVariant(True)).toBool():
                log.show()
            self.jobs[doc] = LyDoc2PDF(doc, log, preview)
            self.updateJobActions()
            def finished():
                listeners[doc.close].remove(self.abortLilyPondJob)
                result = self.jobs[doc].updatedFiles()
                pdfs = result("pdf")
                if pdfs and "pdf" in self.tools:
                    self.tools["pdf"].openUrl(KUrl(pdfs[0]))
                self.actionManager().addActionsToLog(result, log)
                del self.jobs[doc]
                self.updateJobActions()
            listeners[doc.close].append(self.abortLilyPondJob)
            listeners[self.jobs[doc].finished].append(finished)
            
    def abortLilyPondJob(self, doc):
        if doc in self.jobs:
            self.jobs[doc].abort()

    def updateJobActions(self, doc=None):
        doc = doc or self.currentDocument()
        running = doc and doc in self.jobs
        act = self.actionCollection().action
        act("lilypond_run_preview").setEnabled(not running)
        act("lilypond_run_publish").setEnabled(not running)
        act("lilypond_abort").setEnabled(running)
        if running:
            icon = "process-stop"
            tip = i18n("Abort the running LilyPond process")
        else:
            icon = "run-lilypond"
            tip = i18n("Run LilyPond in preview mode")
        act("lilypond_runner").setIcon(KIcon(icon))
        act("lilypond_runner").setToolTip(tip)

    def populateGeneratedFilesMenu(self):
        menu = self.generatedFilesMenu
        for action in menu.actions():
            if action.objectName() != "actions_email":
                sip.delete(action)
        doc = self.currentDocument()
        if not doc:
            return
        menu.addSeparator()
        self.actionManager().addActionsToMenu(doc.updatedFiles(), menu)
        

class ApplyRhythmDialog(KDialog):
    def __init__(self, mainwin):
        KDialog.__init__(self, mainwin)
        self.setCaption(i18n("Apply Rhythm"))
        self.setButtons(KDialog.ButtonCode(KDialog.Ok | KDialog.Apply | KDialog.Cancel))
        self.setModal(True)
        v = KVBox(self)
        v.setSpacing(4)
        self.setMainWidget(v)
        QLabel(i18n("Enter a rhythm:"), v)
        self.lineedit = KLineEdit(v)
        self.lineedit.setToolTip(i18n(
            "Enter a rhythm using space separated duration values "
            "(e.g. 8. 16 8 4 8)"))
        QObject.connect(self, SIGNAL("applyClicked()"), self.doApply)
        QObject.connect(self, SIGNAL("okClicked()"), self.doApply)

    def doApply(self):
        import ly.duration
        self.lineedit.completionObject().addItem(self.lineedit.text())
        self.parent().replaceSelectionWith(ly.duration.applyRhythm(
            self.text, unicode(self.lineedit.text())))

    def edit(self, text):
        self.text = text
        self.show()
        self.lineedit.setFocus()
        self.lineedit.selectAll()


class KonsoleTool(kateshell.mainwindow.KPartTool):
    """ A tool embedding a Konsole """
    _partlibrary = "libkonsolepart"
    
    def __init__(self, mainwin):
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "konsole", i18n("Terminal"), "terminal",
            dock=kateshell.mainwindow.Bottom)
        listeners[mainwin.app.activeChanged].append(self.sync)
        self._sync = self.config().readEntry("sync", QVariant(False)).toBool()
            
    def partFactory(self):
        w = super(KonsoleTool, self).partFactory()
        if self.part:
            d = self.mainwin.currentDocument()
            if d and not d.url().isEmpty():
                url = d.url()
            else:
                url = KUrl.fromPath(
                    self.mainwin.app.defaultDirectory() or os.getcwd())
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
            and doc and doc.doc and not doc.url().isEmpty()):
            # FIXME This does not work currently.
            self.openUrl(doc.url().directory())

    def addMenuActions(self, m):
        m.addSeparator()
        a = m.addAction(i18n("S&ynchronize Terminal with Current Document"))
        a.setCheckable(True)
        a.setChecked(self._sync)
        QObject.connect(a, SIGNAL("triggered()"), self.toggleSync)
        
    def toggleSync(self):
        self._sync = not self._sync

    def saveSettings(self):
        self.config().writeEntry("sync", QVariant(self._sync))
        

class PDFTool(kateshell.mainwindow.KPartTool):
    _partlibrary = "okularpart"
    def __init__(self, mainwin):
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "pdf", i18n("PDF Preview"), "application-pdf",
            dock=kateshell.mainwindow.Right)
        listeners[mainwin.app.activeChanged].append(self.sync)
        self._currentUrl = None
        self._sync = self.config().readEntry("sync", QVariant(True)).toBool()
        # We open urls with a timer otherwise Okular is called 
        # too quickly when the user switches documents too fast.
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        def timeoutFunc():
            if self._currentUrl:
                super(PDFTool, self).openUrl(self._currentUrl)
        QObject.connect(self._timer, SIGNAL("timeout()"), timeoutFunc)
    
    def sync(self, doc):
        if self._sync and not doc.url().isEmpty():
            pdfs = doc.updatedFiles()("pdf")
            if pdfs:
                self.openUrl(KUrl(pdfs[0]))
    
    def toggleSync(self):
        self._sync = not self._sync
    
    def addMenuActions(self, m):
        if self.part:
            m.addSeparator()
            a = m.addAction(i18n("Show PDF Navigation Panel"))
            a.setCheckable(True)
            a.setChecked(self.part.actionCollection().action(
                "show_leftpanel").isChecked())
            QObject.connect(a, SIGNAL("triggered()"), lambda:
                self.part.actionCollection().action("show_leftpanel").toggle())
            a = m.addAction(i18n("Show PDF minipager"))
            a.setCheckable(True)
            w = self._okularMiniBar()
            a.setChecked(w.isVisibleTo(w.parent()))
            QObject.connect(a, SIGNAL("triggered()"), self.toggleMiniBar)
        m.addSeparator()
        a = m.addAction(i18n("S&ynchronize Preview with Current Document"))
        a.setCheckable(True)
        a.setChecked(self._sync)
        QObject.connect(a, SIGNAL("triggered()"), self.toggleSync)
    
    def openUrl(self, url):
        """ Expects KUrl."""
        self.show()
        if url != self._currentUrl:
            self._currentUrl = url
            self._timer.start()

    def _okularMiniBar(self):
        """ get the okular miniBar """
        return self.part.widget().findChild(QWidget, "miniBar").parent()
        
    def toggleMiniBar(self):
        w = self._okularMiniBar()
        if w.isVisibleTo(w.parent()):
            w.hide()
        else:
            w.show()

    def partLoaded(self):
        conf = self.config()
        if not conf.readEntry("minipager", QVariant(True)).toBool():
            self._okularMiniBar().hide()
        self.part.actionCollection().action("show_leftpanel").setChecked(
            conf.readEntry("leftpanel", QVariant(False)).toBool())
        # change shortcut context for actions that conflict with Kate's
        for action in "view_scroll_up", "view_scroll_down":
            self.part.actionCollection().action(action).setShortcutContext(
                Qt.WidgetShortcut)
        
    def saveSettings(self):
        conf = self.config()
        if self.part:
            w = self._okularMiniBar()
            conf.writeEntry("minipager", QVariant(w.isVisibleTo(w.parent())))
            conf.writeEntry("leftpanel", QVariant(
                self.part.actionCollection().action("show_leftpanel").isChecked()))
        conf.writeEntry("sync", QVariant(self._sync))
        
        
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
            "log", i18n("LilyPond Log"), "run-lilypond",
            dock=kateshell.mainwindow.Bottom,
            widget=QStackedWidget())
        self.logs = {}
        self.widget.addWidget(QLabel("<center>(%s)</center>" % i18n("no log")))
        listeners[mainwin.app.activeChanged].append(self.showLog)
        
    def showLog(self, doc):
        if doc in self.logs:
            self.widget.setCurrentWidget(self.logs[doc])
            
    def createLog(self, doc):
        if doc not in self.logs:
            from frescobaldi_app.runlily import Log
            self.logs[doc] = Log(self, doc)
            self.widget.addWidget(self.logs[doc])
            listeners[doc.close].append(self.removeLog)
        self.showLog(doc)
        return self.logs[doc]

    def removeLog(self, doc):
        if doc in self.logs:
            sip.delete(self.logs[doc])
            del self.logs[doc]
            if self.widget.count() == 1:
                if not self._docked:
                    self.dock()
                self.hide()


class RumorTool(kateshell.mainwindow.Tool):
    def __init__(self, mainwin):
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "rumor", i18n("Rumor"), "media-record",
            dock=kateshell.mainwindow.Bottom,
            factory=self.factory)
            
    def factory(self):
        import frescobaldi_app.rumor
        return frescobaldi_app.rumor.RumorPanel(self)



# Easily get our global config
def config(group="preferences"):
    return KGlobal.config().group(group)
    

# determine updated files by a LilyPond process.
def updatedFiles(lyfile, reftime=None):
    """
    Return a generator that can list updated files belonging to
    LilyPond document lyfile.
    Calling the generator with some extension
    returns files newer than lyfile, with that extension.
    """
    if lyfile and os.path.exists(lyfile):
        if reftime is None:
            reftime = os.path.getmtime(lyfile)
        basename = os.path.splitext(lyfile)[0]
        def generatorfunc(ext = "*"):
            files = (
                glob.glob(basename + "." + ext) +
                glob.glob(basename + "-[0-9]*." + ext) +
                glob.glob(basename + "-?*-[0-9]*." + ext))
            return [f for f in files if os.path.getmtime(f) >= reftime]
    else:
        def generatorfunc(ext=None):
            return []
    generatorfunc.lyfile = lyfile
    return generatorfunc
    
