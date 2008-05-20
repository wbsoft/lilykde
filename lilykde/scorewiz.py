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
from rational import Rational

from qt import *
from kdecore import KCompletion
from kdeui import *

import kate

from lilykde import config
from lilykde.util import py2qstringlist, qstringlist2py, romanize
from lilykde.widgets import TapButton
from lilykde.lilydom import *

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

keys = (
    (0, 0), (0, 1),
    (1, -1), (1, 0), (1, 1),
    (2, -1), (2, 0),
    (3, 0), (3, 1),
    (4, -1), (4, 0), (4, 1),
    (5, -1), (5, 0), (5, 1),
    (6, -1), (6, 0),
)

keyNames = {
    'nederlands': (
        'C', 'Cis',
        'Des', 'D', 'Dis',
        'Es', 'E',
        'F', 'Fis',
        'Ges', 'G', 'Gis',
        'As', 'A', 'Ais',
        'Bes', 'B',
    ),
    'english': (
        'C', 'C#',
        'Db', 'D', 'D#',
        'Eb', 'E',
        'F', 'F#',
        'Gb', 'G', 'G#',
        'Ab', 'A', 'A#',
        'Bb', 'B',
    ),
    'deutsch': (
        'C', 'Cis',
        'Des', 'D', 'Dis',
        'Es', 'E',
        'F', 'Fis',
        'Ges', 'G', 'Gis',
        'As', 'A', 'Ais',
        'B', 'H',
    ),
    'norsk': (
        'C', 'Ciss',
        'Dess', 'D', 'Diss',
        'Ess', 'E',
        'F', 'Fiss',
        'Gess', 'G', 'Giss',
        'Ass', 'A', 'Aiss',
        'B', 'H',
    ),
    'italiano': (
        'Do', 'Do diesis',
        'Re bemolle', 'Re', 'Re diesis',
        'Mi bemolle', 'Mi',
        'Fa', 'Fa diesis',
        'Sol bemolle', 'Sol', 'Sol diesis',
        'La bemolle', 'La', 'La diesis',
        'Si bemolle', 'Si',
    ),
    'espanol': (
        'Do', 'Do sostenido',
        'Re bemol', 'Re', 'Re sostenido',
        'Mi bemol', 'Mi',
        'Fa', 'Fa sostenido',
        'Sol bemol', 'Sol', 'Sol sostenido',
        'La bemol', 'La', 'La sostenido',
        'Si bemol', 'Si',
    ),
    'vlaams': (
        'Do', 'Do kruis',
        'Re mol', 'Re', 'Re kruis',
        'Mi mol', 'Mi',
        'Fa', 'Fa kruis',
        'Sol mol', 'Sol', 'Sol kruis',
        'La mol', 'La', 'La kruis',
        'Si mol', 'Si',
    ),
}

keyNames['svenska'] = keyNames['norsk']
keyNames['suomi'] = keyNames['deutsch']
keyNames['catalan'] = keyNames['italiano']
keyNames['portuges'] = keyNames['espanol']

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
    name = 'unnamed'    # subclasses should set a real name as class variable

    @staticmethod
    def numberDoubles(partList):
        """
        Find out if there are part objects in the list of the same type.
        If there are more parts of the same subclass, set their
        num attributes to 1, 2, etc., instead of the default 0.
        """
        types = {}
        for p in partList:
            types.setdefault(p.__class__, []).append(p)

        for t in types.values():
            if len(t) > 1:
                for n, p in enumerate(t):
                    p.num = n + 1

    def __init__(self, parts):
        """
        parts is the Parts instance (the Parts selection widget).

        Creates two widgets:
        - a QListBoxText for in the score view
        - a QGroupBox for in the widget stack, with settings
        The listboxitem carries a pointer to ourselves.
        """
        self.p = parts
        self.l = QListBoxText(parts.score)
        self.l.part = self
        self.w = QVGroupBox(parts.part)
        parts.part.addWidget(self.w)
        self.setName(self.name) # before init self.name is a class variable
        self.widgets(self.w)
        self.num = 0  # used when there are more parts of the same type

    def setName(self, name):
        self.name = name
        self.l.setText(name)
        self.w.setTitle(_("Configure %s") % name)

    def identifier(self):
        """
        Return a name for this part, suitable for use in a LilyPond
        identifier.
        part.numberDoubles must have been run on the part list.
        """
        return self.__class__.__name__ + (self.num and romanize(self.num) or '')

    def select(self):
        self.p.part.raiseWidget(self.w)

    def delete(self):
        self.p.part.removeChild(self.w)
        del self.w, self.l

    def widgets(self, parent):
        """
        Reimplement this method to add widgets with settings.
        The parent currently is a QVGroupBox.
        """
        QLabel('(%s)' % _("No settings available."), parent)

    def run(self, d):
        """
        Create our parts (i.e. call our build() method)
        """
        self.doc = d
        self._partObjs = []
        self._assignments = []
        self.build()

    def assignments(self):
        """
        Return the names of all assignments this part should create.
        """
        return (i.name for i, v in self._assignments)

    def renameAssignment(self, name, newname):
        """
        Rename the named assignment in our part to newname.
        """
        for i, v in self._assignments:
            if i.name == name:
                i.name = newname
                return

    def appendAssignments(self, node):
        """
        Append the LilyDOM assignment nodes to the given node.
        """
        for i, v in self._assignments:
            Assignment(node, i.name).append(v)
            Newline(node)

    def namedContexts(self):
        """
        Return the names of the named contexts in our part.
        """
        return () # FIXME!!!

    def renameNamedContext(self, name, newname):
        """
        Rename the named context to newname.
        """
        pass

    def appendParts(self, node):
        """
        Append the part objects (Staffs etc.) to the given node.
        """
        for i in self._partObjs:
            node.append(i)

    def aftermath(self):
        """
        Add stuff below the main \score.
        """
        d = self.doc
        pass

    def addPart(self, cls, name = None):
        """
        Create and return a new part object (e.g. a PianoStaff)
        """
        p = cls(self.doc, name)
        self._partObjs.append(p)
        return p

    def assignMusic(self, name, addId, octave = 0):
        """
        Creates a stub for music (\relative pitch { \global .... })
        and adds an Identifier to refer to it, to the object
        given in addId.
        """
        i = Identifier(addId, name)
        r = Relative(self.doc)
        Pitch(r, octave, 0, 0)
        s = Seq(r)
        Identifier(s, 'global')
        Newline(s)
        self._assignments.append((i, r))


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
        QLabel('<b>%s</b>' % _("Available parts:"), w)
        self.all = QListView(w)
        b = KPushButton(KStdGuiItem.add(), w)
        QToolTip.add(b, _("Add selected part to your score."))
        QObject.connect(self.all, SIGNAL(
            "doubleClicked(QListViewItem *, const QPoint &, int)"), self.add)
        QObject.connect(b, SIGNAL("clicked()"), self.add)
        self.all.setSorting(-1)
        self.all.setResizeMode(QListView.AllColumns)
        self.all.setSelectionMode(QListView.Extended)
        self.all.addColumn("")
        self.all.header().hide()

        from lilykde.parts import categories
        # reversed because QListView by default inserts new items at the top.
        for name, partTypes in reversed(categories):
            cat = QListViewItem(self.all, name)
            cat.setSelectable(False)
            cat.setOpen(True)
            for partType in reversed(partTypes):
                part = QListViewItem(cat, partType.name)
                part.partType = partType

        # score
        w = QVBox(p)
        QLabel('<b>%s</b>' % _("Score:"), w)
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
        Add the selected part types to the score (i.e.: instantiate them).
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
        """ Highlight item and show it's settings widget. """
        if item:
            item.part.select()

    def remove(self):
        """ Remove selected parts from the score. """
        for index in reversed(range(self.score.count())):
            if self.score.isSelected(index):
                self.score.item(index).part.delete()
                self.score.removeItem(index)

    def moveUp(self):
        """ Move selected parts up. """
        current = self.score.currentItem()
        for index in range(1, self.score.count()):
            if self.score.isSelected(index):
                item = self.score.item(index)
                self.score.takeItem(item)
                self.score.insertItem(item, index - 1)
                if index == current:
                    self.score.setCurrentItem(item)

    def moveDown(self):
        """ Move selected parts down. """
        current = self.score.currentItem()
        for index in reversed(range(self.score.count() - 1)):
            if self.score.isSelected(index):
                item = self.score.item(index)
                self.score.takeItem(item)
                self.score.insertItem(item, index + 1)
                if index == current:
                    self.score.setCurrentItem(item)

    def parts(self):
        """
        Get the ordered list of part objects (that are attached to the
        QListBoxText items.
        If there are more parts of the same class, their num attributes
        are set to 1, 2 instead of the default 0, so they don't produce
        conflicting LilyPond identifiers.
        """
        parts = [
            self.score.item(index).part for index in range(self.score.count())]
        part.numberDoubles(parts)
        return parts


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
            l.title() for l in sorted(keyNames)))
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

        self.midi = QCheckBox(_("Create MIDI output"), prefs)
        QToolTip.add(self.midi, _(
            "Create a MIDI file in addition to the PDF file."))

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
        return lang in keyNames and lang or None


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

    def printout(self):
        """
        Creates the score output using LilyDOM
        and writes it to the current document.
        """
        d = Document()
        d.typographicalQuotes = self.settings.typq.isChecked()

        # version:
        Version(d.body, unicode(self.settings.lyversion.currentText()))
        Newline(d.body)

        # language:
        lang = self.settings.getLanguage()
        if lang:
            d.language = lang
            Text(d.body, '\\include "%s.ly"\n' % lang)

        # header:
        h, head = Header(d), self.titles.read()
        for n in headerNames:
            if head[n]:
                h[n] = head[n]
        # Remove default LilyPond tagline?
        if self.settings.tagl.isChecked() and not h['tagline']:
            Comment(h, " %s" % _("Remove default LilyPond tagline"))
            h['tagline'] = Scheme(d, '#f')
        if len(h):
            d.body.append(h)
            Newline(d.body)

        parts = self.parts.parts()
        if parts:
            self.printoutParts(d, parts)

        # and finally print out:
        kate.view().insertText(unicode(d))

    def printoutParts(self, d, parts):
        """
        Write the parts to the LilyDOM document in d
        """
        # First write a global = {  } construct setting key and time sig
        g = Seq(Assignment(d.body, 'global'), multiline=True)
        # key signature
        note, alter = keys[self.settings.key.currentItem()]
        alter = Rational(alter, 2)
        mode = modes[self.settings.mode.currentItem()][0]
        KeySignature(g, note, alter, mode)
        # time signature
        if self.settings.time.currentItem() < 2:
            Text(g, r"\override Staff.TimeSignature #'style = #'()")
        num, beat = map(int, re.findall('\\d+',
            str(self.settings.time.currentText())))
        TimeSignature(g, num, beat)
        # partial
        if self.settings.pickup.currentItem() > 0:
            Text(g, r"\partial %s" %
                durations[self.settings.pickup.currentItem() - 1])
        Newline(d.body)

        # Now, on to the parts.
        # First we check the names of all the assignments. If there are some
        # with the same name, append their part name. Same for context ids.

        # Build all the parts:
        for p in parts:
            p.run(d)      # This build the LilyDOM parts for the part.

        # Now check if there are name collisions in identifiers:
        names = {}
        for p in parts:
            for i in p.assignments():
                names.setdefault(i, []).append(p)
        for name, plist in names.iteritems():
            if len(plist) > 1:
                # Name occurs more than one time.
                # Then append part name.
                for p in plist:
                    p.renameAssignment(name, name + p.identifier())
        # Same for collisions in named contexts:
        names = {}
        for p in parts:
            for i in p.namedContexts():
                names.setdefault(i, []).append(p)
        for name, plist in names.iteritems():
            if len(plist) > 1:
                # Named contexts occur more than once,
                # Rename them.
                for p in plist:
                    p.renameNamedContext(name, name + p.identifier())

        # Now build the full LilyDOM document.
        # Get all the assignments
        for p in parts:
            p.appendAssignments(d.body)
        Newline(d.body)

        # Main \score
        s = Score(d.body)
        Newline(d.body)
        s1 = Simr(s)
        for p in parts:
            p.appendParts(s1)

        Layout(s)
        if self.settings.midi.isChecked():
            Midi(s)

        # Aftermath
        for p in parts:
            p.aftermath()


    def done(self, result):
        """
        Close the dialog and create the score if Ok was clicked.
        """
        self.saveCompletions()
        if result == KDialogBase.Accepted:
            self.printout()
        KDialogBase.done(self, result)



# kate: indent-width 4;
