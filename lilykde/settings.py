"""
the configuration dialog
"""

from qt import *
from kdeui import KPushButton, KStdGuiItem

from lilykde.util import htmlescape
from lilykde.widgets import ExecLineEdit
from lilykde import config

# Translate the messages
from lilykde.i18n import _


class Settings(QFrame):
    """
    Create a settings dialog widget for LilyKDE.
    Currently using a tab widget, ugly because of the nesting but simple.
    """
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.layout = QVBoxLayout(self)
        self.layout.setMargin(4)
        self.tab = QTabWidget(self)
        self.tab.setMargin(4)
        self.defaultsButton = KPushButton(KStdGuiItem.defaults(), self)
        self.applyButton = KPushButton(KStdGuiItem.apply(), self)
        self.resetButton = KPushButton(KStdGuiItem.reset(), self)
        self.layout.addWidget(self.tab)
        hbox = QHBoxLayout()
        hbox.addWidget(self.defaultsButton)
        hbox.addStretch(1)
        hbox.addWidget(self.applyButton)
        hbox.addWidget(self.resetButton)
        self.layout.addLayout(hbox)
        self.modules = []
        # instantiate all modules
        for moduleclass in (
                CommandSettings,
                ActionSettings,
                HyphenSettings,
            ):
            module = moduleclass(self.tab)
            self.tab.addTab(module, module.title)
            self.modules.append(module)

        self.connect(self.defaultsButton, SIGNAL("clicked()"), self.defaults)
        self.connect(self.applyButton, SIGNAL("clicked()"), self.saveSettings)
        self.connect(self.resetButton, SIGNAL("clicked()"), self.loadSettings)
        self.loadSettings()
        self.setMinimumHeight(240)
        self.setMinimumWidth(400)

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
        self.layout = QGridLayout(self)
        self.commands = []
        for name, default, title, tooltip in (
            ('lilypond', 'lilypond', "Lilypond:",
                _("Name or full path of the LilyPond program.")),
            ('convert-ly', 'convert-ly', "Convert-ly:",
                _("Name or full path of the convert-ly program.")),
            ('rumor', 'rumor', "Rumor:",
                _("Name or full path of the Rumor program.")),
            ('lpr', 'lpr', _("Printcommand:"),
                _("Command to print a PDF file, for example lpr or "
                  "kprinter. You may add some arguments, e.g. "
                  "lpr -P myprinter.")),
        ):
            label = QLabel(title, self)
            widget = ExecLineEdit(self)
            QToolTip.add(label, tooltip)
            QToolTip.add(widget, tooltip)
            self.layout.addWidget(label, len(self.commands), 0)
            self.layout.addWidget(widget, len(self.commands), 1)
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
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel('<p>%s</p>' % htmlescape (_(
            "Paths to search for hyphenation dictionaries of OpenOffice.org, "
            "Scribus, KOffice, etc, one per line. "
            "If you leave out the starting slash, the prefixes from the "
            "KDEDIRS environment variable are prepended.")), self))
        self.pathList = QTextEdit(self)
        self.layout.addWidget(self.pathList)

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
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel('<p>%s</p>' % htmlescape (_(
            "Check the actions you want to display (if applicable) after "
            "LilyPond has successfully compiled your document.")), self))

        def action(name, title, tooltip):
            widget = QCheckBox(title, self)
            QToolTip.add(widget, tooltip)
            self.layout.addWidget(widget)
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


# kate: indent-width 4;
