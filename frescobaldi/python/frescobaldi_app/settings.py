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
    QListWidgetItem, QRadioButton, QTextEdit, QTreeView, QWidget)
from PyKDE4.kdecore import KGlobal, KUrl, i18n
from PyKDE4.kdeui import (
    KIcon, KDialog, KPageDialog, KPushButton, KStandardGuiItem, KVBox)
from PyKDE4.kio import KFile, KUrlRequester

from signals import Signal

import ly.version
from kateshell.app import cacheresult
from frescobaldi_app.widgets import ExecLineEdit, ExecArgsLineEdit

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
        self.changed(False)
            
    def slotCurrentPageChanged(self, current, before):
        w = current.widget()
        if hasattr(w, "help"):
            self.setHelp(w.help)
        else:
            self.setHelp("settings-dialog")
        

class EditorComponent(object):
    def __init__(self, dialog):
        editorItem = dialog.addPage(QWidget(), i18n("Editor Component"))
        editorItem.setHeader(i18n("Editor Component Options"))
        editorItem.setIcon(KIcon("accessories-text-editor"))
        self.editorPages = []
        editor = dialog.mainwin.app.editor
        # Get the KTextEditor config pages.
        for i in range(editor.configPages()):
            cPage = editor.configPage(i, dialog)
            cPage.changed.connect(dialog.changed)
            self.editorPages.append(cPage)
            item = dialog.addSubPage(editorItem, cPage, editor.configPageName(i))
            item.setHeader(editor.configPageFullName(i))
            item.setIcon(editor.configPageIcon(i))
            cPage.help = 'settings-editor-component'

    def defaults(self):
        pass # not available
        
    def loadSettings(self):
        pass # not necessary
        
    def saveSettings(self):
        for page in self.editorPages:
            page.apply()
            

class GeneralPreferences(KVBox):
    def __init__(self, dialog):
        KVBox.__init__(self, dialog)
        self.mainwin = dialog.mainwin
        item = dialog.addPage(self, i18n("General Preferences"))
        item.setHeader(i18n("General Frescobaldi Preferences"))
        item.setIcon(KIcon("configure"))
        
        self.checks = []
        for title, name, default in (
            (i18n("Save document when LilyPond is run"),
                "save on run", False),
            (i18n("Let LilyPond delete intermediate output files"),
                "delete intermediate files", True),
            (i18n("Run LilyPond with verbose output"),
                "verbose lilypond output", False),
            (i18n("Remember cursor position, bookmarks, etc."),
                "save metainfo", False),
            (i18n("Disable the built-in PDF preview"),
                "disable pdf preview", False),
        ):
            b = QCheckBox(title, self, clicked=lambda: dialog.changed())
            self.checks.append((b, name, default))
            
        self.layout().addSpacing(20)
        
        self.versionOptions = {}
        self.customVersion = QLineEdit(textChanged=lambda: dialog.changed())
            
        def changed(dummy):
            dialog.changed()
            self.customVersion.setEnabled(self.versionOptions["custom"].isChecked())
            
        grid = QGridLayout(QGroupBox(i18n(
            "LilyPond version number to use for new documents"), self))
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
        
        self.layout().addStretch(1)

    def defaults(self):
        for widget, name, default in self.checks:
            widget.setChecked(default)
        # lily version:
        self.customVersion.clear()
        self.versionOptions["lilypond"].setChecked(True)
            
    def loadSettings(self):
        conf = config("preferences")
        for widget, name, default in self.checks:
            widget.setChecked(conf.readEntry(name, default))
        # lily version:
        self.customVersion.setText(conf.readEntry("custom version", ""))
        name = conf.readEntry("default version", "")
        if name not in self.versionOptions:
            name = "lilypond"
        self.versionOptions[name].setChecked(True)

    def saveSettings(self):
        conf = config("preferences")
        for widget, name, default in self.checks:
            conf.writeEntry(name, widget.isChecked())
        # disable or enable the builtin PDF preview
        disable = conf.readEntry("disable pdf preview", False)
        running = "pdf" in self.mainwin.tools
        if disable and running:
            self.mainwin.tools["pdf"].delete()
        elif not disable and not running:
            tool = frescobaldi_app.mainapp.PDFTool(self.mainwin)
            tool.sync(self.mainwin.currentDocument())
        # lily version:
        conf.writeEntry("custom version", self.customVersion.text())
        for name, widget in self.versionOptions.items():
            if widget.isChecked():
                conf.writeEntry("default version", name)
                break


class Commands(QWidget):
    """
    Settings regarding commands of lilypond and associated programs
    """
    def __init__(self, dialog):
        QWidget.__init__(self, dialog)
        self.mainwin = dialog.mainwin
        item = dialog.addPage(self, i18n("Paths"))
        item.setHeader(i18n("Paths to programs or data used by Frescobaldi"))
        item.setIcon(KIcon("utilities-terminal"))
        self.help = 'settings-paths'
        
        layout = QGridLayout(self)
        
        # lilypond versions/instances
        self.lilypond = LilyPondInfoList(self)
        self.lilypond.changed.connect(dialog.changed)
        layout.addWidget(self.lilypond, 0, 0, 1, 2)
        
        # commands
        self.commands = []
        for name, default, title, lineedit, tooltip in (
            ('pdf viewer', '', i18n("PDF Viewer:"), ExecArgsLineEdit,
                i18n("PDF Viewer") + " " +
                i18n("(leave empty for operating system default)")),
            ('midi player', '', i18n("MIDI Player:"), ExecArgsLineEdit,
                i18n("MIDI Player") + " " +
                i18n("(leave empty for operating system default)")),
            ('lpr', 'lpr', i18n("Printcommand:"), ExecArgsLineEdit,
                i18n("Command to print a PDF file, for example lpr or "
                  "kprinter. You may add some arguments, e.g. "
                  "lpr -P myprinter.")),
        ):
            label = QLabel(title)
            widget = lineedit()
            widget.textEdited.connect(lambda: dialog.changed())
            label.setBuddy(widget)
            label.setToolTip(tooltip)
            widget.setToolTip(tooltip)
            row = layout.rowCount()
            layout.addWidget(label, row, 0)
            layout.addWidget(widget, row, 1)
            self.commands.append((widget, name, default))
        
        # default directory
        l = QLabel(i18n("Default directory:"))
        self.folder = KUrlRequester()
        l.setBuddy(self.folder)
        row = layout.rowCount()
        tooltip = i18n(
            "The default folder for your LilyPond documents (optional).")
        l.setToolTip(tooltip)
        self.folder.setToolTip(tooltip)
        layout.addWidget(l, row, 0)
        layout.addWidget(self.folder, row, 1)
        self.folder.setMode(KFile.Mode(
            KFile.Directory | KFile.ExistingOnly | KFile.LocalOnly))
        self.folder.button().setIcon(KIcon("document-open-folder"))
        self.folder.textChanged.connect(lambda dummy: dialog.changed())
        
        # LilyPond documentation URL
        l = QLabel(i18n("LilyPond documentation:"))
        self.lilydoc = KUrlRequester(textChanged=lambda: dialog.changed())
        l.setBuddy(self.lilydoc)
        row = layout.rowCount()
        tooltip = i18n(
            "Url or path to the LilyPond documentation.")
        l.setToolTip(tooltip)
        self.lilydoc.setToolTip(tooltip)
        layout.addWidget(l, row, 0)
        layout.addWidget(self.lilydoc, row, 1)
        self.lilydoc.setMode(KFile.Mode(
            KFile.File | KFile.Directory | KFile.ExistingOnly))
        
        # hyphen paths
        l = QLabel(i18n(
            "Paths to search for hyphenation dictionaries of OpenOffice.org, "
            "Scribus, KOffice, etc, one per line. "
            "If you leave out the starting slash, the prefixes from the "
            "KDEDIRS environment variable are prepended."))
        l.setWordWrap(True)
        self.hyphenPaths = QTextEdit(textChanged=lambda: dialog.changed())
        l.setBuddy(self.hyphenPaths)
        layout.addWidget(l, layout.rowCount(), 0, 1, 2)
        layout.addWidget(self.hyphenPaths, layout.rowCount(), 0, 1, 2)

    def setHyphenPaths(self, paths):
        self.hyphenPaths.setPlainText('\n'.join(paths))
        
    def defaults(self):
        self.lilypond.defaults()
        for widget, name, default in self.commands:
            widget.setText(default)
        self.setHyphenPaths(frescobaldi_app.hyphen.defaultPaths)
        self.folder.setPath('')
        self.lilydoc.setUrl(KUrl())
        
    def loadSettings(self):
        self.lilypond.loadSettings()
        conf = config("commands")
        for widget, name, default in self.commands:
            widget.setText(conf.readEntry(name, default))
        paths = config("hyphenation").readEntry("paths", frescobaldi_app.hyphen.defaultPaths)
        self.setHyphenPaths(paths)
        self.folder.setPath(
            config("preferences").readPathEntry("default directory", ""))
        self.lilydoc.setUrl(KUrl(
            config("preferences").readEntry("lilypond documentation", "")))

    def saveSettings(self):
        self.lilypond.saveSettings()
        conf = config("commands")
        for widget, name, default in self.commands:
            if widget.text() or not default:
                conf.writeEntry(name, widget.text())
        paths = [p for p in self.hyphenPaths.toPlainText().splitlines() if p]
        config("hyphenation").writeEntry("paths", paths)
        # reload the table of hyphenation dictionaries
        frescobaldi_app.hyphen.findDicts()
        config("preferences").writePathEntry("default directory",
            self.folder.url().path())
        config("preferences").writeEntry("lilypond documentation",
            self.lilydoc.url().url())
        lilydoc = self.mainwin.tools.get('lilydoc')
        if lilydoc:
            lilydoc.newDocFinder()


class RumorSettings(KVBox):
    """
    Settings regarding commands of lilypond and associated programs
    """
    def __init__(self, dialog):
        QWidget.__init__(self, dialog)
        item = dialog.addPage(self, i18n("Rumor MIDI input"))
        item.setHeader(i18n("Rumor MIDI input plugin settings"))
        item.setIcon(KIcon("media-record"))
        self.help = 'rumor'
        
        layout = QGridLayout(QGroupBox(i18n(
            "Commands used by the Rumor MIDI input module"), self))
        row = 0
        
        # Rumor related commands
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
            widget.textEdited.connect(lambda: dialog.changed())
            label.setBuddy(widget)
            label.setToolTip(tooltip)
            widget.setToolTip(tooltip)
            layout.addWidget(label, row, 0)
            layout.addWidget(widget, row, 1)
            self.commands.append((widget, name, default))
            row += 1
        self.layout().addStretch(1)
        
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


class LilyPondInfoList(QGroupBox):
    """
    Manages a list of LilyPondInfo instances.
    """
    def __init__(self, parent=None):
        QGroupBox.__init__(self, i18n("LilyPond versions to use:"), parent)
        self.changed = Signal()
        
        layout = QGridLayout(self)
        self.instances = QListWidget()
        
        addButton = KPushButton(KStandardGuiItem.add())
        editButton = KPushButton(KStandardGuiItem.configure())
        removeButton = KPushButton(KStandardGuiItem.remove())
        
        self.auto = QCheckBox(i18n(
            "Enable automatic version selection "
            "(choose LilyPond version from document)"),
            clicked=lambda: self.changed())
        
        layout.addWidget(self.instances, 0, 0, 3, 1)
        layout.addWidget(addButton, 0, 1)
        layout.addWidget(editButton, 1, 1)
        layout.addWidget(removeButton, 2, 1)
        layout.addWidget(self.auto, 3, 0, 1, 2)
        
        addButton.clicked.connect(self.addClicked)
        editButton.clicked.connect(self.editClicked)
        removeButton.clicked.connect(self.removeClicked)
        self.instances.itemDoubleClicked.connect(self.itemDoubleClicked)
        
    @cacheresult
    def lilyPondInfoDialog(self):
        return LilyPondInfoDialog(self)
        
    def addClicked(self):
        """ Called when the user clicks Add. """
        dlg = self.lilyPondInfoDialog()
        dlg.loadInfo(LilyPondInfo())
        if dlg.exec_():
            info = LilyPondInfoItem()
            self.instances.addItem(info)
            self.instances.setCurrentItem(info)
            dlg.saveInfo(info)
            self.changed()

    def editClicked(self):
        """ Called when the user clicks Edit. """
        info = self.instances.currentItem()
        if info:
            dlg = self.lilyPondInfoDialog()
            dlg.loadInfo(info)
            if dlg.exec_():
                dlg.saveInfo(info)
                self.changed()
            
    def removeClicked(self, item):
        """ Called when the user clicks Remove. """
        self.instances.takeItem(self.instances.currentRow())
        self.changed()
    
    def itemDoubleClicked(self, item):
        """ Called when the user doubleclicks an item. """
        if item:
            self.instances.setCurrentItem(item)
            self.editClicked()
            
    def items(self):
        """ Iterator over the items in the list. """
        for c in range(self.instances.count()):
            yield self.instances.item(c)
            
    def defaults(self):
        """ Reset ourselves to default state. """
        self.instances.clear()
        info = LilyPondInfoItem()
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
        for info in self.items():
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
        layout = QGridLayout(self.mainWidget())
        
        l = QLabel(i18n("LilyPond Command:"))
        self.lilypond = KUrlRequester()
        l.setBuddy(self.lilypond)
        self.lilypond.lineEdit().setToolTip(i18n(
            "Name or full path of the LilyPond program."))
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

