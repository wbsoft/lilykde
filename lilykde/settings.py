# This file is part of LilyKDE, http://lilykde.googlecode.com/
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
The configuration dialog
"""

from qt import *
from kdeui import KPushButton, KStdGuiItem

from lilykde.util import htmlescape
from lilykde.widgets import ExecLineEdit, ExecArgsLineEdit
from lilykde import config

# Translate the messages
from lilykde.i18n import _

def settings(parent):
    Settings(parent,
        CommandSettings,
        ActionSettings,
        HyphenSettings,
        GeneralSettings,
    ).show()


class Settings(QFrame):
    """
    Create a settings dialog widget for LilyKDE.
    Currently using a tab widget, ugly because of the nesting but simple.
    """
    def __init__(self, parent, *moduleClasses):
        QFrame.__init__(self, parent)
        layout = QVBoxLayout(self)
        layout.setMargin(4)
        self.tab = QTabWidget(self)
        self.tab.setMargin(4)
        defaultsButton = KPushButton(KStdGuiItem.defaults(), self)
        applyButton = KPushButton(KStdGuiItem.apply(), self)
        resetButton = KPushButton(KStdGuiItem.reset(), self)
        layout.addWidget(self.tab)
        hbox = QHBoxLayout()
        hbox.addWidget(defaultsButton)
        hbox.addStretch(1)
        hbox.addWidget(applyButton)
        hbox.addWidget(resetButton)
        layout.addLayout(hbox)
        self.setMinimumHeight(240)
        self.setMinimumWidth(400)
        self.connect(defaultsButton, SIGNAL("clicked()"), self.defaults)
        self.connect(applyButton, SIGNAL("clicked()"), self.saveSettings)
        self.connect(resetButton, SIGNAL("clicked()"), self.loadSettings)
        self.modules = []
        # instantiate all modules
        for mc in moduleClasses:
            self.addModule(mc)

    def addModule(self, moduleClass):
        m = moduleClass(self.tab)
        self.tab.addTab(m, m.title)
        self.modules.append(m)
        m.load()

    def loadSettings(self):
        for m in self.modules:
            m.load()

    def saveSettings(self):
        for m in self.modules:
            m.save()

    def defaults(self):
        for m in self.modules:
            m.defaults()


class CommandSettings(QFrame):
    """
    Settings regarding commands of lilypond's associated programs
    """
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.title = _("Commands")
        layout = QGridLayout(self)
        self.commands = []
        for name, default, title, lineedit, tooltip in (
            ('lilypond', 'lilypond', "LilyPond:", ExecLineEdit,
                _("Name or full path of the LilyPond program.")),
            ('convert-ly', 'convert-ly', "Convert-ly:", ExecLineEdit,
                _("Name or full path of the convert-ly program.")),
            ('lpr', 'lpr', _("Printcommand:"), ExecArgsLineEdit,
                _("Command to print a PDF file, for example lpr or "
                  "kprinter. You may add some arguments, e.g. "
                  "lpr -P myprinter.")),
            ('rumor', 'rumor', "Rumor:", ExecLineEdit,
                _("Name or full path of the Rumor program.")),
            ('aconnect', 'aconnect', "Aconnect:", ExecLineEdit,
                _("Name or full path of the aconnect program (part of ALSA, "
                  "for MIDI input and playback using Rumor).")),
            ('timidity', 'timidity -iA -B2,8 -Os -EFreverb=0', "Timidity:",
                ExecArgsLineEdit,
                _("Full command to start Timidity (or any other program) "
                  "as an ALSA MIDI client.")),
        ):
            label = QLabel(title, self)
            widget = lineedit(self)
            QToolTip.add(label, tooltip)
            QToolTip.add(widget, tooltip)
            layout.addWidget(label, len(self.commands), 0)
            layout.addWidget(widget, len(self.commands), 1)
            self.commands.append((name, widget, default))

    def defaults(self):
        for n, w, d in self.commands:
            w.setText(d)

    def load(self):
        conf = config("commands")
        for n, w, d in self.commands:
            w.setText(conf.get(n, d))

    def save(self):
        conf = config("commands")
        for n, w, d in self.commands:
            if w.text():
                conf[n] = w.text()


class HyphenSettings(QFrame):
    """
    Settings regarding the hyphenation of Lyrics
    """
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.title = _("Hyphenation")
        QVBoxLayout(self).setAutoAdd(True)
        QLabel('<p>%s</p>' % htmlescape (_(
            "Paths to search for hyphenation dictionaries of OpenOffice.org, "
            "Scribus, KOffice, etc, one per line. "
            "If you leave out the starting slash, the prefixes from the "
            "KDEDIRS environment variable are prepended.")), self)
        self.pathList = QTextEdit(self)

    def defaults(self):
        from lilykde.hyphen import defaultpaths
        self.pathList.setText('\n'.join(defaultpaths))

    def load(self):
        conf = config("hyphenation")
        from lilykde.hyphen import defaultpaths
        paths = conf["paths"] or '\n'.join(defaultpaths)
        self.pathList.setText(paths)

    def save(self):
        conf = config("hyphenation")
        conf["paths"] = self.pathList.text()
        import lilykde.hyphen
        lilykde.hyphen.findDicts()


class ActionSettings(QFrame):
    """
    Which actions to display at the end of a succesful LilyPond run
    """
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.title = _("Actions")
        QVBoxLayout(self).setAutoAdd(True)
        QLabel('<p>%s</p>' % htmlescape (_(
            "Check the actions you want to display (if applicable) after "
            "LilyPond has successfully compiled your document.")), self)

        def action(name, title, tooltip):
            widget = QCheckBox(title, self)
            QToolTip.add(widget, tooltip)
            return name, widget

        self.actions = (
            action('open_folder', _("Open folder"), _(
                "Open the folder containing the LilyPond and PDF documents.")),
            action('open_pdf', _("Open PDF"), _(
                "Open the generated PDF file with the default PDF viewer.")),
            action('print_pdf', _("Print"), _(
                "Print the PDF using the print command set in the Commands "
                "settings page.")),
            action('email_pdf', _("Email PDF"), _(
                "Attach the PDF to an email message.")),
            action('play_midi', _("Play MIDI"), _(
                "Play the generated MIDI files using the default MIDI player "
                "(Timidity++ is recommended).")),
        )

    def defaults(self):
        for a, w in self.actions:
            w.setChecked(True)

    def load(self):
        conf = config("actions")
        for a, w in self.actions:
            check = bool(conf[a] != '0')
            w.setChecked(check)

    def save(self):
        conf = config("actions")
        for a, w in self.actions:
            conf[a] = w.isChecked() and 1 or 0


class GeneralSettings(QFrame):
    """
    General preferences
    """
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.title = _("Preferences")
        QVBoxLayout(self).setAutoAdd(True)

        self.checks = [(QCheckBox(t, self), c, d) for t, c, d in (
            (_("Keep undocked windows on top of Kate"),
                 "keep undocked on top", 1),
            (_("Save document when LilyPond is run"),
                "save on run", 0),
            )]

    def defaults(self):
        for w, c, d in self.checks:
            w.setChecked(d)

    def load(self):
        conf = config("preferences")
        for w, c, d in self.checks:
            w.setChecked(bool(int(conf.get(c, d))))

    def save(self):
        conf = config("preferences")
        for w, c, d in self.checks:
            conf[c] = w.isChecked() and 1 or 0



# kate: indent-width 4;
