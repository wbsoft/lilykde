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
Config dialog
"""

from PyQt4.QtCore import QObject, QSize, QString, QVariant, SIGNAL
from PyQt4.QtGui import (
    QCheckBox, QGridLayout, QGroupBox, QLabel, QLineEdit, QRadioButton,
    QTextEdit, QTreeView, QWidget)
from PyKDE4.kdecore import KGlobal, i18n
from PyKDE4.kdeui import KIcon, KPageDialog, KVBox
from PyKDE4.kio import KFile, KUrlRequester

import ly.version

from frescobaldi_app.widgets import ExecLineEdit, ExecArgsLineEdit

# these modules provide their own default settings or update functions
import frescobaldi_app.hyphen, frescobaldi_app.mainapp, frescobaldi_app.rumor

class SettingsDialog(KPageDialog):
    def __init__(self, mainwin):
        KPageDialog.__init__(self, mainwin)
        self.mainwin = mainwin
        self.setFaceType(KPageDialog.Tree)
        self.setButtons(KPageDialog.ButtonCode(
            KPageDialog.Reset | KPageDialog.Default | KPageDialog.Apply |
            KPageDialog.Ok | KPageDialog.Cancel | KPageDialog.Help))
        self.setCaption(i18n("Configure"))
        self.setHelp("settings-dialog")
        self.setDefaultButton(KPageDialog.Ok)
        QObject.connect(self, SIGNAL("applyClicked()"), self.saveSettings)
        QObject.connect(self, SIGNAL("defaultClicked()"), self.defaultClicked)
        QObject.connect(self, SIGNAL("resetClicked()"), self.loadSettings)
        QObject.connect(self,
            SIGNAL("currentPageChanged(KPageWidgetItem*, KPageWidgetItem*)"),
            self.slotCurrentPageChanged)
            
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
        
    def defaultClicked(self):
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
            QObject.connect(cPage, SIGNAL("changed()"), dialog.changed)
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
            b = QCheckBox(title, self)
            QObject.connect(b, SIGNAL("clicked()"), dialog.changed)
            self.checks.append((b, name, default))
            
        self.layout().addSpacing(20)
        
        self.versionOptions = {}
        self.customVersion = QLineEdit()
            
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
            self.versionOptions[name] = QRadioButton(title)
            QObject.connect(self.versionOptions[name], SIGNAL("toggled(bool)"), changed)
        
        self.customVersion.setToolTip(i18n(
            "Enter a valid LilyPond version number, e.g. 2.12.0"))
        QObject.connect(self.customVersion, SIGNAL("textChanged(QString)"),
            lambda dummy: dialog.changed())
        QObject.connect(self.versionOptions["custom"], SIGNAL("clicked()"),
            lambda: self.customVersion.setFocus())
        
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
            widget.setChecked(conf.readEntry(name, QVariant(default)).toBool())
        # lily version:
        self.customVersion.setText(conf.readEntry("custom version", QVariant("")).toString())
        name = unicode(conf.readEntry("default version", QVariant("")).toString())
        if name not in self.versionOptions:
            name = "lilypond"
        self.versionOptions[name].setChecked(True)

    def saveSettings(self):
        conf = config("preferences")
        for widget, name, default in self.checks:
            conf.writeEntry(name, QVariant(widget.isChecked()))
        # disable or enable the builtin PDF preview
        disable = conf.readEntry("disable pdf preview", QVariant(False)).toBool()
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
        item = dialog.addPage(self, i18n("Paths"))
        item.setHeader(i18n("Paths to programs or data used by Frescobaldi"))
        item.setIcon(KIcon("utilities-terminal"))
        self.help = 'settings-paths'
        
        layout = QGridLayout(self)
        
        # commands
        self.commands = []
        for name, default, title, lineedit, tooltip in (
            ('lilypond', 'lilypond', "LilyPond:", ExecLineEdit,
                i18n("Name or full path of the LilyPond program.")),
            ('convert-ly', 'convert-ly', "Convert-ly:", ExecLineEdit,
                i18n("Name or full path of the convert-ly program.")),
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
            QObject.connect(widget, SIGNAL("textEdited(const QString&)"),
                lambda: dialog.changed())
            label.setBuddy(widget)
            label.setToolTip(tooltip)
            widget.setToolTip(tooltip)
            layout.addWidget(label, len(self.commands), 0)
            layout.addWidget(widget, len(self.commands), 1)
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
        QObject.connect(self.folder, SIGNAL("textChanged(const QString&)"),
            lambda dummy: dialog.changed())
        
        # hyphen paths
        l = QLabel(i18n(
            "Paths to search for hyphenation dictionaries of OpenOffice.org, "
            "Scribus, KOffice, etc, one per line. "
            "If you leave out the starting slash, the prefixes from the "
            "KDEDIRS environment variable are prepended."))
        l.setWordWrap(True)
        self.hyphenPaths = QTextEdit()
        l.setBuddy(self.hyphenPaths)
        layout.addWidget(l, layout.rowCount(), 0, 1, 2)
        layout.addWidget(self.hyphenPaths, layout.rowCount(), 0, 1, 2)
        QObject.connect(self.hyphenPaths, SIGNAL("textChanged()"),
            dialog.changed)

    def setHyphenPaths(self, paths):
        self.hyphenPaths.setPlainText('\n'.join(unicode(p) for p in paths))
        
    def defaults(self):
        for widget, name, default in self.commands:
            widget.setText(default)
        self.setHyphenPaths(frescobaldi_app.hyphen.defaultPaths)
        self.folder.setPath('')
        
    def loadSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            widget.setText(conf.readEntry(name, QVariant(default)).toString())
        paths = config("hyphenation").readEntry("paths",
            QVariant(frescobaldi_app.hyphen.defaultPaths)).toStringList()
        self.setHyphenPaths(paths)
        self.folder.setPath(
            config("preferences").readPathEntry("default directory", ""))
        
    def saveSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            if widget.text() or not default:
                conf.writeEntry(name, widget.text())
        paths = [p for p in unicode(self.hyphenPaths.toPlainText()).splitlines()
            if p]
        config("hyphenation").writeEntry("paths", paths)
        # reload the table of hyphenation dictionaries
        frescobaldi_app.hyphen.findDicts()
        config("preferences").writePathEntry("default directory",
            self.folder.url().path())


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
            QObject.connect(widget, SIGNAL("textEdited(const QString&)"),
                lambda: dialog.changed())
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
            widget.setText(conf.readEntry(name, QVariant(default)).toString())
        
    def saveSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            if widget.text():
                conf.writeEntry(name, widget.text())
    


def config(group):
    return KGlobal.config().group(group)

def command(cmd):
    return unicode(config("commands").readEntry(cmd, QVariant(cmd)).toString())
