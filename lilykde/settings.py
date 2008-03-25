"""
the configuration dialog
"""

from qt import *
from kdeui import KPushButton, KStdGuiItem

from lilykde.util import htmlescape
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
            m.load(config())

    def saveSettings(self):
        for m in self.modules:
            m.save(config())

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
        for name, title, default in (
            ('lilypond', _("Lilypond:"), 'lilypond'),
            ('convert-ly', _("Convert-ly:"), 'convert-ly'),
            ('lpr', _("Printcommand:"), 'lpr'),
        ):
            self.layout.addWidget(QLabel(title, self), len(self.commands), 0)
            widget = QLineEdit(self)
            self.layout.addWidget(widget, len(self.commands), 1)
            self.commands.append((name, widget, default))

    def defaults(self):
        for n, w, d in self.commands:
            w.setText(d)

    def load(self, c):
        conf = c.group("commands")
        for n, w, d in self.commands:
            w.setText(conf.get(n, d))

    def save(self, c):
        conf = c.group("commands")
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

    def load(self, c):
        conf = c.group("hyphenation")
        from lilykde.hyphen import defaultpaths
        paths = conf["paths"] or '\n'.join(defaultpaths)
        self.pathList.setText(paths)

    def save(self, c):
        conf = c.group("hyphenation")
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

        def action(name, title):
            widget = QCheckBox(title, self)
            self.layout.addWidget(widget)
            return name, widget

        self.actions = (
            action('open_folder', _("Open folder")),
            action('open_pdf', _("Open PDF")),
            action('print_pdf', _("Print")),
            action('email_pdf', _("Email PDF")),
            action('play_midi', _("Play MIDI")),
        )

    def defaults(self):
        for a, w in self.actions:
            w.setChecked(True)

    def load(self, c):
        conf = c.group("actions")
        for a, w in self.actions:
            check = bool(conf[a] != '0')
            w.setChecked(check)

    def save(self, c):
        conf = c.group("actions")
        for a, w in self.actions:
            conf[a] = 1 and w.isChecked() or 0


# kate: indent-width 4;
