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

import glob, os, re, sip, time
from dbus.service import method

from PyQt4.QtCore import QObject, QString, QTimer, QVariant, Qt, SIGNAL
from PyQt4.QtGui import QActionGroup, QLabel, QStackedWidget, QWidget
from PyKDE4.kdecore import KConfig, KGlobal, KUrl, i18n
from PyKDE4.kdeui import (
    KActionMenu, KApplication, KDialog, KIcon, KLineEdit, KMessageBox,
    KStandardAction, KVBox)
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
    defaultMode = "LilyPond"
    
    def __init__(self, servicePrefix, installPrefix=None):
        kateshell.app.MainApp.__init__(self, servicePrefix, installPrefix)
        # just set now because we are translated
        self.fileTypes = ["*.ly *.ily *.lyi|%s" % i18n("LilyPond files")]
        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = self.serviceName + '/MainApp'
        os.environ["FRESCOBALDI_PID"] = str(os.getpid())
        # check if stuff needs to be run after an update of Frescobaldi
        if self.version() != config("").readEntry("version", "0.0"):
            from frescobaldi_app.install import install
            install(self)
        
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
    
    @lazy
    def stateManager(self):
        return StateManager(self)
        
        
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
        if config().readEntry("save metainfo", QVariant(False)).toBool():
            self.app.stateManager().loadState(self)
        
    def aboutToClose(self):
        if config().readEntry("save metainfo", QVariant(False)).toBool():
            self.app.stateManager().saveState(self)
        
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

    @lazy
    def manipulator(self):
        """
        Returns a singleton object for this document that can
        perform more advanced manipulations.
        """
        import frescobaldi_app.document
        return frescobaldi_app.document.DocumentManipulator(self)
        

class MainWindow(kateshell.mainwindow.MainWindow):
    """ Our customized Frescobaldi MainWindow """
    def __init__(self, app):
        kateshell.mainwindow.MainWindow.__init__(self, app)

        KonsoleTool(self)
        LogTool(self)
        QuickInsertTool(self)
        RumorTool(self)
        if not config().readEntry("disable pdf preview", QVariant(False)).toBool():
            PDFTool(self)
        
        self.jobs = {}
        listeners[app.activeChanged].append(self.updateJobActions)
        
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
            elif d.url().protocol() != "file":
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
        
        # Edit menu actions:
        @self.onSelAction(i18n("Cut and Assign"), "edit-cut", key="Ctrl+Shift+C",
            tooltip=i18n("Cut selection and assign it to a LilyPond variable."))
        def edit_cut_assign(text):
            self.currentDocument().manipulator().assignSelectionToVariable()
            
        # actions and functionality for editing pitches
        a = KActionMenu(KIcon("applications-education-language"),
                i18n("Pitch Name Language"), self)
        a.setToolTip(i18n("Change the LilyPond language used for pitch names "
                          "in this document or in the selection."))
        self.actionCollection().addAction('pitch_change_language', a)
        QObject.connect(a.menu(), SIGNAL("aboutToShow()"), lambda menu=a.menu():
            self.currentDocument().manipulator().populateLanguageMenu(menu))
        
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
        
        @self.onSelAction(i18n("Copy rhythm"),
            tooltip=i18n("Copy the rhythm of the selected music."))
        def durations_copy_rhythm(text):
            import ly.duration
            text = ' '.join(ly.duration.extractRhythm(text))
            KApplication.clipboard().setText(text)
            
        @self.onSelAction(i18n("Paste rhythm"),
            tooltip=i18n("Paste a rhythm to the selected music."))
        def durations_paste_rhythm(text):
            import ly.duration
            rhythm = unicode(KApplication.clipboard().text())
            return ly.duration.applyRhythm(text, rhythm)
        
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
        def options_configure():
            import frescobaldi_app.settings
            frescobaldi_app.settings.SettingsDialog(self).show()

    def setupGeneratedMenus(self):
        super(MainWindow, self).setupGeneratedMenus()
        # Generated file menu:
        menu = self.factory().container("lilypond_actions", self)
        def populateGenFilesMenu(menu=menu):
            for action in menu.actions():
                if action.objectName() != "actions_email":
                    sip.delete(action)
            doc = self.currentDocument()
            if not doc:
                return
            menu.addSeparator()
            self.actionManager().addActionsToMenu(doc.updatedFiles(), menu)
        QObject.connect(menu, SIGNAL("aboutToShow()"), populateGenFilesMenu)
        
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

    def saveSettings(self):
        self.app.stateManager().cleanup()
        super(MainWindow, self).saveSettings()


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

    def readConfig(self, conf):
        self._sync = conf.readEntry("sync", QVariant(False)).toBool()

    def writeConfig(self, conf):
        conf.writeEntry("sync", QVariant(self._sync))
        

class PDFTool(kateshell.mainwindow.KPartTool):
    _partlibrary = "okularpart"
    def __init__(self, mainwin):
        self._config = {}
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "pdf", i18n("PDF Preview"), "application-pdf",
            dock=kateshell.mainwindow.Right)
        listeners[mainwin.app.activeChanged].append(self.sync)
        self._currentUrl = None
        # We open urls with a timer otherwise Okular is called 
        # too quickly when the user switches documents too fast.
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        def timeoutFunc():
            if self._currentUrl:
                super(PDFTool, self).openUrl(self._currentUrl)
        QObject.connect(self._timer, SIGNAL("timeout()"), timeoutFunc)

    def delete(self):
        listeners[self.mainwin.app.activeChanged].remove(self.sync)
        super(PDFTool, self).delete()
        
    def sync(self, doc):
        if self._config["sync"] and not doc.url().isEmpty():
            pdfs = doc.updatedFiles()("pdf")
            if pdfs:
                self.openUrl(KUrl(pdfs[0]))
    
    def addMenuActions(self, m):
        m.addSeparator()
        def act(name, title):
            a = m.addAction(title)
            a.setCheckable(True)
            a.setChecked(self._config[name])
            QObject.connect(a, SIGNAL("triggered()"),
                lambda: self.toggleAction(name))
        act("leftpanel", i18n("Show PDF Navigation Panel"))
        act("minipager", i18n("Show PDF minipager"))
        m.addSeparator()
        act("sync", i18n("S&ynchronize Preview with Current Document"))

    def toggleAction(self, name):
        c = self._config[name] = not self._config[name]
        if not self.part:
            return
        # if the part has already loaded, perform these settings.
        if name == "leftpanel":
            self.part.actionCollection().action("show_leftpanel").setChecked(c)
        elif name == "minipager":
            self._okularMiniBar().setVisible(c)

    def openUrl(self, url):
        """ Expects KUrl."""
        if not self.failed:
            self.show()
            if url != self._currentUrl:
                self._currentUrl = url
                self._timer.start()

    def _okularMiniBar(self):
        """ get the okular miniBar """
        return self.part.widget().findChild(QWidget, "miniBar").parent()
        
    def partLoaded(self):
        if not self._config["minipager"]:
            self._okularMiniBar().hide()
        self.part.actionCollection().action("show_leftpanel").setChecked(
            self._config["leftpanel"])
        # change shortcut context for actions that conflict with Kate's
        for action in "view_scroll_up", "view_scroll_down":
            self.part.actionCollection().action(action).setShortcutContext(
                Qt.WidgetShortcut)
        # default to single page layout
        single = self.part.actionCollection().action("view_render_mode_single")
        if single and not single.isChecked():
            single.trigger()

    def readConfig(self, conf):
        for name, default in (
            ("minipager", True),
            ("leftpanel", False),
            ("sync", True)):
            self._config[name] = conf.readEntry(name, QVariant(default)).toBool()
            
    def writeConfig(self, conf):
        for name in "minipager", "leftpanel", "sync":
            conf.writeEntry(name, QVariant(self._config[name]))
        
        
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


class StateManager(object):
    """
    Manages state and meta-info for documents, like bookmarks
    and cursor position, etc.
    """
    def __init__(self, app):
        self.app = app
        self.metainfos = KConfig("metainfos", KConfig.NoGlobals, "appdata")
        
    def loadState(self, doc):
        if (not doc.url().isEmpty() and
                self.metainfos.hasGroup(doc.url().prettyUrl())):
            group = self.metainfos.group(doc.url().prettyUrl())
            last = group.readEntry("time", QVariant(0.0)).toDouble()[0]
            # when it is a local file, only load the state when the
            # file was not modified later
            if not doc.localPath() or (
                    os.path.exists(doc.localPath()) and
                    os.path.getmtime(doc.localPath()) <= last):
                doc.readConfig(group)
            
    def saveState(self, doc):
        if doc.view and not doc.url().isEmpty():
            group = self.metainfos.group(doc.url().prettyUrl())
            group.writeEntry("time", QVariant(time.time()))
            doc.writeConfig(group)
            group.sync()
            
    def cleanup(self):
        """ Purge entries that are not used for more than a month. """
        for g in self.metainfos.groupList():
            last = self.metainfos.group(g).readEntry("time", QVariant(0.0)).toDouble()[0]
            if (time.time() - last) / 86400 > 31:
                self.metainfos.deleteGroup(g)
        self.metainfos.sync()



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
    
