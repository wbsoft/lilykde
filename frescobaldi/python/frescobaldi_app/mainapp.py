# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
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

from __future__ import unicode_literals

import os, re, sip, weakref
from dbus.service import method

from PyQt4.QtCore import QDir, QEvent, QSize, QTimer, Qt
from PyQt4.QtGui import (
    QActionGroup, QColor, QIcon, QLabel, QPalette, QPixmap, QProgressBar,
    QStackedWidget, QWidget)
from PyKDE4.kdecore import KConfig, KGlobal, KUrl, i18n
from PyKDE4.kdeui import (
    KActionMenu, KApplication, KDialog, KIcon, KIconLoader, KLineEdit, KMenu,
    KMessageBox, KNotification, KStandardAction, KStandardGuiItem, KVBox)
from PyKDE4.kparts import KParts
from PyKDE4.ktexteditor import KTextEditor

from signals import Signal

import kateshell.app, kateshell.mainwindow
from kateshell.app import cacheresult


# Constants ...
# find specially formatted variables in a LilyPond source document
_variables_re = re.compile(r'^%%([a-z]+(?:-[a-z]+)*):[ \t]*(.+?)[ \t]*$', re.M)


class MainApp(kateshell.app.MainApp):
    """ A Frescobaldi application instance """
    
    defaultEncoding = 'UTF-8'
    defaultMode = "LilyPond"
    
    def __init__(self, servicePrefix):
        kateshell.app.MainApp.__init__(self, servicePrefix)
        # just set now because we are translated
        self.fileTypes = ["*.ly *.ily *.lyi|" + i18n("LilyPond files")]
        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = self.serviceName + '/MainApp'
        os.environ["FRESCOBALDI_PID"] = str(os.getpid())
        # make files for stylesheets and LilyPond-generated pics easily found:
        QDir.setSearchPaths('css', KGlobal.dirs().findDirs('appdata', 'css/'))
        QDir.setSearchPaths('pics', KGlobal.dirs().findDirs('appdata', 'pics/'))
    
    def setupConfiguration(self, config):
        # If the application got upgraded, run the install module
        oldVersion = config.readEntry("version", "")
        if oldVersion != self.version():
            config.writeEntry("version", self.version())
            from frescobaldi_app.install import install
            install(self, oldVersion)
        # force install ourselves as custom editor in okularpart
        # when this key is True or unset (e.g. by an installer).
        if config.readEntry('configure okularpart', True):
            config.writeEntry('configure okularpart', False)
            from frescobaldi_app.install import installOkularPartRC
            installOkularPartRC()
    
    def openUrl(self, url, encoding=None):
        # The URL can be python string, dbus string or KUrl
        if not isinstance(url, KUrl):
            url = KUrl(url)
        nav = False
        if url.protocol() == "textedit":
            m = re.match(r"^(.*):(\d+):(\d+):(\d+)$", url.path())
            if m:
                # We have a valid textedit:/ uri.
                url = KUrl.fromPath(m.group(1).encode('latin1').decode("utf-8"))
                line, char, col = map(int, m.group(2, 3, 4))
                nav = True
            else:
                # We can't open malformed textedit urls
                url = KUrl()
        d = kateshell.app.MainApp.openUrl(self, url, encoding)
        if nav:
            d.setCursorPosition(line, col, False)
        return d

    @method("org.lilypond.TextEdit", in_signature='s', out_signature='b')
    def openTextEditUrl(self, url):
        """Opens the specified textedit:// URL.

        To be called by ktexteditservice (part of lilypond-kde4).
        
        """
        return bool(self.openUrl(url))

    def createMainWindow(self):
        """ use our own MainWindow """
        return MainWindow(self)

    def createDocument(self, url=None, encoding=None):
        return Document(self, url, encoding)

    def defaultDirectory(self):
        return config().readPathEntry("default directory", "")
    
    def findDocument(self, url):
        """Finds the document at KUrl url.
        
        Also non-local or nameless documents are checked: see runlily.py
        
        """
        d = super(MainApp, self).findDocument(url)
        if d:
            return d
        # now check for our LocalFileManagers ...
        for d in self.documents:
            manager = d.localFileManager()
            if manager and manager.path() == url:
                return d
        return False
    
    def keepMetaInfo(self):
        return config().readEntry("save metainfo", False)


class Document(kateshell.app.Document):
    """ Our own Document type with LilyPond-specific features """
    
    metainfoDefaults = {
        "custom lilypond version": "", # lily version last used in custom dialog
        "custom verbose": False,       # custom dialog: was verbose checked?
        "custom preview": True,        # custom dialog: was preview checked?
        "build time": 0.0,             # remember build time
        "preview": True,               # was last run in preview mode?
        }
    
    def __init__(self, *args, **kwargs):
        super(Document, self).__init__(*args, **kwargs)
        self.resetLocalFileManager()
        self.urlChanged.connect(self.resetLocalFileManager)

    def documentIcon(self):
        if self.app.mainwin.jobManager().job(self):
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
        # rename "Print..." action to make clear KatePart's print action prints
        # the source text instead of LilyPond scores
        action = self.view.actionCollection().action("file_print")
        if action:
            action.setText(i18n("Print Source..."))
        # activate completion
        iface = self.view.codeCompletionInterface()
        if iface:
            iface.registerCompletionModel(self.completionModel())

    @cacheresult
    def completionModel(self):
        return CompletionModel(self)
        
    def contextMenu(self):
        menu = KMenu(self.view)
        menu.aboutToShow.connect(self.populateContextMenu)
        return menu
        
    def populateContextMenu(self):
        self.manipulator().populateContextMenu(self.view.contextMenu())
    
    def aboutToClose(self):
        self.resetLocalFileManager()
    
    def setCursorPosition(self, line, column, translate=True):
        shiftPressed = KApplication.keyboardModifiers() & Qt.ShiftModifier
        if self.view:
            if shiftPressed:
                # select from the current cursor position.
                start = self.view.cursorPosition()
            else:
                self.view.removeSelection()
        super(Document, self).setCursorPosition(line, column, translate)
        if self.view and shiftPressed:
            end = self.view.cursorPosition()
            self.view.setSelection(KTextEditor.Range(start, end))
            self.manipulator().adjustSelectionToChords()
    
    def variables(self):
        """Returns a dictionary with variables put in specially formatted LilyPond
        comments, like:
        %%varname: value
        (double percent at start of line, varname, colon and value).
        
        Varname should consist of lowercase letters, and may contain (but not
        end or start with) single hyphens.
        
        """
        return dict(_variables_re.findall(self.text()))
    
    def updatedFiles(self):
        """Returns a function that can list updated files based on extension.
        
        Checks the mode of the last LilyPond run (preview or not) and honors
        the %%master directives that would have been used by the Job.
        
        """
        if self.localFileManager():
            path = self.localFileManager().path()
        else:
            path = self.localPath()
            # look for %%master directives
            lvars = self.variables()
            ly = (lvars.get('master-preview' if self.metainfo["preview"]
                        else 'master-publish') or lvars.get('master'))
            if ly:
                path = os.path.join(os.path.dirname(path), ly)
        return updatedFiles(path)

    @cacheresult
    def manipulator(self):
        """Returns a singleton object for this document that can perform more
        advanced manipulations."""
        import frescobaldi_app.document
        return frescobaldi_app.document.DocumentManipulator(self)

    def currentIndent(self, cursor=None, checkColumn=True):
        """Returns the indent of the line the given cursor is on, or of the
        current line.
        
        If checkColumn is True (default), the indent returned is not deeper
        than the column the cursor is on.
        
        """
        if cursor is None:
            cursor = self.view.cursorPosition()
        text = self.line(cursor.line())
        if checkColumn:
            text = text[:cursor.column()]
        return len(re.match(r'\s*', text).group().expandtabs(self.tabWidth()))
        
    def indent(self, text, start = None, startscheme = False):
        """Convenience method to indent text according to settings of this
        document."""
        import ly.indent
        return ly.indent.indent(text,
            start = start,
            indentwidth = self.indentationWidth(),
            tabwidth = self.tabWidth(),
            usetabs = not self.indentationSpaces(),
            startscheme = startscheme,
            )

    def needsLocalFileManager(self):
        return self.url().isEmpty() or self.url().protocol() != "file"
        
    def localFileManager(self, create = False):
        if create and not self._localFileManager:
            import frescobaldi_app.runlily
            self._localFileManager = frescobaldi_app.runlily.LocalFileManager(self)
        return self._localFileManager

    def resetLocalFileManager(self):
        self._localFileManager = None

    def lilyPondVersion(self):
        """Returns the version of LilyPond this document uses (looking at
        the \version "x.x.x" statement).
        
        Returns None if the document does not specify a version.
        
        """
        import ly.version
        return ly.version.getVersion(self.text())


class SymbolManager(object):
    """Manages the LilyPond icons for objects like widgets and actions.
    
    Ensures that if the palette is changed, the icons are redrawn in the current
    foreground color. You can mixin this with a widget or just instantiate it
    and call the recolor method on palette changes (look at our changeEvent
    method for an example).
    
    """
    def __init__(self):
        # we store mapping obj->(icon_name, size) in a weak dict
        # objs that have a setIcon method
        self._objs = {}
        # objs that have a setItemIcon method: obj->(index, icon_name, size)
        self._itemobjs = {}
        # objs that need to have setIconSize called after drawing the icons
        self._sizeobjs = {}
        self._ownsize = None # must setIconSize() be called on us?
        # TODO: add support for models or objects with a special property
        self._defaultSize = 22
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.redrawSymbols)
        self.triggerRedraw()

    def addSymbol(self, obj, icon_name, size=0):
        self._objs[obj] = (icon_name, size)
    
    def addItemSymbol(self, obj, index, icon_name, size=0):
        self._itemobjs.setdefault(obj, []).append((index, icon_name, size))
        
    def setSymbolSize(self, obj, size):
        if obj is self:
            self._ownsize = size
        else:
            self._sizeobjs[obj] = size
        
    def defaultSymbolSize(self):
        return self._defaultSize
    
    def setDefaultSymbolSize(self, size):
        self._defaultSize = size
        
    def triggerRedraw(self, msecs = 0):
        self._timer.start(msecs)
        
    def redrawSymbols(self):
        for obj, (icon_name, size) in self._objs.items()[:]: # copy
            try:
                obj.setIcon(self.symbolIcon(icon_name, size))
            except RuntimeError: # underlying C/C++ object has been deleted
                del self._objs[obj]
        for obj, items in self._itemobjs.items()[:]: # copy
            try:
                for index, icon_name, size in items:
                    obj.setItemIcon(index, self.symbolIcon(icon_name, size))
            except RuntimeError:  # underlying C/C++ object has been deleted
                del self._itemobjs[obj]
        for obj, size in self._sizeobjs.items()[:]: # copy
            try:
                obj.setIconSize(QSize(size, size))
            except RuntimeError:  # underlying C/C++ object has been deleted
                del self._sizeobjs[obj]
        if self._ownsize:
            try:
                self.setIconSize(QSize(self._ownsize, self._ownsize))
            except RuntimeError:  # underlying C/C++ object has been deleted
                self._ownsize = None
            
    def symbolIcon(self, name, size=0):
        size = size or self._defaultSize
        pixmap = KIconLoader.global_().loadIcon(name, KIconLoader.User, size) 
        alpha = pixmap.alphaChannel()
        pixmap.fill(KApplication.palette().color(QPalette.ButtonText))
        pixmap.setAlphaChannel(alpha)
        return QIcon(pixmap)
        
    def changeEvent(self, ev):
        """
        Respond to events, in particular palette events,
        to recolor LilyPond symbol icons.
        """
        if ev.type() == QEvent.PaletteChange:
            self.triggerRedraw()


class MainWindow(SymbolManager, kateshell.mainwindow.MainWindow):
    """ Our customized Frescobaldi MainWindow """
    
    # called when Apply or Ok is clicked in the settings dialog.
    settingsChanged = Signal()
    
    def __init__(self, app):
        SymbolManager.__init__(self)
        kateshell.mainwindow.MainWindow.__init__(self, app)
        self.progressBar = QProgressBar()
        self.progressBar.setMaximumHeight(16)
        self.statusBar().addPermanentWidget(self.progressBar)
        self.progressBar.hide()
        self.currentDocumentChanged.connect(self.updateJobActions)
        self.expansionShortcuts = ExpansionShortcuts(self)
        self.charSelectShortcuts = CharSelectShortcuts(self)
        self.quickInsertShortcuts = QuickInsertShortcuts(self)
        self.jobManager().jobFinished.connect(self.setDocumentStatus)
        self.jobManager().jobFinished.connect(self.notifyCompileFinished)
        
    @cacheresult
    def actionManager(self):
        """Returns the ActionManager, managing actions that can be performed
        on files creating by LilyPond."""
        import frescobaldi_app.actions
        return frescobaldi_app.actions.ActionManager(self)
        
    @cacheresult
    def scoreWizard(self):
        with self.app.busyCursor():
            import frescobaldi_app.scorewiz
            return frescobaldi_app.scorewiz.ScoreWizard(self)
    
    @cacheresult
    def applyRhythmDialog(self):
        return ApplyRhythmDialog(self)
    
    @cacheresult
    def expandManager(self):
        import frescobaldi_app.expand
        return frescobaldi_app.expand.ExpandManager(self)
    
    @cacheresult
    def jobManager(self):
        man = JobManager()
        man.jobStarted.connect(self.updateJobActions)
        man.jobFinished.connect(self.updateJobActions)
        man.jobStarted.connect(self.setTabIcons)
        man.jobFinished.connect(self.setTabIcons)
        return man
    
    @cacheresult
    def runLilyPondDialog(self):
        import frescobaldi_app.runlily
        return frescobaldi_app.runlily.RunLilyPondDialog(self)
    
    @cacheresult
    def progressBarManager(self):
        import frescobaldi_app.progress
        return frescobaldi_app.progress.ProgressBarManager(self.jobManager(),
            self.progressBar)
    
    @cacheresult
    def blankStaffPaperWizard(self):
        with self.app.busyCursor():
            import frescobaldi_app.blankpaper
            return frescobaldi_app.blankpaper.Dialog(self)
        
    @cacheresult
    def charSelectDialog(self):
        with self.app.busyCursor():
            import frescobaldi_app.charselect
            return frescobaldi_app.charselect.Dialog(self)
        
    def createSessionManager(self):
        """Reimplemented from kateshell.mainwindow.MainWindow"""
        return SessionManager(self)
    
    def setupActions(self):
        super(MainWindow, self).setupActions()
        
        # LilyPond runner toolbar icon
        @self.onAction(i18n("LilyPond"), "run-lilypond")
        def lilypond_runner():
            d = self.currentDocument()
            if d:
                if KApplication.keyboardModifiers() & Qt.ShiftModifier:
                    self.runLilyPond("custom")
                else:
                    job = self.jobManager().job(d)
                    job.abort() if job else self.runLilyPond("preview")

        # Score wizard
        @self.onAction(i18n("Setup New Score..."), "text-x-lilypond",
            key="Ctrl+Shift+N")
        def lilypond_score_wizard():
            self.scoreWizard().show()
        
        # run LilyPond actions
        @self.onAction(i18n("Run LilyPond (preview)"), "run-lilypond",
            key="Ctrl+M")
        def lilypond_run_preview():
            self.runLilyPond("preview")
            
        @self.onAction(i18n("Run LilyPond (publish)"), "run-lilypond",
            key="Ctrl+Alt+P")
        def lilypond_run_publish():
            self.runLilyPond("publish")
        
        @self.onAction(i18n("Run LilyPond (custom)..."), "run-lilypond",
            key="Shift+Ctrl+M")
        def lilypond_run_custom():
            self.runLilyPond("custom")
        
        @self.onAction(i18n("Interrupt LilyPond Job"), "process-stop")
        def lilypond_abort():
            d = self.currentDocument()
            if d:
                job = self.jobManager().job(d)
                if job:
                    job.abort()
        
        # File menu actions:
        @self.onAction(i18n("Print Music..."), "document-print",
            key="Ctrl+Shift+P")
        def file_print_music():
            d = self.currentDocument()
            self.actionManager().print_(d.updatedFiles())
        
        @self.onAction(i18n("Email Documents..."), "mail-send", key="Ctrl+E")
        def file_email_documents():
            d = self.currentDocument()
            self.actionManager().email(d.updatedFiles(), d.metainfo["preview"])
        
        # Edit menu actions:
        @self.onSelAction(i18n("Cut and Assign"), "edit-cut",
            key="Ctrl+Shift+C", tooltip=i18n(
                "Cut selection and assign it to a LilyPond variable."))
        def edit_cut_assign(text):
            self.currentDocument().manipulator().assignSelectionToVariable()
        
        @self.onAction(i18n("Repeat last note or chord"), key="Ctrl+;",
            tooltip=i18n("Repeat the last music expression (note or chord)."))
        def edit_repeat_last():
            self.currentDocument().manipulator().repeatLastExpression()
            
        @self.onAction(i18n("Insert or Manage Expansions..."), key="Ctrl+.",
            tooltip=i18n("Expand last word or open the expansions dialog."))
        def edit_expand():
            self.expandManager().expand()
        
        @self.onAction(i18n("Special Characters..."), "accessories-character-map",
            key="Ctrl+Y", tooltip=i18n("Insert special characters."))
        def edit_insert_specialchars():
            self.charSelectDialog().show()
        
        # (this action is currently only displayed in the contextmenu)
        @self.onSelAction(i18n("Add to Expansions"), "list-add")
        def edit_expand_add(text):
            self.expandManager().addExpansion(text)
        
        @self.onAction(i18n("Next blank line"), "go-down-search", key="Alt+Down",
            tooltip=i18n("Go to the next blank line."))
        def edit_next_blank_line():
            d = self.currentDocument()
            for num in range(d.view.cursorPosition().line(), d.doc.lines() - 1):
                if not isblank(d.line(num)) and isblank(d.line(num + 1)):
                    d.view.setCursorPosition(
                        KTextEditor.Cursor(num + 1, len(d.line(num + 1))))
                    d.view.removeSelection()
                    return
        
        @self.onAction(i18n("Previous blank line"), "go-up-search", key="Alt+Up",
            tooltip=i18n("Go to the previous blank line."))
        def edit_prev_blank_line():
            d = self.currentDocument()
            for num in range(d.view.cursorPosition().line() - 1, -1, -1):
                if isblank(d.line(num)) and (num == 0 or not isblank(d.line(num - 1))):
                    d.view.setCursorPosition(KTextEditor.Cursor(num, len(d.line(num))))
                    d.view.removeSelection()
                    return
        
        @self.onAction(i18n("Select to next blank line"), key="Shift+Alt+Down",
            tooltip=i18n(
                "Selects text from the current position down to and "
                "including the next blank line."))
        def edit_select_next_blank_line():
            d = self.currentDocument()
            cursor = d.view.cursorPosition()
            for num in range(cursor.line() + 1, d.doc.lines() - 2):
                if isblank(d.line(num)) and not isblank(d.line(num + 1)):
                    newcur = KTextEditor.Cursor(num + 1, 0)
                    break
            else:
                docRange = d.doc.documentRange()
                newcur = docRange.end()
            if d.view.selection():
                r = d.view.selectionRange()
                if cursor.position() == r.start().position():
                    cursor = r.end()
                elif cursor.position() == r.end().position():
                    cursor = r.start()
            else:
                line = cursor.line()
                while line < d.doc.lines() and isblank(d.line(line)):
                    line += 1
                cursor.setLine(line)
            d.view.setSelection(KTextEditor.Range(cursor, newcur))
            d.view.setCursorPosition(newcur)
        
        @self.onAction(i18n("Select to previous blank line"), key="Shift+Alt+Up",
            tooltip=i18n(
                "Selects text from the current position up to right after the "
                "previous blank line."))
        def edit_select_previous_blank_line():
            d = self.currentDocument()
            cursor = d.view.cursorPosition()
            for num in range(cursor.line() - 2, -1, -1):
                if isblank(d.line(num)) and not isblank(d.line(num + 1)):
                    newcur = KTextEditor.Cursor(num + 1, 0)
                    break
            else:
                newcur = KTextEditor.Cursor(0, 0)
            if d.view.selection():
                r = d.view.selectionRange()
                if cursor.position() == r.start().position():
                    cursor = r.end()
                elif cursor.position() == r.end().position():
                    cursor = r.start()
            else:
                line = cursor.line()
                if line < d.doc.lines() - 1 and isblank(d.line(line)):
                    line += 1
                cursor.setLine(line)
            d.view.setSelection(KTextEditor.Range(cursor, newcur))
            d.view.setCursorPosition(newcur)
        
        @self.onSelAction(i18n("Move selection to next blank line"),
            key="Shift+Alt+Ctrl+Down",
            tooltip=i18n("Moves selected block to next blank line."))
        def edit_moveto_next_blank_line(text):
            self.currentDocument().manipulator().moveSelectionDown()
        
        @self.onSelAction(i18n("Move selection to previous blank line"),
            key="Shift+Alt+Ctrl+Up",
            tooltip=i18n("Moves selected block to previous blank line."))
        def edit_moveto_previous_blank_line(text):
            self.currentDocument().manipulator().moveSelectionUp()
        
        # Generated files menu:
        a = KActionMenu(KIcon("media-playback-start"), i18n("Play/View"), self)
        self.actionCollection().addAction('lilypond_actions', a)
        a.setDelayed(False)
        def makefunc(action):
            def populateMenu():
                menu = action.menu()
                menu.clear()
                doc = self.currentDocument()
                if not doc:
                    return
                self.actionManager().addActionsToMenu(doc.updatedFiles(), menu)
            return populateMenu
        a.menu().aboutToShow.connect(makefunc(a))
            
        # actions and functionality for editing pitches
        a = KActionMenu(KIcon("applications-education-language"),
                i18n("Pitch Name Language"), self)
        a.setToolTip(i18n("Change the LilyPond language used for pitch names "
                          "in this document or in the selection."))
        self.actionCollection().addAction('pitch_change_language', a)
        a.menu().aboutToShow.connect((lambda action:
            lambda: self.currentDocument().manipulator().populateLanguageMenu(
                action.menu()))(a))
        
        @self.onAction(i18n("Convert Relative to &Absolute"), tooltip=i18n(
            "Converts the notes in the document or selection from relative to "
            "absolute pitch."))
        def pitch_relative_to_absolute():
            self.currentDocument().manipulator().convertRelativeToAbsolute()
            
        @self.onAction(i18n("Convert Absolute to &Relative"), tooltip=i18n(
            "Converts the notes in the document or selection from absolute to "
            "relative pitch."))
        def pitch_absolute_to_relative():
            self.currentDocument().manipulator().convertAbsoluteToRelative()

        @self.onAction(i18n("Transpose..."), tooltip=i18n(
            "Transposes all notes in the document or selection."))
        def pitch_transpose():
            self.currentDocument().manipulator().transpose()
        
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
            
        @self.onSelAction(i18n("Undot durations"), tooltip=i18n(
            "Remove one dot from all the durations in the selection."))
        def durations_undot(text):
            import ly.duration
            return ly.duration.undotDurations(text)
            
        @self.onSelAction(i18n("Remove scaling"), tooltip=i18n(
            "Remove all scaling (*n/m) from the durations in the selection."))
        def durations_remove_scaling(text):
            import ly.duration
            return ly.duration.removeScaling(text)
            
        @self.onSelAction(i18n("Remove durations"),
            tooltip=i18n("Remove all durations from the selection."))
        def durations_remove(text):
            import ly.duration
            return ly.duration.removeDurations(text)
            
        @self.onSelAction(i18n("Make implicit"), tooltip=i18n(
            "Make durations implicit (remove repeated durations)."))
        def durations_implicit(text):
            import ly.duration
            return ly.duration.makeImplicit(text)
            
        @self.onSelAction(i18n("Make implicit (per line)"), tooltip=i18n(
            "Make durations implicit (remove repeated durations), "
            "except for the first duration in a line."))
        def durations_implicit_per_line(text):
            import ly.duration
            return ly.duration.makeImplicitPerLine(text)
            
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
            rhythm = KApplication.clipboard().text()
            return ly.duration.applyRhythm(text, rhythm)
        
        # Setup lyrics hyphen and de-hyphen action
        @self.onSelAction(i18n("Hyphenate Lyrics Text"), keepSelection=False,
            key="Ctrl+L")
        def lyrics_hyphen(text):
            import frescobaldi_app.hyphen
            return frescobaldi_app.hyphen.hyphenate(text, self)
            
        @self.onSelAction(i18n("Remove hyphenation"), keepSelection=False)
        def lyrics_dehyphen(text):
            return text.replace(' -- ', '')
        
        @self.onSelAction(i18n("Copy Lyrics with hyphenation removed"),
            keepSelection=False)
        def lyrics_copy_dehyphen(text):
            KApplication.clipboard().setText(text.replace(' -- ', ''))
        
        # Other actions
        @self.onAction(i18n("Single Quote"), key="Ctrl+'")
        def insert_quote_single():
            self.currentDocument().manipulator().insertTypographicalQuote()
            
        @self.onAction(i18n("Double Quote"), key='Ctrl+"')
        def insert_quote_double():
            self.currentDocument().manipulator().insertTypographicalQuote(True)

        @self.onAction(i18n("Align"), "format-indent-more")
        def source_indent():
            self.currentDocument().manipulator().indent()
        
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
    
        # Settings
        @self.onAction(KStandardAction.Preferences)
        def options_configure():
            with self.app.busyCursor():
                import frescobaldi_app.settings
                frescobaldi_app.settings.SettingsDialog(self).show()
        
        @self.onSelAction(i18n("Repeat selected music"), key="Ctrl+Shift+R",
            keepSelection=False)
        def edit_repeat(text):
            return self.currentDocument().manipulator().wrapSelection(text, 
                "\\repeat volta 2 {")
        
        @self.onAction(i18n("Insert pair of braces"), "code-context",
            key="Ctrl+{")
        def edit_insert_braces():
            d = self.currentDocument()
            if d.selectionText():
                d.replaceSelectionWith(d.manipulator().wrapSelection(
                    d.selectionText()), keepSelection=False)
            else:
                self.currentDocument().manipulator().insertTemplate("{\n(|)\n}")
        
        # Other wizards/tools:
        @self.onAction(i18n("Create blank staff paper"), "text-plain")
        def wizard_blank_staff_paper():
            self.blankStaffPaperWizard().show()

    def setupTools(self):
        QuickInsertTool(self)
        KonsoleTool(self)
        LogTool(self)
        KMidTool(self)
        RumorTool(self)
        PDFTool(self)
        LilyDocTool(self)
            
    def runLilyPond(self, mode):
        """Run LilyPond on the current document.
        
        mode is "preview", "publish" or "custom".
        For "custom", a dialog is opened where the user can adjust the
        parameters for the LilyPond run (such as which version to use).
        
        """
        d = self.currentDocument()
        if not d:
            return
        if d.url().protocol() == "file" and d.isModified() and not (
            KMessageBox.warningContinueCancel(self, i18n(
                "Your document has been modified and needs to be saved before "
                "LilyPond can be started.\n\n"
                "Save the document now?"), None,
                KStandardGuiItem.save(), KStandardGuiItem.cancel(),
                "save_on_run") == KMessageBox.Continue and d.save()):
            return # cancelled save of local file
        
        # create a Job
        import frescobaldi_app.runlily
        job = frescobaldi_app.runlily.DocumentJob(d)
        
        # configure this Job
        job.preview = False
        if mode == "custom":
            if not self.runLilyPondDialog().configureJob(job, d):
                return # job configure dialog cancelled by user
        else:
            job.preview = mode == "preview"
            # forces the session a certain version?
            command = self.sessionManager().lilyPondCommand()
            if not command:
                if config("lilypond").readEntry("automatic version", False):
                    docVersion = d.lilyPondVersion()
                    if docVersion:
                        command = automaticLilyPondCommand(docVersion)
            job.command = command or lilyPondCommand()
            
        # check if there is not already a job running. We do it now, so the
        # custom dialog can be requested even when there is a job running.
        if self.jobManager().job(d):
            return KMessageBox.sorry(self, i18n(
                "There is already a LilyPond job running "
                "for this document."), i18n("Can't process document"))
        
        # check if the user has a forced point and click setting in the file
        text = d.text()
        import ly.rx
        for m in ly.rx.point_and_click.finditer(text):
            if m.group(1) or m.group(2):
                on, off = m.start(1), m.start(2)
                ask = lambda msg: KMessageBox.warningContinueCancel(self,
                    "<p>{0}</p><p>{1}</p>".format(msg, i18n("Continue anyway?")),
                    None, KStandardGuiItem.cont(), KStandardGuiItem.cancel(),
                    "point_and_click") == KMessageBox.Continue
                if ((job.preview and off >= 0 and not ask(i18n(
                    "You want to run LilyPond in preview mode (with point and "
                    "click enabled), but your document contains a command to "
                    "turn point and click off."))) or
                    (not job.preview and on >= 0 and not ask(i18n(
                    "You want to run LilyPond in publish mode (with point and "
                    "click disabled), but your document contains a command to "
                    "turn point and click on.")))):
                    # cancelled
                    # put the cursor at the point and click command
                    import frescobaldi_app.document
                    cursor = frescobaldi_app.document.Cursor()
                    cursor.walk(text[:m.start()])
                    d.view.setCursorPosition(cursor.kteCursor())
                    return
                    
        # init the progress bar (only done once)
        self.progressBarManager()
        # run the LilyPond Job
        self.jobManager().run(job)
        
    def updateJobActions(self):
        """Called when the current document (or its status) has changed."""
        doc = self.currentDocument()
        running = bool(doc and self.jobManager().job(doc))
        act = self.actionCollection().action
        act("lilypond_run_preview").setEnabled(not running)
        act("lilypond_run_publish").setEnabled(not running)
        act("lilypond_abort").setEnabled(running)
        if running:
            icon = "process-stop"
            tip = i18n("Abort the running LilyPond process")
        else:
            icon = "run-lilypond"
            tip = i18n("Run LilyPond in preview mode "
                       "(Shift-click for custom dialog)")
        act("lilypond_runner").setIcon(KIcon(icon))
        act("lilypond_runner").setToolTip(tip)
    
    def setTabIcons(self, job):
        """Called on start/stop of a job, to update the icon in the tab bar."""
        self.viewTabs.setDocumentStatus(job.document)
    
    def setDocumentStatus(self, job, success):
        """Called when a job exits. """
        doc = job.document
        # reset cursor position translations if LilyPond created a new PDF
        if job.updatedFiles()("pdf"):
            doc.resetCursorTranslations()
        # remember if the last run used point and click or not
        doc.metainfo["preview"] = job.preview
        
    def allActionCollections(self):
        for name, coll in super(MainWindow, self).allActionCollections():
            yield name, coll
        yield i18n("Expansion Manager"), self.expansionShortcuts.actionCollection()
        yield i18n("Special Characters"), self.charSelectShortcuts.actionCollection()
        yield i18n("Quick Insert"), self.quickInsertShortcuts.actionCollection()
        
    def saveSettings(self):
        self.app.stateManager().cleanup()
        super(MainWindow, self).saveSettings()

    def notifyCompileFinished(self, job, success):
        """Called when a job exits, notify the user on longer compiles."""
        if job.buildTime >= 10 and self.isMinimized():
            n = KNotification("compileFinished", self)
            if success:
                n.setText(i18n(
                    "LilyPond has successfully compiled %1.",
                    job.document.documentName()))
            else:
                n.setText(i18n(
                    "LilyPond exited with an error compiling %1.",
                    job.document.documentName()))
            n.sendEvent()


class ApplyRhythmDialog(KDialog):
    def __init__(self, mainwin):
        KDialog.__init__(self, mainwin)
        self.setCaption(i18n("Apply Rhythm"))
        self.setButtons(KDialog.ButtonCode(
            KDialog.Ok | KDialog.Apply | KDialog.Cancel | KDialog.Help))
        self.setHelp("rhythm")
        self.setModal(True)
        v = KVBox(self)
        v.setSpacing(4)
        self.setMainWidget(v)
        QLabel(i18n("Enter a rhythm:"), v)
        self.lineedit = KLineEdit(v)
        self.lineedit.setToolTip(i18n(
            "Enter a rhythm using space separated duration values "
            "(e.g. 8. 16 8 4 8)"))
        self.applyClicked.connect(self.doApply)
        self.okClicked.connect(self.doApply)

    def doApply(self):
        import ly.duration
        self.lineedit.completionObject().addItem(self.lineedit.text())
        self.parent().currentDocument().replaceSelectionWith(
            ly.duration.applyRhythm(self.text, self.lineedit.text()))

    def edit(self, text):
        self.text = text
        self.show()
        self.lineedit.setFocus()
        self.lineedit.selectAll()


class KonsoleTool(kateshell.mainwindow.KPartTool):
    """ A tool embedding a Konsole """
    _partlibrary = "libkonsolepart"
    _partappname = "Konsole"
    def __init__(self, mainwin):
        import PyKDE4
        kde_4_5_or_higher = PyKDE4.kdecore.version() >= 263424
        icon = "utilities-terminal" if kde_4_5_or_higher else "terminal"
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "konsole", i18n("Terminal"), icon,
            key="Meta+Alt+T", dock=kateshell.mainwindow.Bottom)
        mainwin.currentDocumentChanged.connect(self.sync)
            
    def partLoaded(self):
        d = self.mainwin.currentDocument()
        if d and not d.url().isEmpty():
            url = d.url()
        else:
            url = KUrl.fromPath(
                self.mainwin.app.defaultDirectory() or os.getcwd())
        self.openUrl(url)

    def slotAction(self):
        if self.part and self.isActive() and not self.widget.hasFocus():
            self.widget.setFocus()
        else:
            self.toggle()
    
    def show(self):
        super(KonsoleTool, self).show()
        if self.part:
            self.widget.setFocus()
        
    def sync(self, doc):
        if (self.part and self._sync
            and doc and doc.doc and not doc.url().isEmpty()):
            # FIXME This does not work currently.
            self.openUrl(doc.url())

    def addMenuActions(self, m):
        a = m.addAction(i18n("S&ynchronize Terminal with Current Document"))
        a.setCheckable(True)
        a.setChecked(self._sync)
        a.triggered.connect(self.toggleSync)
        
    def toggleSync(self):
        self._sync = not self._sync

    def readConfig(self, conf):
        self._sync = conf.readEntry("sync", False)

    def writeConfig(self, conf):
        conf.writeEntry("sync", self._sync)
        

class KMidTool(kateshell.mainwindow.Tool):
    helpAnchor = "kmid"
    def __init__(self, mainwin):
        self.failed = False # failed the player to load?
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "kmid", i18n("MIDI Player"), "audio-midi",
            key="Meta+Alt+M", dock=kateshell.mainwindow.Bottom)
        
    def factory(self):
        import frescobaldi_app.kmid
        player = frescobaldi_app.kmid.player(self)
        if player:
            return player
        self.failed = True
        label = QLabel(i18n(
            "Could not load the KMid part.\n"
            "Please install KMid 2.4.0 or higher."))
        label.setAlignment(Qt.AlignCenter)
        return label


class PDFTool(kateshell.mainwindow.KPartTool):
    _partlibrary = "okularpart"
    _partappname = "Okular"
    def __init__(self, mainwin):
        self._config = {}
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "pdf", i18n("PDF Preview"), "application-pdf",
            key="Meta+Alt+P", dock=kateshell.mainwindow.Right)
        self._urlToOpen = None
        self._currentUrl = None
        # We open urls with a timer otherwise Okular is called 
        # too quickly when the user switches documents too fast.
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.timeoutFunc)
        mainwin.aboutToClose.connect(self.appQuit)
        if self._config["sync"]:
            mainwin.currentDocumentChanged.connect(self.sync)
            mainwin.jobManager().jobFinished.connect(self.openUpdatedPDF)
    
    def appQuit(self):
        """ Called when the application exits. """
        self._timer.stop()
        self.part and self.part.closeUrl()
        
    def timeoutFunc(self):
        """(Internal) Called when the timer times out.
        
        If an url was recorded, it is opened now.
        
        """
        if self._urlToOpen:
            super(PDFTool, self).openUrl(self._urlToOpen)
            self._urlToOpen = None
            self._timer.start(500)

    def _reallyOpenUrl(self, url):
        """(Internal) Opens the url and starts a timer to prevent it from being
        called too quickly again.
        
        If the timer is already running, the url is recorded and opened on
        timeout().
        
        """
        self._urlToOpen = url
        self._timer.isActive() or self._timer.start(0)
        
    def openUrl(self, url):
        """ Expects KUrl."""
        if not self.failed:
            self.show()
            if url != self._currentUrl:
                self._currentUrl = url
                self._reallyOpenUrl(url)
    
    def reloadUrl(self):
        if self._currentUrl:
            self._reallyOpenUrl(self._currentUrl)
            
    def sync(self, doc):
        pdfs = doc.updatedFiles()("pdf")
        if pdfs:
            self.openUrl(KUrl(pdfs[0]))

    def openUpdatedPDF(self, job):
        pdfs = job.updatedFiles()("pdf")
        if pdfs:
            self.openUrl(KUrl(pdfs[0]))
        
    def addMenuActions(self, m):
        def act(name, title):
            a = m.addAction(title)
            a.setCheckable(True)
            a.setChecked(self._config[name])
            a.triggered.connect(lambda: self.toggleAction(name))
        act("leftpanel", i18n("Show PDF Navigation Panel"))
        act("minipager", i18n("Show PDF minipager"))
        a = m.addAction(KIcon("configure"), i18n("Configure Okular..."))
        a.triggered.connect(self.openOkularSettings)
        m.addSeparator()
        act("sync", i18n("S&ynchronize Preview with Current Document"))
        a = m.addAction(KIcon("view-refresh"), i18n("Reload"))
        a.triggered.connect(self.reloadUrl)
        a.setEnabled(bool(self._currentUrl))

    def openOkularSettings(self):
        self.materialize()
        if self.part:
            a = self.part.actionCollection().action("options_configure")
            if a:
                a.trigger()
                
    def toggleAction(self, name):
        c = self._config[name] = not self._config[name]
        # if the part has already loaded, perform these settings.
        if name == "leftpanel" and self.part:
            self.part.actionCollection().action("show_leftpanel").setChecked(c)
        elif name == "minipager" and self.part:
            self._okularMiniBar().setVisible(c)
        elif name == "sync":
            if c:
                self.mainwin.currentDocumentChanged.connect(self.sync)
                self.mainwin.jobManager().jobFinished.connect(self.openUpdatedPDF)
                d = self.mainwin.currentDocument()
                if d:
                    self.sync(d)
            else:
                self.mainwin.currentDocumentChanged.disconnect(self.sync)
                self.mainwin.jobManager().jobFinished.disconnect(self.openUpdatedPDF)

    def _okularMiniBar(self):
        """ get the okular miniBar """
        return self.part.widget().findChild(QWidget, "miniBar").parent()
        
    def partLoaded(self):
        if not self._config["minipager"]:
            self._okularMiniBar().hide()
        self.part.actionCollection().action("show_leftpanel").setChecked(
            self._config["leftpanel"])
        # change shortcut context for actions that conflict with Kate's
        for action in "view_scroll_up", "view_scroll_down", "close_find_bar":
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
            self._config[name] = conf.readEntry(name, default)
            
    def writeConfig(self, conf):
        for name in "minipager", "leftpanel", "sync":
            conf.writeEntry(name, self._config[name])
        
        
class QuickInsertTool(kateshell.mainwindow.Tool):
    helpAnchor = "quickinsert"
    defaultWidth = 160
    def __init__(self, mainwin):
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "quickinsert", i18n("Quick Insert"), "document-properties",
            key="Meta+Alt+I", dock=kateshell.mainwindow.Left)
            
    def factory(self):
        import frescobaldi_app.lqi
        return frescobaldi_app.lqi.QuickInsertPanel(self)


class LogTool(kateshell.mainwindow.Tool):
    def __init__(self, mainwin):
        self._config = {}
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "log", i18n("LilyPond Log"), "run-lilypond",
            key="Meta+Alt+L", dock=kateshell.mainwindow.Bottom,
            widget=QStackedWidget())
        self.logs = {}
        label = QLabel("({0})".format(i18n("no log")))
        label.setAlignment(Qt.AlignCenter)
        self.widget.addWidget(label)
        mainwin.currentDocumentChanged.connect(self.showLog)
        mainwin.app.documentClosed.connect(self.removeLog)
        self.widget.destroyed.connect(lambda: self.logs.clear())
        mainwin.jobManager().jobStarted.connect(self.startJob)
        mainwin.jobManager().jobFinished.connect(self.finishJob)
        
    def showLog(self, doc):
        if doc in self.logs:
            self.widget.setCurrentWidget(self.logs[doc])
            
    def log(self, doc):
        return self.logs.get(doc)
        
    def createLog(self, doc):
        if doc not in self.logs:
            from frescobaldi_app.runlily import Log
            self.logs[doc] = Log(self, doc)
            self.widget.addWidget(self.logs[doc])
        self.showLog(doc)
        if not self._config["errors only"]:
            self.show()
        return self.logs[doc]

    def removeLog(self, doc):
        if doc in self.logs:
            sip.delete(self.logs[doc])
            del self.logs[doc]
            if self.widget.count() == 1:
                if not self._docked:
                    self.dock()
                self.hide()
    
    def startJob(self, job):
        log = self.createLog(job.document)
        log.clear()
        job.output.connect(log)
    
    def finishJob(self, job, success):
        log = self.log(job.document)
        if log and not success:
            log.show() # even if LP didn't show an error location
        
    def addMenuActions(self, m):
        def act(name, title):
            a = m.addAction(title)
            a.setCheckable(True)
            a.setChecked(self._config[name])
            a.triggered.connect(lambda: self.toggleAction(name))
        act("errors only", i18n("Only show on errors"))
        # context menu options of the Log, if there...
        # (check it without importing runlily module)
        if hasattr(self.widget.currentWidget(), "addContextMenuActions"):
            self.widget.currentWidget().addContextMenuActions(m)
        
    def toggleAction(self, name):
        self._config[name] = not self._config[name]
        
    def readConfig(self, conf):
        for name, default in (
            ("errors only", False),
            ):
            self._config[name] = conf.readEntry(name, default)
            
    def writeConfig(self, conf):
        for name in ("errors only",):
            conf.writeEntry(name, self._config[name])
        

class RumorTool(kateshell.mainwindow.Tool):
    helpAnchor = "rumor"
    def __init__(self, mainwin):
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "rumor", i18n("Rumor"), "media-record",
            key="Meta+Alt+R", dock=kateshell.mainwindow.Bottom)
            
    def factory(self):
        import frescobaldi_app.rumor
        return frescobaldi_app.rumor.RumorPanel(self)


class LilyDocTool(kateshell.mainwindow.Tool):
    helpAnchor = "lilydoc"
    def __init__(self, mainwin):
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "lilydoc", i18n("LilyPond Documentation"), "lilydoc",
            key="Meta+Alt+D", dock=kateshell.mainwindow.Right)
        self._docFinder = None
        
    def factory(self):
        self.docFinder()
        import frescobaldi_app.lilydoc
        return frescobaldi_app.lilydoc.LilyDoc(self)

    def docFinder(self):
        if self._docFinder is None:
            self.newDocFinder()
        return self._docFinder
        
    def newDocFinder(self):
        import frescobaldi_app.lilydoc
        self._docFinder = frescobaldi_app.lilydoc.DocFinder(self)
        
    def openUrl(self, url):
        self.materialize()
        self.widget.openUrl(url)
        self.show()


class JobManager(object):
    """Manages running LilyPond jobs.
    
    Emits:
    jobStarted(job)
    jobFinished(job, success)
    
    """
    jobStarted = Signal()
    jobFinished = Signal()
    
    def __init__(self):
        self.jobs = {}
        
    def job(self, doc):
        """Returns the job running for the given document.
        
        Returns None if no job is running.
        
        """
        return self.jobs.get(doc)
    
    def count(self):
        """Returns the number of running jobs."""
        return len(self.jobs)
        
    def docs(self):
        """Returns a list of documents that have a LilyPond job running."""
        return self.jobs.keys()
    
    def run(self, job):
        """Runs a job.
        
        Adds the job to the list of running jobs, emits the jobStarted() signal,
        and calls the job.start() method. The jobFinished() signal is emitted
        when the job has finished.
        
        """
        if job.document in self.jobs:
            return
        self.jobs[job.document] = job
        job.done.connect(self._finished)
        self.jobStarted(job)
        job.start()
    
    def _finished(self, success, job):
        del self.jobs[job.document]
        self.jobFinished(job, success)


class CompletionModel(KTextEditor.CodeCompletionModel):
    def __init__(self, doc):
        KTextEditor.CodeCompletionModel.__init__(self, doc.view)
        self.doc = weakref.proxy(doc)
        self.result = None
        
    def completionInvoked(self, view, word, invocationType):
        import frescobaldi_app.completion
        self.result = frescobaldi_app.completion.getCompletions(
            self, view, word, invocationType)
        self.reset()
    
    def index(self, row, column, parent):
        return self.result.index(row, column, parent)
        
    def data(self, index, role):
        return self.result.data(index, role)
    
    def executeCompletionItem(self, doc, word, row):
        if not self.result.executeCompletionItem(doc, word, row):
            KTextEditor.CodeCompletionModel.executeCompletionItem(
                self, doc, word, row)
    
    def rowCount(self, parent):
        return self.result.rowCount(parent)


class ExpansionShortcuts(kateshell.mainwindow.UserShortcutManager):
    """Manages shortcuts for the expand dialog.
    
    This is setup initially so that keyboard shortcuts for expansions
    work without the expandManager being loaded. Pressing a keyboard
    shortcut actually loads the expansion manager to perform the action.
    
    """
    # which config group to store our shortcuts
    configGroup = "expand shortcuts"
    
    def widget(self):
        return self.mainwin.viewStack # where the text editor views are.
        
    def client(self):
        return self.mainwin.expandManager()


class CharSelectShortcuts(kateshell.mainwindow.UserShortcutManager):
    """Manages shortcuts for the charselect dialog."""
    configGroup = "charselect shortcuts"
    
    def widget(self):
        return self.mainwin.viewStack # where the text editor views are.
        
    def client(self):
        return self.mainwin.charSelectDialog()


class QuickInsertShortcuts(kateshell.mainwindow.UserShortcutManager):
    """Manages shortcuts for the Quick Insert panel."""
    configGroup = "quickinsert shortcuts"
    
    def widget(self):
        return self.mainwin.viewStack
        
    def client(self):
        tool = self.mainwin.tools["quickinsert"]
        tool.materialize()
        return tool.widget.toolboxWidget


class SessionManager(kateshell.mainwindow.SessionManager):
    def createEditorDialog(self):
        import frescobaldi_app.sessions
        return frescobaldi_app.sessions.EditorDialog(self)
    
    def lilyPondCommand(self):
        """Returns the LilyPond command for this session, if configured. """
        if self.current():
            return self.config().readEntry('lilypond', '')


# Easily get our global config
def config(group="preferences"):
    return KGlobal.config().group(group)
    
def lilyPondCommand():
    """ The default configured LilyPond command. """
    return config("lilypond").readEntry("default", "lilypond")
    
def lilyPondVersion(command = None):
    """The version of the LilyPond binary command.
    
    If no command is given, the default LilyPond command is used.
    
    """
    import ly.version
    return ly.version.LilyPondInstance(command or lilyPondCommand()).version()
    
def otherCommand(command, lilypond=None):
    """Returns the full path to the command (e.g. 'convert-ly') that belongs
    to the given or default lilypond command."""
    if not lilypond:
        lilypond = lilyPondCommand()
    cmd = config("lilypond").group(lilypond).readEntry(command, command)
    import ly.version
    return ly.version.LilyPondInstance(lilypond).path_to(cmd) or cmd
    
def convertLyCommand(lilypond=None):
    """Returns the convert-ly command belonging to the given (or default)
    lilypond command."""
    return otherCommand('convert-ly', lilypond)

def automaticLilyPondCommand(version):
    """Returns the LilyPond command that is suitable to compile a document
    with version version.
    
    The version argument should be a ly.version.Version instance.
    Returns None if no suitable LilyPond version is available.
    
    """
    # find the configured lilypond versions
    conf = config("lilypond")
    paths = conf.readEntry("paths", ["lilypond"])

    # remove paths for which Automatic selection is turned off
    paths = [p for p in paths if conf.group(p).readEntry("auto", True)]
    
    # get all versions
    import ly.version
    ver = dict((path, ly.version.LilyPondInstance(path).version())
        for path in paths)

    # sort on version
    paths.sort(key=ver.get)

    # return lowerst possible version
    for path in paths:
        if ver[path] >= version:
            return path

# determine updated files by a LilyPond process.
def updatedFiles(lyfile, reftime=None):
    """Returns a generator that yields updated files belonging to
    LilyPond document lyfile.
    
    Calling the returned generator with an extension (e.g. 'pdf') returns files
    newer than lyfile, with that extension.
    
    """
    import fnmatch
    if lyfile and os.path.exists(lyfile):
        if reftime is None:
            reftime = os.path.getmtime(lyfile)
        directory, name = os.path.split(lyfile)
        escname = re.escape(os.path.splitext(name)[0]) # remove ext, escape
        def generatorfunc(ext = "*"):
            ext = fnmatch.translate(ext.lstrip('.'))
            pat = re.compile(r'{0}(-[^-]+)*\.{1}'.format(escname, ext))
            try:
                files = [f for f in os.listdir(directory) if pat.match(f)]
            except OSError:
                return []
            files.sort(key=filenamekey)
            files = [os.path.join(directory, f) for f in files]
            return [f for f in files if os.path.getmtime(f) >= reftime]
    else:
        def generatorfunc(ext=None):
            return []
    generatorfunc.lyfile = lyfile
    return generatorfunc
    

# is string an empty or blank line?
def isblank(text):
    """True if text is empty or whitespace-only."""
    return not text or text.isspace()

def filenamekey(filename):
    """Returns a key for natural sorting file names containing numbers."""
    name, ext = os.path.splitext(filename)
    l = tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', name))
    return l, ext

