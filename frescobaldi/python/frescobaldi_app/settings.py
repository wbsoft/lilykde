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

"""
Config dialog
"""

from PyQt4.QtCore import QSize, Qt
from PyQt4.QtGui import (
    QCheckBox, QGridLayout, QGroupBox, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QRadioButton, QTextEdit, QTreeView, QVBoxLayout, QWidget)
from PyKDE4.kdecore import KGlobal, KUrl, i18n
from PyKDE4.kdeui import (
    KDialog, KHBox, KIcon, KPageDialog, KPushButton, KStandardGuiItem, KVBox)
from PyKDE4.kio import KFile, KUrlRequester

from signals import Signal

import ly.version
from kateshell.app import cacheresult
from kateshell.widgets import (
    ExecLineEdit, ExecArgsLineEdit, FilePathEdit, ListEdit)

# these modules provide their own default settings or update functions
import frescobaldi_app.hyphen, frescobaldi_app.mainapp, frescobaldi_app.rumor


class SettingsDialog(KPageDialog):
    def __init__(self, mainwin):
        KPageDialog.__init__(self, mainwin)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.mainwin = mainwin
        self.setFaceType(KPageDialog.Tree)
        self.setButtons(KPageDialog.ButtonCode(
            KPageDialog.Reset | KPageDialog.Default | KPageDialog.Apply |
            KPageDialog.Ok | KPageDialog.Cancel | KPageDialog.Help))
        self.setCaption(i18n("Configure"))
        self.setHelp("settings-dialog")
        self.setDefaultButton(KPageDialog.Ok)
        self.applyClicked.connect(self.saveSettings)
        self.defaultClicked.connect(self.slotDefaultClicked)
        self.resetClicked.connect(self.loadSettings)
        self.currentPageChanged.connect(self.slotCurrentPageChanged)
            
        self.pages = [
            GeneralPreferences(self),
            Commands(self),
            RumorSettings(self),
            EditorComponent(self),
        ]
        self.loadSettings()
        # make icons in tree somewhat larger
        tree = self.findChild(QTreeView)
        if tree:
            tree.setIconSize(QSize(22, 22))
        # restore our dialog size
        self.restoreDialogSize(config("settings dialog"))
        self.finished.connect(lambda: self.saveDialogSize(config("settings dialog")))
    
    def changed(self, changed=True):
        self.enableButton(KPageDialog.Apply, changed)
        
    def done(self, result):
        if result:
            self.saveSettings()
        KPageDialog.done(self, result)
        
    def slotDefaultClicked(self):
        for page in self.pages:
            page.defaults()
        self.changed(True)
            
    def loadSettings(self):
        for page in self.pages:
            page.loadSettings()
        self.changed(False)
        
    def saveSettings(self):
        for page in self.pages:
            page.saveSettings()
            page.applySettings()
        self.changed(False)
            
    def slotCurrentPageChanged(self, current, before):
        self.setHelp(getattr(current.widget(), "help", "settings-dialog"))
        

class SettingsBase(object):
    """ Base class for a unit that contains settings. """
    def defaults(self):
        """ Implement in subclass: reset settings to default. """
        pass
    
    def loadSettings(self):
        """ Implement in subclass: load settings from configfile. """
        pass
    
    def saveSettings(self):
        """ Implement in subclass: write settings to configfile. """
        pass
    
    def applySettings(self):
        """ Implement in subclass: do something after the new settings have been
        saved. """
        pass
    
    
class SettingsPage(QWidget, SettingsBase):
    """ Base class for a page with settings, possibly in SettingsGroups. """
    
    changed = Signal()
    
    def __init__(self, dialog):
        QWidget.__init__(self, dialog)
        self.dialog = dialog
        self.setLayout(QVBoxLayout())
        self.groups = []
        self.changed.connect(lambda: dialog.changed())
        
    def defaults(self):
        for group in self.groups:
            group.defaults()
    
    def loadSettings(self):
        for group in self.groups:
            group.loadSettings()
            
    def saveSettings(self):
        for group in self.groups:
            group.saveSettings()
    
    def applySettings(self):
        for group in self.groups:
            group.applySettings()


class SettingsGroup(QGroupBox, SettingsBase):
    """ Base class for a group box with settings """
    def __init__(self, title, page):
        """ page is a SettingsPage """
        QGroupBox.__init__(self, title, page)
        page.layout().addWidget(self)
        page.layout().addStretch(1)
        page.groups.append(self)
        self.changed = page.changed # quick connect :-)
        self.page = page
        

class CheckGroup(SettingsGroup):
    """ Base class for a group box with check boxes. """
    
    configGroup = None  # must define a name in subclass
    
    def __init__(self, title, page):
        super(CheckGroup, self).__init__(title, page)
        self.checks = []
        
    def addCheckBox(self, title, name, default):
        b = QCheckBox(title, self, clicked=self.changed)
        self.checks.append((b, name, default))
        return b
            
    def defaults(self):
        for widget, name, default in self.checks:
            widget.setChecked(default)
            
    def loadSettings(self):
        conf = config(self.configGroup)
        for widget, name, default in self.checks:
            widget.setChecked(conf.readEntry(name, default))

    def saveSettings(self):
        conf = config(self.configGroup)
        for widget, name, default in self.checks:
            conf.writeEntry(name, widget.isChecked())
    
        
class GeneralPreferences(SettingsPage):
    """
    General preferences.
    """
    def __init__(self, dialog):
        super(GeneralPreferences, self).__init__(dialog)
        item = dialog.addPage(self, i18n("General Preferences"))
        item.setHeader(i18n("General Frescobaldi Preferences"))
        item.setIcon(KIcon("configure"))
        
        LilyPondDocumentVersion(self)
        SavingDocument(self)
        RunningLilyPond(self)
        Warnings(self)
        
        
class Commands(SettingsPage):
    """
    Settings regarding commands of lilypond and associated programs.
    """
    def __init__(self, dialog):
        super(Commands, self).__init__(dialog)
        item = dialog.addPage(self, i18n("Paths"))
        item.setHeader(i18n("Paths to programs or data used by Frescobaldi"))
        item.setIcon(KIcon("utilities-terminal"))
        self.help = 'settings-paths'
        
        LilyPondVersions(self)
        HelperApps(self)
        LilyDocBrowser(self)
        HyphenationSettings(self)


class RumorSettings(SettingsPage):
    """
    Settings regarding rumor and associated programs.
    """
    def __init__(self, dialog):
        super(RumorSettings, self).__init__(dialog)
        item = dialog.addPage(self, i18n("Rumor MIDI input"))
        item.setHeader(i18n("Rumor MIDI input plugin settings"))
        item.setIcon(KIcon("media-record"))
        self.help = 'rumor'
        
        RumorCommands(self)
        

class EditorComponent(SettingsPage):
    """
    Settings from the KatePart editing component.
    """
    def __init__(self, dialog):
        super(EditorComponent, self).__init__(dialog)
        editorItem = dialog.addPage(self, i18n("Editor Component"))
        editorItem.setHeader(i18n("Editor Component Options"))
        editorItem.setIcon(KIcon("accessories-text-editor"))
        self.help = 'settings-editor-component'
        
        TabBarSettings(self)
        
        self.editorPages = []
        editor = dialog.mainwin.app.editor
        # Get the KTextEditor config pages.
        for i in range(editor.configPages()):
            cPage = editor.configPage(i, self)
            cPage.changed.connect(self.changed)
            self.editorPages.append(cPage)
            item = dialog.addSubPage(editorItem, cPage, editor.configPageName(i))
            item.setHeader(editor.configPageFullName(i))
            item.setIcon(editor.configPageIcon(i))
            cPage.help = 'settings-editor-component'

    def saveSettings(self):
        super(EditorComponent, self).saveSettings()
        for page in self.editorPages:
            page.apply()
            

class RunningLilyPond(CheckGroup):
    
    configGroup = "preferences"
    
    def __init__(self, page):
        super(RunningLilyPond, self).__init__(i18n("Running LilyPond"), page)
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        
        layout.addWidget(
            self.addCheckBox(i18n("Let LilyPond delete intermediate output files"),
                "delete intermediate files", True))
        layout.addWidget(
            self.addCheckBox(i18n("Run LilyPond with verbose output"),
                "verbose lilypond output", False))

        layout.addWidget(
            self.addCheckBox(i18n("Disable the built-in PDF preview"),
                "disable pdf preview", False))
        
        h = KHBox()
        QLabel(i18n("LilyPond include path:"), h)
        self.includePath = FilePathEdit(h)
        self.includePath.changed.connect(page.changed)
        layout.addWidget(h)

    def defaults(self):
        super(RunningLilyPond, self).defaults()
        self.includePath.clear()
        
    def loadSettings(self):
        super(RunningLilyPond, self).loadSettings()
        self.includePath.setValue(
            config("preferences").readPathEntry("lilypond include path", []))

    def saveSettings(self):
        super(RunningLilyPond, self).saveSettings()
        conf = config("preferences")
        conf.writePathEntry("lilypond include path",
            self.includePath.value())
    
    def applySettings(self):
        # disable or enable the builtin PDF preview
        mainwin = self.page.dialog.mainwin
        disable = config("preferences").readEntry("disable pdf preview", False)
        running = "pdf" in mainwin.tools
        if disable and running:
            mainwin.tools["pdf"].delete()
        elif not disable and not running:
            tool = frescobaldi_app.mainapp.PDFTool(mainwin)
            tool.sync(mainwin.currentDocument())


class SavingDocument(CheckGroup):
    
    configGroup = "preferences"

    def __init__(self, page):
        super(SavingDocument, self).__init__(i18n("When saving documents"), page)
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        
        layout.addWidget(
            self.addCheckBox(i18n("Remember cursor position, bookmarks, etc."),
                "save metainfo", False))

        # default directory
        h = KHBox()
        l = QLabel(i18n("Default directory:"), h)
        self.folder = KUrlRequester(h)
        l.setBuddy(self.folder)
        tooltip = i18n("The default folder for your LilyPond documents (optional).")
        l.setToolTip(tooltip)
        self.folder.setToolTip(tooltip)
        layout.addWidget(h)
        self.folder.setMode(KFile.Mode(
            KFile.Directory | KFile.ExistingOnly | KFile.LocalOnly))
        self.folder.button().setIcon(KIcon("document-open-folder"))
        self.folder.textChanged.connect(page.changed)

    def defaults(self):
        super(SavingDocument, self).defaults()
        
    def loadSettings(self):
        super(SavingDocument, self).loadSettings()
        self.folder.setPath(
            config("preferences").readPathEntry("default directory", ""))
        
    def saveSettings(self):
        super(SavingDocument, self).saveSettings()
        config("preferences").writePathEntry("default directory",
            self.folder.url().path())
        

class LilyPondDocumentVersion(SettingsGroup):
    
    def __init__(self, page):
        super(LilyPondDocumentVersion, self).__init__(i18n(
            "LilyPond version number to use for new documents"), page)
            
        grid = QGridLayout(self)
        grid.setSpacing(0)
        
        self.versionOptions = {}
        self.customVersion = QLineEdit(textChanged=page.changed)
            
        def changed(dummy):
            page.changed()
            self.customVersion.setEnabled(self.versionOptions["custom"].isChecked())
            
        for title, name in (
            (i18n("Use version number of installed LilyPond"), "lilypond"),
            (i18n("Use version number of last convert-ly rule"), "convert-ly"),
            (i18n("Use custom version number:"), "custom"),
        ):
            self.versionOptions[name] = QRadioButton(title, toggled=changed)
        
        self.customVersion.setToolTip(i18n(
            "Enter a valid LilyPond version number, e.g. 2.12.0"))
        self.versionOptions["custom"].clicked.connect(lambda: self.customVersion.setFocus())
        
        grid.addWidget(self.versionOptions["lilypond"], 0, 0, 1, 2)
        grid.addWidget(self.versionOptions["convert-ly"], 1, 0, 1, 2)
        grid.addWidget(self.versionOptions["custom"], 2, 0, 1, 1)
        grid.addWidget(self.customVersion, 2, 1, 1, 1)

    def defaults(self):
        self.customVersion.clear()
        self.versionOptions["lilypond"].setChecked(True)
            
    def loadSettings(self):
        conf = config("preferences")
        self.customVersion.setText(conf.readEntry("custom version", ""))
        name = conf.readEntry("default version", "")
        if name not in self.versionOptions:
            name = "lilypond"
        self.versionOptions[name].setChecked(True)

    def saveSettings(self):
        conf = config("preferences")
        conf.writeEntry("custom version", self.customVersion.text())
        for name, widget in self.versionOptions.items():
            if widget.isChecked():
                conf.writeEntry("default version", name)
                break


class Warnings(CheckGroup):
    
    configGroup = "Notification Messages"
    
    def __init__(self, page):
        super(Warnings, self).__init__(i18n("Warnings and Notifications"), page)
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        
        layout.addWidget(
            self.addCheckBox(i18n("Warn when a document contains a conflicting point and click setting"),
                "point_and_click", True))
        layout.addWidget(
            self.addCheckBox(i18n("Warn when a document needs to be saved before LilyPond is run"),
                "save_on_run", True))


class HelperApps(SettingsGroup):
    def __init__(self, page):
        super(HelperApps, self).__init__(i18n("Helper applications"), page)
        
        layout = QGridLayout(self)
        self.commands = []
        for name, default, title, lineedit, tooltip in (
            ('pdf viewer', '', i18n("PDF Viewer:"), ExecArgsLineEdit,
                i18n("PDF Viewer") + " " +
                i18n("(leave empty for operating system default)")),
            ('midi player', '', i18n("MIDI Player:"), ExecArgsLineEdit,
                i18n("MIDI Player") + " " +
                i18n("(leave empty for operating system default)")),
        ):
            label = QLabel(title)
            widget = lineedit()
            widget.textEdited.connect(page.changed)
            label.setBuddy(widget)
            label.setToolTip(tooltip)
            widget.setToolTip(tooltip)
            row = layout.rowCount()
            layout.addWidget(label, row, 0)
            layout.addWidget(widget, row, 1)
            self.commands.append((widget, name, default))

    def defaults(self):
        for widget, name, default in self.commands:
            widget.setText(default)
        
    def loadSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            widget.setText(conf.readEntry(name, default))

    def saveSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            if widget.text() or not default:
                conf.writeEntry(name, widget.text())


class LilyDocBrowser(SettingsGroup):
    def __init__(self, page):
        super(LilyDocBrowser, self).__init__(i18n("LilyPond Documentation"), page)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        
        h = KHBox()
        l = QLabel(i18n("Url:"), h)
        self.lilydoc = KUrlRequester(h)
        self.lilydoc.textChanged.connect(page.changed)
        l.setBuddy(self.lilydoc)
        tooltip = i18n(
            "Url or path to the LilyPond documentation.")
        l.setToolTip(tooltip)
        self.lilydoc.setToolTip(tooltip)
        self.lilydoc.fileDialog().setCaption(i18n("LilyPond Documentation"))
        layout.addWidget(h)
        self.lilydoc.setMode(KFile.Mode(
            KFile.File | KFile.Directory | KFile.ExistingOnly))

    def defaults(self):
        self.lilydoc.setUrl(KUrl())
        
    def loadSettings(self):
        self.lilydoc.setUrl(KUrl(
            config("preferences").readEntry("lilypond documentation", "")))

    def saveSettings(self):
        config("preferences").writeEntry(
            "lilypond documentation", self.lilydoc.url().url())
    
    def applySettings(self):
        lilydoc = self.page.dialog.mainwin.tools.get('lilydoc')
        if lilydoc:
            lilydoc.newDocFinder()


class HyphenationSettings(SettingsGroup):
    def __init__(self, page):
        super(HyphenationSettings, self).__init__(i18n("Lyrics Hyphenation"), page)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
    
        # hyphen paths
        l = QLabel(i18n(
            "Paths to search for hyphenation dictionaries of OpenOffice.org, "
            "Scribus, KOffice, etc, one per line. "
            "If you leave out the starting slash, the prefixes from the "
            "KDEDIRS environment variable are prepended."))
        l.setWordWrap(True)
        self.hyphenPaths = QTextEdit(textChanged=page.changed)
        l.setBuddy(self.hyphenPaths)
        layout.addWidget(l)
        layout.addWidget(self.hyphenPaths)

    def setHyphenPaths(self, paths):
        self.hyphenPaths.setPlainText('\n'.join(paths))
        
    def defaults(self):
        self.setHyphenPaths(frescobaldi_app.hyphen.defaultPaths)
        
    def loadSettings(self):
        paths = config("hyphenation").readEntry("paths", frescobaldi_app.hyphen.defaultPaths)
        self.setHyphenPaths(paths)

    def saveSettings(self):
        paths = [p for p in self.hyphenPaths.toPlainText().splitlines() if p]
        config("hyphenation").writeEntry("paths", paths)
        
    def applySettings(self):
        # reload the table of hyphenation dictionaries
        frescobaldi_app.hyphen.findDicts()


class RumorCommands(SettingsGroup):
    def __init__(self, page):
        super(RumorCommands, self).__init__(i18n(
            "Commands used by the Rumor MIDI input module"), page)
        
        layout = QGridLayout(self)
        
        self.commands = []
        for name, default, title, lineedit, tooltip in (
            ('rumor', 'rumor', "Rumor:", ExecLineEdit,
                i18n("Name or full path of the Rumor program.")),
            ('aconnect', 'aconnect', "Aconnect:", ExecLineEdit,
                i18n("Name or full path of the aconnect program (part of ALSA, "
                  "for MIDI input and playback using Rumor).")),
            ('timidity', frescobaldi_app.rumor.default_timidity_command,
                "Timidity:", ExecArgsLineEdit,
                i18n("Full command to start Timidity (or any other program) "
                  "as an ALSA MIDI client.")),
        ):
            label = QLabel(title)
            widget = lineedit()
            widget.textEdited.connect(page.changed)
            label.setBuddy(widget)
            label.setToolTip(tooltip)
            widget.setToolTip(tooltip)
            row = layout.rowCount()
            layout.addWidget(label, row, 0)
            layout.addWidget(widget, row, 1)
            self.commands.append((widget, name, default))
        
    def defaults(self):
        for widget, name, default in self.commands:
            widget.setText(default)
        
    def loadSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            widget.setText(conf.readEntry(name, default))
        
    def saveSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            if widget.text():
                conf.writeEntry(name, widget.text())


class LilyPondVersions(SettingsGroup):
    """Manage multiple versions of LilyPond."""
    def __init__(self, page):
        super(LilyPondVersions, self).__init__(i18n("LilyPond versions to use:"), page)
        layout = QVBoxLayout(self)
        
        self.instances = LilyPondInfoList(self)
        self.instances.changed.connect(page.changed)
        layout.addWidget(self.instances)
        self.auto = QCheckBox(i18n(
            "Enable automatic version selection "
            "(choose LilyPond version from document)"),
            clicked=page.changed)
        layout.addWidget(self.auto)
        
    def defaults(self):
        """ Reset ourselves to default state. """
        self.instances.clear()
        info = self.instances.createItem()
        self.instances.addItem(info)
        self.instances.setCurrentItem(info)
        self.auto.setChecked(False)
        info.changed()
        
    def loadSettings(self):
        self.instances.clear()
        conf = config("lilypond")
        self.auto.setChecked(conf.readEntry("automatic version", False))
        paths = conf.readEntry("paths", ["lilypond"])
        default = conf.readEntry("default", "lilypond")
        # sort on version and move erratic entries to the end
        paths.sort(key=lambda path: ly.version.LilyPondInstance(path).version() or (999,))
        for path in paths:
            info = LilyPondInfoItem(path)
            info.default = path == default
            self.instances.addItem(info)
            info.loadSettings(conf.group(path))
            if info.default:
                self.instances.setCurrentItem(info)
    
    def saveSettings(self):
        paths = []
        default = ""
        conf = config("lilypond")
        conf.deleteGroup()
        for info in self.instances.items():
            paths.append(info.lilypond)
            if info.default:
                default = info.lilypond
            info.saveSettings(conf.group(info.lilypond))
        if not paths:
            paths = ["lilypond"]
        if not default:
            default = paths[0]
        conf.writeEntry("paths", paths)
        conf.writeEntry("default", default)
        conf.writeEntry("automatic version", self.auto.isChecked())


class TabBarSettings(CheckGroup):
    """
    Settings for the document tab bar provided by kateshell.
    """
    configGroup = "tab bar"
    
    def __init__(self, page):
        super(TabBarSettings, self).__init__(i18n("Document Tabs"), page)
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        
        layout.addWidget(
            self.addCheckBox(i18n("Close Button"), "close button", True))
        layout.addWidget(
            self.addCheckBox(i18n("Large Tabs"), "expanding", False))
        layout.addWidget(
            self.addCheckBox(i18n("Tabs can be moved"), "movable", True))
    
    def applySettings(self):
        self.page.dialog.mainwin.viewTabs.readSettings()


class LilyPondInfoList(ListEdit):
    """
    Manages a list of LilyPondInfo instances.
    """
    @cacheresult
    def lilyPondInfoDialog(self):
        return LilyPondInfoDialog(self)
        
    def createItem(self):
        return LilyPondInfoItem()
    
    def openEditor(self, item):
        dlg = self.lilyPondInfoDialog()
        dlg.loadInfo(item)
        if dlg.exec_():
            dlg.saveInfo(item)
            return True
        return False
        

class LilyPondInfo(object):
    """
    Encapsulates information about a LilyPond instance.
    
    Attributes:
    lilypond    the lilypond command (default "lilypond")
    commands    a dict with the values of the commands, relative to the directory
                of the lilypond command; the name is also the default value for
                the command.
    default     whether to set this lilypond command as the default
    auto        whether to include this command in automatic version selection
    """
    def __init__(self, lilypond="lilypond"):
        self.lilypond = lilypond
        self.commands = dict((name, name) for name, descr in self.commandNames())
        self.default = False
        self.auto = True
        
    @staticmethod
    def commandNames():
        """
        Returns a tuple with two-tuples (name, description) of commands
        that can be configured as belonging to a LilyPond instance.
        The name is also the default value for the command.
        """
        return (
            ("convert-ly", i18n("Convert-ly:")),
            ("lilypond-book", i18n("Lilypond-book:")),
        )

    def changed(self):
        """ Implement to be notified of changes. """
        pass

    def loadSettings(self, group):
        for cmd, descr in self.commandNames():
            self.commands[cmd] = group.readEntry(cmd, cmd)
        self.auto = group.readEntry("auto", True)
        self.changed()
    
    def saveSettings(self, group):
        for cmd, descr in self.commandNames():
            group.writeEntry(cmd, self.commands[cmd])
        group.writeEntry("auto", self.auto)


class LilyPondInfoItem(QListWidgetItem, LilyPondInfo):
    def __init__(self, lilypond="lilypond"):
        QListWidgetItem.__init__(self)
        LilyPondInfo.__init__(self, lilypond)
    
    def changed(self):
        """ Call this when this item needs to redisplay itself. """
        lp = self.lilypond
        lilypond = ly.version.LilyPondInstance(lp)
        if lilypond.version():
            lp += " ({0})".format(lilypond.version())
            self.setIcon(KIcon("run-lilypond"))
            self.setToolTip(
                '<table border=0><tbody>'
                '<tr><td><b>{0}: </b></td><td>{1}</td></tr>'
                '<tr><td><b>{2}: </b></td><td>{3}</td></tr>'
                '</tbody></table>'.format(
                    i18n("Path"), lilypond.command() or "",
                    i18n("Version"), lilypond.version()))
        else:
            self.setIcon(KIcon("dialog-error"))
            self.setToolTip(i18n("Can't determine LilyPond version."))
        if self.default:
            lp += " [{0}]".format(i18n("default"))
            
            # reset the default state for others
            for c in range(self.listWidget().count()):
                item = self.listWidget().item(c)
                if item is not self and item.default:
                    item.default = False
                    item.changed()
        self.setText(lp)
        

class LilyPondInfoDialog(KDialog):
    """
    A dialog to edit attributes of a LilyPondInfo instance.
    """
    def __init__(self, parent):
        KDialog.__init__(self, parent)
        self.setButtons(KDialog.ButtonCode(
            KDialog.Ok | KDialog.Cancel | KDialog.Help))
        self.setCaption(i18n("LilyPond"))
        self.setHelp("settings-paths-lilypond")
        layout = QGridLayout(self.mainWidget())
        
        l = QLabel(i18n("LilyPond Command:"))
        self.lilypond = KUrlRequester()
        l.setBuddy(self.lilypond)
        self.lilypond.lineEdit().setToolTip(i18n(
            "Name or full path of the LilyPond program."))
        self.lilypond.fileDialog().setCaption(i18n("LilyPond Command"))
        layout.addWidget(l, 0, 0, 1, 2)
        layout.addWidget(self.lilypond, 1, 0, 1, 2)
        
        self.commands = {}
        row = 2
        for name, description in LilyPondInfo.commandNames():
            l = QLabel(description)
            e = self.commands[name] = QLineEdit()
            l.setBuddy(e)
            layout.addWidget(l, row, 0, Qt.AlignRight)
            layout.addWidget(e, row, 1)
            row += 1
        self.default = QCheckBox(i18n("Set as default"))
        layout.addWidget(self.default, row, 1)
        self.auto = QCheckBox(i18n("Include in automatic version selection"))
        layout.addWidget(self.auto, row+1, 1)
        
    def loadInfo(self, info):
        """ Display the settings in the LilyPondInfo object in our dialog. """
        self.lilypond.setText(info.lilypond)
        for name, value in info.commands.items():
            self.commands[name].setText(value)
        self.default.setChecked(info.default)
        self.auto.setChecked(info.auto)
        
    def saveInfo(self, info):
        """ Write the settings in our dialog to the LilyPondInfo object. """
        info.lilypond = self.lilypond.text()
        for name, widget in self.commands.items():
            info.commands[name] = widget.text()
        info.default = self.default.isChecked()
        info.auto = self.auto.isChecked()
        info.changed()


def config(group):
    return KGlobal.config().group(group)

