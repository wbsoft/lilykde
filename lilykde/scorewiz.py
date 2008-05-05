"""
A Score Wizard

provides a wizard dialog to quickly set up a LilyPond score.

The user can select items (staffs or different types of staffgroup)
and define their order. All items will live in Score, i.e.

general preambule (main settings, title etc.)
preambule of item1 (assignments etc.)
preambule of item2

\score {
  <<
    music of item1
    music of item2
  >>
  \layout {
    general layout stuff
  }
  optional midi block
}

aftermath of item1 (additional score blocks,)
aftermath of item2 (e.g. for extra midi output files)


Wizard:

    Page 1:

        Titling, etc.

    page 2:

        Parts with associated settings



"""

import re
from string import Template
from time import time

from qt import *
from kdecore import KCompletion
from kdeui import *

import kate

from lilykde import config
from lilykde.util import py2qstringlist, qstringlist2py
from lilykde.widgets import TapButton

# Translate messages
from lilykde.i18n import _

headers = (
    ('dedication',  _("Dedication")),
    ('title',       _("Title")),
    ('subtitle',    _("Subtitle")),
    ('subsubtitle', _("Subsubtitle")),
    ('instrument',  _("Instrument")),
    ('composer',    _("Composer")),
    ('arranger',    _("Arranger")),
    ('poet',        _("Poet")),
    ('meter',       _("Meter")),
    ('piece',       _("Piece")),
    ('opus',        _("Opus")),
    ('copyright',   _("Copyright")),
    ('tagline',     _("Tagline")),
)

headerNames = zip(*headers)[0]

modes = (
    ('major',       _("Major")),
    ('minor',       _("Minor")),
    ('ionian',      _("Ionian")),
    ('dorian',      _("Dorian")),
    ('phrygian',    _("Phrygian")),
    ('lydian',      _("Lydian")),
    ('mixolydian',  _("Mixolydian")),
    ('aeolian',     _("Aeolian")),
    ('locrian',     _("Locrian")),
)

keys = {
    'nederlands': (
        ('c', 'C'),
        ('cis', 'Cis'),
        ('des', 'Des'),
        ('d', 'D'),
        ('dis', 'Dis'),
        ('es', 'Es'),
        ('e', 'E'),
        ('f', 'F'),
        ('fis', 'Fis'),
        ('ges', 'Ges'),
        ('g', 'G'),
        ('gis', 'Gis'),
        ('as', 'As'),
        ('a', 'A'),
        ('ais', 'Ais'),
        ('bes', 'Bes'),
        ('b', 'B'),
    ),
    'english': (
        ('c', 'C'),
        ('cs', 'C#'),
        ('df', 'Db'),
        ('d', 'Ab'),
        ('ds', 'D#'),
        ('ef', 'Eb'),
        ('e', 'E'),
        ('f', 'F'),
        ('fs', 'F#'),
        ('gf', 'Gb'),
        ('g', 'G'),
        ('gs', 'G#'),
        ('af', 'Ab'),
        ('a', 'A'),
        ('as', 'A#'),
        ('bf', 'Bb'),
        ('b', 'B'),
    ),
    'deutsch': (
        ('c', 'C'),
        ('cis', 'Cis'),
        ('des', 'Des'),
        ('d', 'D'),
        ('dis', 'Dis'),
        ('es', 'Es'),
        ('e', 'E'),
        ('f', 'F'),
        ('fis', 'Fis'),
        ('ges', 'Ges'),
        ('g', 'G'),
        ('gis', 'Gis'),
        ('as', 'As'),
        ('a', 'A'),
        ('ais', 'Ais'),
        ('b', 'B'),
        ('h', 'H'),
    ),
    'norsk': (
        ('c', 'C'),
        ('cis', 'Ciss'),
        ('des', 'Dess'),
        ('d', 'D'),
        ('dis', 'Diss'),
        ('es', 'Ess'),
        ('e', 'E'),
        ('f', 'F'),
        ('fis', 'Fiss'),
        ('ges', 'Gess'),
        ('g', 'G'),
        ('gis', 'Giss'),
        ('as', 'Ass'),
        ('a', 'A'),
        ('ais', 'Aiss'),
        ('b', 'B'),
        ('h', 'H'),
    ),
    'italiano': (
        ('do', 'Do'),
        ('dod', 'Do diesis'),
        ('reb', 'Re bemolle'),
        ('re', 'Re'),
        ('red', 'Re diesis'),
        ('mib', 'Mi bemolle'),
        ('mi', 'Mi'),
        ('fa', 'Fa'),
        ('fad', 'Fa diesis'),
        ('solb', 'Sol bemolle'),
        ('sol', 'Sol'),
        ('sold', 'Sol diesis'),
        ('lab', 'La bemolle'),
        ('la', 'La'),
        ('lad', 'La diesis'),
        ('sib', 'Si bemolle'),
        ('si', 'Si'),
    ),
    'espanol': (
        ('do', 'Do'),
        ('dos', 'Do sostenido'),
        ('reb', 'Re bemol'),
        ('re', 'Re'),
        ('res', 'Re sostenido'),
        ('mib', 'Mi bemol'),
        ('mi', 'Mi'),
        ('fa', 'Fa'),
        ('fas', 'Fa sostenido'),
        ('solb', 'Sol bemol'),
        ('sol', 'Sol'),
        ('sols', 'Sol sostenido'),
        ('lab', 'La bemol'),
        ('la', 'La'),
        ('las', 'La sostenido'),
        ('sib', 'Si bemol'),
        ('si', 'Si'),
    ),
    'vlaams': (
        ('do', 'Do'),
        ('dok', 'Do kruis'),
        ('reb', 'Re mol'),
        ('re', 'Re'),
        ('rek', 'Re kruis'),
        ('mib', 'Mi mol'),
        ('mi', 'Mi'),
        ('fa', 'Fa'),
        ('fak', 'Fa kruis'),
        ('solb', 'Sol mol'),
        ('sol', 'Sol'),
        ('solk', 'Sol kruis'),
        ('lab', 'La mol'),
        ('la', 'La'),
        ('lak', 'La kruis'),
        ('sib', 'Si mol'),
        ('si', 'Si'),
    ),
}

keys['svenska'] = keys['norsk']
keys['suomi'] = keys['deutsch']
keys['catalan'] = keys['italiano']
keys['portuges'] = keys['espanol']

keyNames = dict((n, tuple(t for p, t in v)) for n, v in keys.iteritems())

durations = ['16', '16.', '8', '8.', '4', '4.', '2', '2.', '1', '1.']

html = Template(r"""<table style='font-family:serif;'>
<tr><td colspan=3 align=center>$dedication</td><tr>
<tr><td colspan=3 align=center style='font-size:20pt;'><b>$title</b></td><tr>
<tr><td colspan=3 align=center style='font-size:12pt;'><b>$subtitle</b></td><tr>
<tr><td colspan=3 align=center><b>$subsubtitle</b></td><tr>
<tr>
    <td align=left width='25%%'>$poet</td>
    <td align=center><b>$instrument</b></td>
    <td align=right width='25%%'>$composer</td>
</tr>
<tr>
    <td align=left>$meter</td>
    <td> </td>
    <td align=right>$arranger</td>
</tr>
<tr>
    <td align=left>$piece</td>
    <td> </td>
    <td align=right>$opus</td>
</tr>
<tr><td colspan=3 align=center><img src='scorewiz.png'></td></tr>
<tr><td colspan=3 align=center>$copyright <i>(%s)</i></td></tr>
<tr><td colspan=3 align=center>$tagline <i>(%s)</i></td></tr>
</table>""").substitute(
    dict((k, "<a href='%s'>%s</a>" % (k, v)) for k, v in headers)) % (
        _("bottom of first page"),
        _("bottom of last page"))


class part(object):
    """
    The base class for LilyKDE part types.
    """
    def __init__(self, parts):
        """
        parts is the Parts instance (the Parts selection widget).

        Create two widgets:
        - a QListBoxText for in the score view
        - a QGroupBox for in the widget stack, with settings
        The listboxitem carries a pointer to ourselves.
        """
        self.l = QListBoxText(parts.score, self.name)
        self.w = QVGroupBox(self.name, parts.part)
        parts.part.addWidget(self.w)
        self.l.part = self

    def setName(self, name):
        self.l.setText(name)
        self.w.setTitle(name)


class Titles(object):
    """
    A widget where users can fill in all the titles that are put
    in the \header block.
    """

    def __init__(self, parent):
        self.p = parent.addPage(_("Titles and Headers"))

        l = QHBoxLayout(self.p)
        # The html view with the score layout example
        t = KTextBrowser(self.p, None, True)
        t.setLinkUnderline(False)
        t.setText(html)
        t.setMinimumWidth(t.contentsWidth() + 10)
        t.setMinimumHeight(t.contentsHeight() + 5)
        l.addWidget(t)
        QObject.connect(t, SIGNAL("urlClick(const QString &)"), self.focus)

        l.addSpacing(6)

        g = QGridLayout(len(headers), 2, 0)
        g.setColSpacing(1, 200)
        l.addLayout(g)

        for c, h in enumerate(headers):
            name, title = h
            l = QLabel(title + ":", self.p)
            e = KLineEdit(self.p, name)
            l.setBuddy(e)
            g.addWidget(l, c, 0)
            g.addWidget(e, c, 1)
            # set completion items
            parent.complete(e)

    def focus(self, name):
        """
        Give the text entry for the clicked header name keyboard focus.
        """
        self.p.child(str(name)).setFocus()

    def read(self):
        """
        Return a dictionary with header names mapped to
        unicode values for all the text entries.
        """
        return dict((h, unicode(self.p.child(h).text())) for h in headerNames)


class Parts(object):
    """
    The widget where users can select parts and adjust their settings.
    """
    def __init__(self, parent):
        self.p = parent.addPage(_("Parts"))

        # We have three main panes:
        # all part types (in a treeview),
        # selected parts (in a list view)
        # part settings of the selected part.

        p = QSplitter(self.p)
        QHBoxLayout(self.p).addWidget(p)

        # all parts
        w = QVBox(p)
        self.all = QListView(w)
        b = KPushButton(KStdGuiItem.add(), w)
        QToolTip.add(b, _("Add selected part to your score."))
        QObject.connect(self.all, SIGNAL(
            "doubleClicked(QListViewItem *, const QPoint &, int)"), self.add)
        QObject.connect(b, SIGNAL("clicked()"), self.add)
        self.all.setSorting(-1)
        self.all.setResizeMode(QListView.AllColumns)
        self.all.setSelectionMode(QListView.Extended)
        self.all.addColumn(_("Parts"))

        from lilykde.parts import categories
        for name, partTypes in categories:
            cat = QListViewItem(self.all, name)
            cat.setSelectable(False)
            cat.setOpen(True)
            for partType in partTypes:
                part = QListViewItem(cat, partType.name)
                part.partType = partType

        # score
        w = QVBox(p)
        self.score = QListBox(w)
        self.score.setSelectionMode(QListBox.Extended)
        QObject.connect(self.score, SIGNAL("highlighted(QListBoxItem*)"),
            self.select)
        w = QHBox(w)
        b = KPushButton(KStdGuiItem.remove(), w)
        QToolTip.add(b, _("Remove selected part from your score."))
        QObject.connect(b, SIGNAL("clicked()"), self.remove)

        up = QToolButton(Qt.UpArrow, w)
        down = QToolButton(Qt.DownArrow, w)
        QToolTip.add(up, _("Move selected part up."))
        QToolTip.add(down, _("Move selected part down."))
        QObject.connect(up, SIGNAL("clicked()"), self.moveUp)
        QObject.connect(down, SIGNAL("clicked()"), self.moveDown)

        # part config
        self.part = QWidgetStack(p)

    def add(self, item = None, *args):
        """
        Add the selected part types to the score.
        Discards the args from the doubleClicked signal.
        Selects the first part if the list was empty.
        """
        # return when a category is doubleclicked.
        if item and item.depth() == 0:
            return
        c = self.score.count()
        it = QListViewItemIterator(self.all, QListViewItemIterator.Selected)
        while it.current():
            it.current().partType(self)
            it += 1
        if c == 0 and self.score.count() > 0:
            self.score.setCurrentItem(0)
            self.score.setSelected(0, True)

    def select(self, item):
        if item:
            self.part.raiseWidget(item.part.w)

    def remove(self):
        """ Remove selected parts from the score. """
        for index in reversed(range(self.score.count())):
            if self.score.isSelected(index):
                self.part.removeWidget(self.score.item(index).part.w)
                self.score.item(index).part.w.hide()
                self.score.removeItem(index)

    def moveUp(self):
        """ Move selected parts up. """
        for index in range(1, self.score.count()):
            if self.score.isSelected(index):
                item = self.score.item(index)
                self.score.takeItem(item)
                self.score.insertItem(item, index - 1)

    def moveDown(self):
        """ Move selected parts down. """
        for index in reversed(range(self.score.count() - 1)):
            if self.score.isSelected(index):
                item = self.score.item(index)
                self.score.takeItem(item)
                self.score.insertItem(item, index + 1)


class Settings(object):
    """
    The widget where users can set other preferences.
    """
    def __init__(self, parent):
        self.p = parent.addPage(_("Score settings"))
        score = QVGroupBox(_("Score settings"), self.p)
        lily =  QVGroupBox(_("LilyPond"), self.p)
        prefs = QVGroupBox(_("General preferences"), self.p)
        h = QHBoxLayout(self.p)
        v = QVBoxLayout()
        h.addLayout(v)
        v.addWidget(score)
        v.addSpacing(4)
        v.addWidget(lily)
        h.addSpacing(8)
        h.addWidget(prefs)

        # Score settings
        h = QHBox(score)
        h.setSpacing(2)
        l = QLabel(_("Key signature:"), h)
        self.key = QComboBox(False, h) # the key names are filled in later
        self.mode = QComboBox(False, h)
        self.mode.insertStringList(py2qstringlist(t for n, t in modes))
        l.setBuddy(self.key)

        h = QHBox(score)
        h.setSpacing(2)
        l = QLabel(_("Time signature:"), h)
        self.time = QComboBox(True, h)
        self.time.insertItem(QPixmap.fromMimeSource('c44.png'), '(4/4)')
        self.time.insertItem(QPixmap.fromMimeSource('c22.png'), '(2/2)')
        self.time.insertStringList(py2qstringlist((
            '2/4', '3/4', '4/4', '5/4', '6/4', '7/4',
            '2/2', '3/2', '4/2',
            '3/8', '5/8', '6/8', '7/8', '8/8', '9/8', '12/8',
            '3/16', '6/16', '12/16')))
        l.setBuddy(self.time)

        h = QHBox(score)
        h.setSpacing(2)
        l = QLabel(_("Pickup measure:"), h)
        self.pickup = QComboBox(False, h)
        self.pickup.setMinimumHeight(24)
        self.pickup.insertItem(_("None"))
        pix = [QPixmap.fromMimeSource('note_%s.png' % d.replace('.', 'd'))
            for d in durations]
        for p in pix:
            self.pickup.insertItem(p)
        l.setBuddy(self.pickup)

        h = QHBox(score)
        h.setSpacing(2)
        l = QLabel(_("Metronome mark:"), h)
        self.metroDur = QComboBox(False, h)
        self.metroDur.setMinimumHeight(24)
        l.setBuddy(self.metroDur)
        for d in pix:
            self.metroDur.insertItem(d)
        self.metroDur.setCurrentItem(durations.index('4'))
        l = QLabel('=', h)
        l.setMaximumWidth(12)
        self.metroVal = QComboBox(True, h)
        self.metroValues, start = [], 40
        for end, step in (60, 2), (72, 3), (120, 4), (144, 6), (210, 8):
            self.metroValues.extend(range(start, end, step))
            start = end
        self.metroVal.insertStringList(py2qstringlist(map(str, self.metroValues)))
        self.metroVal.setCurrentText('100')
        tap = TapButton(h, self.tap)

        h = QHBox(score)
        h.setSpacing(2)
        l = QLabel(_("Tempo indication:"), h)
        self.tempoInd = KLineEdit(h, "tempo")
        parent.complete(self.tempoInd)
        l.setBuddy(self.tempoInd)
        QToolTip.add(self.tempoInd, _(
            "A tempo indication, e.g. \"Allegro.\""))

        # LilyPond settings
        h = QHBox(lily)
        h.setSpacing(2)
        l = QLabel(_("Language:"), h)
        self.lylang = QComboBox(False, h)
        l.setBuddy(self.lylang)
        self.lylang.insertItem(_("Default"))
        self.lylang.insertStringList(py2qstringlist(
            l.title() for l in sorted(keys)))
        QToolTip.add(self.lylang, _(
            "The LilyPond language you want to use for the pitch names."))
        QObject.connect(self.lylang, SIGNAL("activated(const QString&)"),
            self.setLanguage)
        self.setLanguage('nederlands')  # TODO: set to saved default

        h = QHBox(lily)
        h.setSpacing(2)
        l = QLabel(_("Version:"), h)
        self.lyversion = QComboBox(True, h)
        l.setBuddy(self.lyversion)
        from lilykde.version import version
        try: self.lyversion.insertItem("%d.%d.%d" % version)
        except: pass
        self.lyversion.insertStringList(py2qstringlist(('2.10.0', '2.11.0')))
        QToolTip.add(self.lyversion, _(
            "The LilyPond version you will be using for this document."))


        # General preferences
        self.typq = QCheckBox(_("Use typographical quotes"), prefs)
        QToolTip.add(self.typq, _(
            "Replace normal quotes in titles with nice typographical quotes."))

        self.tagl = QCheckBox(_("Remove default tagline"), prefs)
        QToolTip.add(self.tagl, _(
            "Suppress the default tagline output by LilyPond."))

    def tap(self, bpm):
        """ Tap the tempo tap button """
        l = [abs(t - bpm) for t in self.metroValues]
        m = min(l)
        if m < 6:
            self.metroVal.setCurrentItem(l.index(m))

    def setLanguage(self, lang):
        lang = unicode(lang).lower()    # can be QString
        if lang not in keyNames:
            lang = 'nederlands'
        index = self.key.currentItem()
        self.key.clear()
        self.key.insertStringList(py2qstringlist(keyNames[lang]))
        self.key.setCurrentItem(index)

    def getLanguage(self):
        lang = unicode(self.lylang.currentText()).lower()
        return lang in keys and lang or None

    def getKeySig(self):
        lang = self.getLanguage() or "nederlands"
        key = keyNames[lang][self.key.currentItem()][0]
        mode = modes[self.mode.currentItem()][0]
        return key, mode


class ScoreWizard(KDialogBase):
    """ The main score wizard dialog. """
    def __init__(self, parent):
        KDialogBase.__init__(self, KDialogBase.Tabbed,
            "LilyKDE " + _("Score Setup Wizard"),
            KDialogBase.Ok | KDialogBase.Cancel, KDialogBase.Ok, parent)
        self.completableWidgets = []
        self.titles = Titles(self)
        self.parts = Parts(self)
        self.settings = Settings(self)
        self.loadCompletions()

    def complete(self, w):
        """ Stores the widget and its completion data. """
        self.completableWidgets.append(w)

    def loadCompletions(self):
        """ Loads the completion data from the config. """
        conf = config("scorewiz completion")
        for w in self.completableWidgets:
            compObj, name = w.completionObject(), str(w.name())
            compObj.setOrder(KCompletion.Sorted)
            compObj.setItems(py2qstringlist(conf.get(name, '').splitlines()))

    def saveCompletions(self):
        """ Saves completion items for all lineedits. """
        conf = config("scorewiz completion")
        for w in self.completableWidgets:
            name, text = str(w.name()), unicode(w.text())
            items = qstringlist2py(w.completionObject().items())
            if len(text) > 1 and text not in items:
                items.append(text)
            conf[name] = '\n'.join(items)

    def format(self, text):
        """ Formats a string of text according to preferences """
        # typographical quotes?
        if self.settings.typq.isChecked():
            text = re.sub(r'"(.*?)"', u'\u201C\\1\u201D', text)
            text = re.sub(r"'(.*?)'", u'\u2018\\1\u2019', text)
            text = text.replace("'", u'\u2018')
        # escape regular double quotes
        text = text.replace('"', '\\"')
        # quote the string
        return '"%s"' % text

    def printout(self):
        """
        Creates the score output and writes it to the current document.
        """
        output = []
        out = output.append

        # version:
        out('\\version "%s"\n' %
            unicode(self.settings.lyversion.currentText()))

        # language:
        lang = self.settings.getLanguage()
        if lang:
            out('\n\\include "%s.ly"\n' % lang)

        # header:
        noTagline = self.settings.tagl.isChecked()
        head = self.titles.read()
        if max(head.values()) or noTagline:
            out('\n\\header {\n')
            for h in headerNames:
                if head[h]:
                    out('  %s = %s\n' % (h, self.format(head[h])))
                elif h == 'tagline' and noTagline:
                    out('  tagline = ##f\n')
            out('}\n\n')





        # and finally print out:
        kate.view().insertText(''.join(output))

    def done(self, result):
        """
        Close the dialog and create the score if Ok was clicked.
        """
        self.saveCompletions()
        if result == KDialogBase.Accepted:
            self.printout()
        KDialogBase.done(self, result)



# kate: indent-width 4;
