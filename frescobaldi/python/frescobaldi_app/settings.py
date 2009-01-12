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

"""
Config dialog
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import KFile, KUrlRequester

from frescobaldi_app.widgets import ExecLineEdit, ExecArgsLineEdit

# these modules provide their own default settings
import frescobaldi_app.rumor, frescobaldi_app.hyphen

class SettingsDialog(KPageDialog):
    def __init__(self, mainwin):
        KPageDialog.__init__(self, mainwin)
        self.mainwin = mainwin
        self.setFaceType(KPageDialog.Tree)
        self.setButtons(KPageDialog.ButtonCode(
            KPageDialog.Default | KPageDialog.Apply |
            KPageDialog.Ok | KPageDialog.Cancel))
        self.setCaption(i18n("Configure"))
        self.setDefaultButton(KPageDialog.Ok)
        self.enableButton(KPageDialog.Apply, False)
        QObject.connect(self, SIGNAL("applyClicked()"), self.applyClicked)
        QObject.connect(self, SIGNAL("defaultClicked()"), self.defaultClicked)
        self.pages = [
            GeneralPreferences(self),
            Commands(self),
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
        
    def applyClicked(self):
        self.saveSettings()
        self.changed(False)

    def defaultClicked(self):
        for page in self.pages:
            page.defaults()
        self.changed()
            
    def loadSettings(self):
        for page in self.pages:
            page.loadSettings()
        
    def saveSettings(self):
        for page in self.pages:
            page.saveSettings()
            

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
        item = dialog.addPage(self, i18n("General Preferences"))
        item.setHeader(i18n("General Frescobaldi Preferences"))
        item.setIcon(KIcon("configure"))
        
        self.checks = []
        for title, name, default in (
            (i18n("Save document when LilyPond is run"),
                "save on run", False),
            (i18n("Let LilyPond delete intermediate output files"),
                "delete intermediate files", True),
        ):
            b = QCheckBox(title, self)
            QObject.connect(b, SIGNAL("clicked()"), dialog.changed)
            self.checks.append((b, name, default))
        self.layout().addStretch(1)

    def defaults(self):
        for widget, name, default in self.checks:
            widget.setChecked(default)
            
    def loadSettings(self):
        conf = config("preferences")
        for widget, name, default in self.checks:
            widget.setChecked(conf.readEntry(name, QVariant(default)).toBool())

    def saveSettings(self):
        conf = config("preferences")
        for widget, name, default in self.checks:
            conf.writeEntry(name, QVariant(widget.isChecked()))


class Commands(QWidget):
    """
    Settings regarding commands of lilypond and associated programs
    """
    def __init__(self, dialog):
        QWidget.__init__(self, dialog)
        self.dialog = dialog
        item = dialog.addPage(self, i18n("Paths"))
        item.setHeader(i18n("Paths to programs or data used by Frescobaldi"))
        item.setIcon(KIcon("utilities-terminal"))
        
        layout = QGridLayout(self)
        
        # commands
        self.commands = []
        for name, default, title, lineedit, tooltip in (
            ('lilypond', 'lilypond', "LilyPond:", ExecLineEdit,
                i18n("Name or full path of the LilyPond program.")),
            ('convert-ly', 'convert-ly', "Convert-ly:", ExecLineEdit,
                i18n("Name or full path of the convert-ly program.")),
            ('lpr', 'lpr', i18n("Printcommand:"), ExecArgsLineEdit,
                i18n("Command to print a PDF file, for example lpr or "
                  "kprinter. You may add some arguments, e.g. "
                  "lpr -P myprinter.")),
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
            layout.addWidget(label, len(self.commands), 0)
            layout.addWidget(widget, len(self.commands), 1)
            self.commands.append((widget, name, default))
        
        # default directory
        l = QLabel(i18n("Default directory:"))
        self.folder = KUrlRequester()
        l.setBuddy(self.folder)
        row = layout.rowCount()
        tooltip = i18n("The default folder for LilyPond documents "
                       "(may be empty).")
        l.setToolTip(tooltip)
        self.folder.setToolTip(tooltip)
        layout.addWidget(l, row, 0)
        layout.addWidget(self.folder, row, 1)
        self.folder.setMode(KFile.Mode(
            KFile.Directory | KFile.ExistingOnly | KFile.LocalOnly))
        self.folder.button().setIcon(KIcon("document-open-folder"))
        
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

    def setHyphenPaths(self, paths):
        # disconnect first; unfortunately QTextEdit has no textEdited signal...
        QObject.disconnect(self.hyphenPaths, SIGNAL("textChanged()"),
            self.dialog.changed)
        self.hyphenPaths.setPlainText('\n'.join(unicode(p) for p in paths))
        QObject.connect(self.hyphenPaths, SIGNAL("textChanged()"),
            self.dialog.changed)
        
    def defaults(self):
        for widget, name, default in self.commands:
            widget.setText(default)
        self.setHyphenPaths(frescobaldi_app.hyphen.defaultPaths)
        self.folder.setPath('')
        
    def loadSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            widget.setText(conf.readEntry(name, default))
        paths = config("hyphenation").readEntry("paths",
            frescobaldi_app.hyphen.defaultPaths)
        self.setHyphenPaths(paths)
        changed = lambda arg: self.dialog.changed()
        QObject.disconnect(self.folder, SIGNAL("textChanged(const QString&)"),
            changed)
        self.folder.setPath(config("preferences").readPathEntry(
            "default directory", ""))
        QObject.connect(self.folder, SIGNAL("textChanged(const QString&)"),
            changed)
        
    def saveSettings(self):
        conf = config("commands")
        for widget, name, default in self.commands:
            if widget.text():
                conf.writeEntry(name, widget.text())
        paths = [p for p in unicode(self.hyphenPaths.toPlainText()).splitlines()
            if p]
        config("hyphenation").writeEntry("paths", paths)
        # reload the table of hyphenation dictionaries
        frescobaldi_app.hyphen.findDicts()
        config("preferences").writePathEntry("default directory",
            self.folder.url().path())


def config(group):
    return KGlobal.config().group(group)

