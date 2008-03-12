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
        self.applyButton = KPushButton(KStdGuiItem.apply(), self)
        self.resetButton = KPushButton(KStdGuiItem.reset(), self)
        self.layout.addWidget(self.tab)
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.applyButton)
        hbox.addWidget(self.resetButton)
        self.layout.addLayout(hbox)
        self.modules = []
        # instantiate all modules
        for moduleclass in (
                CommandSettings,
                HyphenSettings,
            ):
            module = moduleclass(self.tab)
            self.tab.addTab(module, module.title)
            self.modules.append(module)

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


class CommandSettings(QFrame):
    """
    Settings regarding commands of lilypond's associated programs
    """
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.title = _("Commands")
        self.conf = config.group("commands")

        self.layout = QGridLayout(self, 2, 2)
        self.layout.addWidget(QLabel(_("Lilypond:"), self), 0, 0)
        self.layout.addWidget(QLabel(_("Convert-ly:"), self), 1, 0)
        self.lilyCmd = QLineEdit(self)
        self.convCmd = QLineEdit(self)
        self.layout.addWidget(self.lilyCmd, 0, 1)
        self.layout.addWidget(self.convCmd, 1, 1)

    def load(self):
        self.lilyCmd.setText(self.conf.readEntry("lilypond") or "lilypond")
        self.convCmd.setText(self.conf.readEntry("convert-ly") or "convert-ly")

    def save(self):
        lily = self.lilyCmd.text()
        if lily: self.conf.writeEntry("lilypond", lily)
        conv = self.convCmd.text()
        if conv: self.conf.writeEntry("convert-ly", conv)


class HyphenSettings(QFrame):
    """
    Settings regarding the hyphenation of Lyrics
    """
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.title = _("Hyphenation")
        self.conf = config.group("hyphenation")

        self.layout = QVBoxLayout(self)
        self.label = QLabel('<p>%s</p>' % htmlescape (_(
            "Paths to search for hyphenation dictionaries of OpenOffice.org, "
            "Scribus, KOffice, etc, one per line. "
            "If you leave out the starting slash, the prefixes from the "
            "KDEDIRS environment variable are prepended.")), self)
        self.pathList = QTextEdit(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.pathList)

    def load(self):
        from lilykde.hyphen import defaultpaths
        paths = self.conf.readEntry("paths") or '\n'.join(defaultpaths)
        self.pathList.setText(paths)

    def save(self):
        self.conf.writeEntry("paths", self.pathList.text())
        import lilykde.hyphen
        lilykde.hyphen.findDicts()
