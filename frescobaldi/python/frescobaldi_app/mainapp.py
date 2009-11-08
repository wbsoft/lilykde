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

import os, re, sip, weakref
from dbus.service import method

from PyQt4.QtCore import (
    QEvent, QObject, QSize, QString, QTimer, QVariant, Qt, SIGNAL)
from PyQt4.QtGui import (
    QActionGroup, QColor, QIcon, QLabel, QPalette, QPixmap, QProgressBar,
    QStackedWidget, QWidget)
from PyKDE4.kdecore import KConfig, KGlobal, KUrl, i18n
from PyKDE4.kdeui import (
    KActionMenu, KApplication, KDialog, KIcon, KIconLoader, KLineEdit, KMenu,
    KMessageBox, KStandardAction, KVBox)
from PyKDE4.kparts import KParts
from PyKDE4.ktexteditor import KTextEditor

import kateshell.app, kateshell.mainwindow
from kateshell.app import lazymethod


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
        self.fileTypes = ["*.ly *.ily *.lyi|%s" % i18n("LilyPond files")]
        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = self.serviceName + '/MainApp'
        os.environ["FRESCOBALDI_PID"] = str(os.getpid())
        # check if stuff needs to be run after an update of Frescobaldi
        if self.version() != config("").readEntry("version", QVariant("0.0")).toString():
            from frescobaldi_app.install import install
            install(self)
        
    def openUrl(self, url, encoding=None):
        # The URL can be python string, dbus string or QString or KUrl
        if not isinstance(url, KUrl):
            url = KUrl(url)
        nav = False
        if url.protocol() == "textedit":
            m = re.match(r"^(.*):(\d+):(\d+):(\d+)$", unicode(url.path()))
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
    
    def findDocument(self, url):
        """
        Finds the document at KUrl url.
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
        return config().readEntry("save metainfo", QVariant(False)).toBool()


class Document(kateshell.app.Document):
    """ Our own Document type with LilyPond-specific features """
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
        # activate completion
        iface = self.view.codeCompletionInterface()
        if iface:
            iface.registerCompletionModel(self.completionModel())

    @lazymethod
    def completionModel(self):
        return CompletionModel(self)
        
    def contextMenu(self):
        menu = KMenu(self.view)
        QObject.connect(menu, SIGNAL("aboutToShow()"), self.populateContextMenu)
        return menu
        
    def populateContextMenu(self):
        self.manipulator().populateContextMenu(self.view.contextMenu())
    
    def aboutToClose(self):
        self.resetLocalFileManager()
    
    def setCursorPosition(self, line, column, translate=True):
        shiftPressed = KApplication.keyboardModifiers() & Qt.ShiftModifier
        if self.view and shiftPressed:
            # select from the current cursor position.
            start = self.view.cursorPosition()
        super(Document, self).setCursorPosition(line, column, translate)
        if self.view and shiftPressed:
            end = self.view.cursorPosition()
            self.view.setSelection(KTextEditor.Range(start, end))
            self.manipulator().fixSelection()
    
    def variables(self):
        """
        Returns a dictionary with variables put in specially formatted LilyPond
        comments, like:
        %%varname: value
        (double percent at start of line, varname, colon and value)
        Varname should consist of lowercase letters, and may contain (but not
        end or start with) single hyphens.
        """
        return dict(_variables_re.findall(self.text()))
    
    def updatedFiles(self):
        """
        Returns a function that can list updated files based on extension.
        """
        if self.localFileManager():
            path = self.localFileManager().path()
        else:
            path = self.localPath()
        return updatedFiles(path)

    @lazymethod
    def manipulator(self):
        """
        Returns a singleton object for this document that can
        perform more advanced manipulations.
        """
        import frescobaldi_app.document
        return frescobaldi_app.document.DocumentManipulator(self)

    def currentIndent(self, cursor=None, checkColumn=True):
        """
        Returns the indent of the line the given cursor is on, or
        of the current line.
        
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
        """
        Convenience method to indent text according to settings of this
        document.
        """
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


class SymbolManager(object):
    """
    Manages the LilyPond icons for objects like widgets and actions.
    
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
        QObject.connect(self._timer, SIGNAL("timeout()"), self.redrawSymbols)
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
    def __init__(self, app):
        SymbolManager.__init__(self)
        kateshell.mainwindow.MainWindow.__init__(self, app)
        self.progressBar = QProgressBar()
        self.progressBar.setMaximumHeight(16)
        self.statusBar().addPermanentWidget(self.progressBar)
        self.progressBar.hide()
        self.currentDocumentChanged.connect(self.updateJobActions)
    
    @lazymethod
    def actionManager(self):
        """
        Returns the ActionManager, managing actions that can be performed
        on files creating by LilyPond.
        """
        import frescobaldi_app.actions
        return frescobaldi_app.actions.ActionManager(self)
        
    @lazymethod
    def scoreWizard(self):
        import frescobaldi_app.scorewiz
        return frescobaldi_app.scorewiz.ScoreWizard(self)
    
    @lazymethod
    def applyRhythmDialog(self):
        return ApplyRhythmDialog(self)
    
    @lazymethod
    def expandManager(self):
        import frescobaldi_app.expand
        return frescobaldi_app.expand.ExpandManager(self)
    
    @lazymethod
    def jobManager(self):
        import frescobaldi_app.runlily
        man = frescobaldi_app.runlily.JobManager(self)
        man.jobStarted.connect(self.updateJobActions)
        man.jobFinished.connect(self.updateJobActions)
        self.progressBarManager(man) # show progress of jobs using progress bar
        man.jobStarted.connect(self.viewTabs.setDocumentStatus)
        man.jobFinished.connect(self.viewTabs.setDocumentStatus)
        return man
    
    @lazymethod
    def progressBarManager(self, jobmanager):
        import frescobaldi_app.progress
        return frescobaldi_app.progress.ProgressBarManager(jobmanager,
            self.progressBar)
    
    @lazymethod
    def blankStaffPaperWizard(self):
        import frescobaldi_app.blankpaper
        return frescobaldi_app.blankpaper.Dialog(self)
        
    def setupActions(self):
        super(MainWindow, self).setupActions()
        
        # LilyPond runner toolbar icon
        @self.onAction(i18n("LilyPond"), "run-lilypond")
        def lilypond_runner():
            d = self.currentDocument()
            if d:
                job = self.jobManager().job(d)
                if job:
                    job.abort()
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
            sorry = lambda msg: KMessageBox.sorry(self, msg,
                i18n("Can't process document"))
            if self.jobManager().job(d):
                return sorry(i18n(
                    "There is already a LilyPond job running "
                    "for this document."))
            if (d.url().protocol() == "file" and d.isModified()) and not (
                    config().readEntry("save on run", QVariant(False)).toBool()
                    and d.save()):
                return sorry(i18n(
                    "Your document has been modified, "
                    "please save first."))
            # Run LilyPond; get a LogWidget and create a job
            def finished(success, job):
                result = job.updatedFiles()
                pdfs = result("pdf")
                if pdfs:
                    if "pdf" in self.tools:
                        self.tools["pdf"].openUrl(KUrl(pdfs[0]))
                    d.resetCursorTranslations()
                log = self.tools["log"].log(d)
                if log:
                    self.actionManager().addActionsToLog(result, log)
                    if not success:
                        log.show() # even if LP didn't show an error location
            log = self.tools["log"].createLog(d)
            job = self.jobManager().createJob(d, log, preview)
            job.done.connect(finished)
        
        @self.onAction(i18n("Interrupt LilyPond Job"), "process-stop")
        def lilypond_abort():
            d = self.currentDocument()
            if d:
                job = self.jobManager().job(d)
                if job:
                    job.abort()
        
        # Edit menu actions:
        @self.onSelAction(i18n("Cut and Assign"), "edit-cut", key="Ctrl+Shift+C",
            tooltip=i18n("Cut selection and assign it to a LilyPond variable."))
        def edit_cut_assign(text):
            self.currentDocument().manipulator().assignSelectionToVariable()
        
        @self.onAction(i18n("Repeat last note or chord"), key="Ctrl+;",
            tooltip=i18n("Repeat the last music expression (note or chord)."))
        def edit_repeat_last():
            self.currentDocument().manipulator().repeatLastExpression()
            
        @self.onAction(i18n("Expand"), key="Ctrl+.",
            tooltip=i18n("Expand last word or open the expansions dialog."))
        def edit_expand():
            self.expandManager().expand()
        
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
            "Selects text from the current position down to and including the next blank line."))
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
            "Selects text from the current position up to right after the previous blank line."))
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
        
        @self.onSelAction(i18n("Move selection to next blank line"), key="Shift+Alt+Ctrl+Down",
            tooltip=i18n("Moves selected block to next blank line."))
        def edit_moveto_next_blank_line(text):
            self.currentDocument().manipulator().moveSelectionDown()
        
        @self.onSelAction(i18n("Move selection to previous blank line"), key="Shift+Alt+Ctrl+Up",
            tooltip=i18n("Moves selected block to previous blank line."))
        def edit_moveto_previous_blank_line(text):
            self.currentDocument().manipulator().moveSelectionUp()
        
        # actions and functionality for editing pitches
        a = KActionMenu(KIcon("applications-education-language"),
                i18n("Pitch Name Language"), self)
        a.setToolTip(i18n("Change the LilyPond language used for pitch names "
                          "in this document or in the selection."))
        self.actionCollection().addAction('pitch_change_language', a)
        QObject.connect(a.menu(), SIGNAL("aboutToShow()"), lambda menu=a.menu():
            self.currentDocument().manipulator().populateLanguageMenu(menu))
        
        @self.onAction(i18n("Convert Relative to Absolute"), tooltip=i18n(
            "Converts the notes in the document or selection from relative to absolute pitch."))
        def pitch_relative_to_absolute():
            self.currentDocument().manipulator().convertRelativeToAbsolute()
            
        @self.onAction(i18n("Convert Absolute to Relative"), tooltip=i18n(
            "Converts the notes in the document or selection from absolute to relative pitch."))
        def pitch_absolute_to_relative():
            self.currentDocument().manipulator().convertAbsoluteToRelative()

        @self.onAction(i18n("Transpose..."), tooltip=i18n(
            "Transposes all notes in the document or selection."))
        def pitch_transpose():
            KMessageBox.sorry(self, "Not yet implemented.")
            #self.transposeDialog().show()
        
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
        
        # Bar lines
        for name, text, title, key in (
            ("bar_double", "||", i18n("Double bar line"), "Alt+;"),
            ("bar_end", "|.", i18n("Ending bar line"), "Alt+."),
            ("bar_dotted", ":", i18n("Dotted bar line"), None),
            ("bar_dashed", "dashed", i18n("Dashed bar line"), None),
            ("bar_invisible", "", i18n("Invisible bar line"), None),
            ("bar_repeat_start", "|:", i18n("Repeat start"), None),
            ("bar_repeat_double", ":|:", i18n("Repeat both"), None),
            ("bar_repeat_end", ":|", i18n("Repeat end"), None),
            ("bar_tick", "'", i18n("Tick bar line"), "Alt+'"),
            ("bar_single", "|", i18n("Single bar line"), None),
            ("bar_sws", "|.|", i18n("Small-Wide-Small bar line"), None),
            ("bar_ws", ".|", i18n("Wide-Small bar line"), None),
            ("bar_ww", ".|.", i18n("Double wide bar line"), None),
            ("bar_cswc", ":|.:", i18n("Repeat both (old)"), None),
            ("bar_cswsc", ":|.|:", i18n("Repeat both (classic)"), None),
            ):
            a = self.act(name, title, key=key, func=lambda text=text:
                    self.currentDocument().manipulator().insertBarLine(text))
            self.addSymbol(a, name)
            
        # Setup lyrics hyphen and de-hyphen action
        @self.onSelAction(i18n("Hyphenate Lyrics Text"), keepSelection=False, key="Ctrl+L")
        def lyrics_hyphen(text):
            import frescobaldi_app.hyphen
            return frescobaldi_app.hyphen.hyphenate(text, self)
            
        @self.onSelAction(i18n("Remove hyphenation"), keepSelection=False)
        def lyrics_dehyphen(text):
            return text.replace(' -- ', '')
            
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
    
        @self.onAction(i18n("Email..."), "mail-send")
        def actions_email():
            self.actionManager().email(self.currentDocument().updatedFiles())
            
        # Settings
        @self.onAction(KStandardAction.Preferences)
        def options_configure():
            import frescobaldi_app.settings
            frescobaldi_app.settings.SettingsDialog(self).show()
        
        @self.onSelAction(i18n("Repeat selected music"), key="Ctrl+Shift+R",
            keepSelection=False)
        def edit_repeat(text):
            return self.currentDocument().manipulator().wrapBrace(text, 
                "\\repeat volta 2")
        
        @self.onAction(i18n("Insert pair of braces"), "code-context", key="Ctrl+{")
        def edit_insert_braces():
            d = self.currentDocument()
            if d.selectionText():
                d.replaceSelectionWith(d.manipulator().wrapBrace(
                    d.selectionText()), keepSelection=False)
            else:
                self.currentDocument().manipulator().insertTemplate("{\n(|)\n}")
        
        # Other wizards/tools:
        @self.onAction(i18n("Create blank staff paper"), "text-plain")
        def wizard_blank_staff_paper():
            self.blankStaffPaperWizard().show()

            
    def setupTools(self):
        KonsoleTool(self)
        LogTool(self)
        QuickInsertTool(self)
        RumorTool(self)
        if not config().readEntry("disable pdf preview", QVariant(False)).toBool():
            PDFTool(self)
        LilyDocTool(self)
    
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
            
    def updateJobActions(self):
        doc = self.currentDocument()
        running = bool(doc and not doc.isEmpty() and self.jobManager().job(doc))
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
        QObject.connect(self, SIGNAL("applyClicked()"), self.doApply)
        QObject.connect(self, SIGNAL("okClicked()"), self.doApply)

    def doApply(self):
        import ly.duration
        self.lineedit.completionObject().addItem(self.lineedit.text())
        self.parent().currentDocument().replaceSelectionWith(ly.duration.applyRhythm(
            self.text, unicode(self.lineedit.text())))

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
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "konsole", i18n("Terminal"), "terminal",
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
            self.openUrl(doc.url())

    def addMenuActions(self, m):
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
    _partappname = "Okular"
    def __init__(self, mainwin):
        self._config = {}
        kateshell.mainwindow.KPartTool.__init__(self, mainwin,
            "pdf", i18n("PDF Preview"), "application-pdf",
            key="Meta+Alt+P", dock=kateshell.mainwindow.Right)
        mainwin.currentDocumentChanged.connect(self.sync)
        self._currentUrl = None
        # We open urls with a timer otherwise Okular is called 
        # too quickly when the user switches documents too fast.
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        QObject.connect(self._timer, SIGNAL("timeout()"), self.timeoutFunc)
    
    def timeoutFunc(self):
        if self._currentUrl:
            super(PDFTool, self).openUrl(self._currentUrl)

    def sync(self, doc):
        if self._config["sync"]:
            pdfs = doc.updatedFiles()("pdf")
            if pdfs:
                self.openUrl(KUrl(pdfs[0]))

    def addMenuActions(self, m):
        def act(name, title):
            a = m.addAction(title)
            a.setCheckable(True)
            a.setChecked(self._config[name])
            QObject.connect(a, SIGNAL("triggered()"),
                lambda: self.toggleAction(name))
        act("leftpanel", i18n("Show PDF Navigation Panel"))
        act("minipager", i18n("Show PDF minipager"))
        a = m.addAction(i18n("Configure Okular..."))
        QObject.connect(a, SIGNAL("triggered()"), self.openOkularSettings)
        m.addSeparator()
        act("sync", i18n("S&ynchronize Preview with Current Document"))

    def openOkularSettings(self):
        self.materialize()
        if self.part:
            a = self.part.actionCollection().action("options_configure")
            if a:
                a.trigger()
                
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
    helpAnchor = "quickinsert"
    defaultWidth = 160
    def __init__(self, mainwin):
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "quickinsert", i18n("Quick Insert"), "document-properties",
            key="Meta+Alt+I", dock=kateshell.mainwindow.Left)
            
    def factory(self):
        import frescobaldi_app.lqi
        return frescobaldi_app.lqi.ToolBox(self)


class LogTool(kateshell.mainwindow.Tool):
    def __init__(self, mainwin):
        self._config = {}
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "log", i18n("LilyPond Log"), "run-lilypond",
            key="Meta+Alt+L", dock=kateshell.mainwindow.Bottom,
            widget=QStackedWidget())
        self.logs = {}
        self.widget.addWidget(QLabel("<center>(%s)</center>" % i18n("no log")))
        mainwin.currentDocumentChanged.connect(self.showLog)
        mainwin.app.documentClosed.connect(self.removeLog)
        QObject.connect(self.widget, SIGNAL("destroyed()"),
            lambda: self.logs.clear())
            
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
    
    def addMenuActions(self, m):
        def act(name, title):
            a = m.addAction(title)
            a.setCheckable(True)
            a.setChecked(self._config[name])
            QObject.connect(a, SIGNAL("triggered()"),
                lambda: self.toggleAction(name))
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
            self._config[name] = conf.readEntry(name, QVariant(default)).toBool()
            
    def writeConfig(self, conf):
        for name in ("errors only",):
            conf.writeEntry(name, QVariant(self._config[name]))
        

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
    import fnmatch
    if lyfile and os.path.exists(lyfile):
        if reftime is None:
            reftime = os.path.getmtime(lyfile)
        directory, name = os.path.split(lyfile)
        escname = re.escape(os.path.splitext(name)[0]) # remove ext, escape
        def generatorfunc(ext = "*"):
            ext = fnmatch.translate(ext.lstrip('.'))
            pat = re.compile(r'%s(-[^-]+)*\.%s' % (escname, ext))
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
    return not text or text.isspace()

def filenamekey(filename):
    """
    Returns a key for natural sorting file names
    """
    name, ext = os.path.splitext(filename)
    l = [m.group(2) or int(m.group(1))
            for m in re.finditer(r'(\d+)|(\D+)', name)]
    return l, ext

