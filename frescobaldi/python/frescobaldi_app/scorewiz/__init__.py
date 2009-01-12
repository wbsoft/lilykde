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
Score Wizard
"""

import os, re, sip, string, sys
import ly, ly.dom, ly.version
from rational import Rational

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

from frescobaldi_app.widgets import TapButton
from frescobaldi_app.mainapp import lazy

def config(group=None):
    c = KGlobal.config().group("scorewiz")
    if group:
        c = c.group(group)
    return c

def onSignal(obj, signalName):
    """ decorator to easily add connect a Qt signal to a Python slot."""
    def decorator(func):
        QObject.connect(obj, SIGNAL(signalName), func)
        return func
    return decorator


class ScoreWizard(KPageDialog):
    def __init__(self, mainwin):
        KPageDialog.__init__(self, mainwin)
        self.mainwin = mainwin
        self.setFaceType(KPageDialog.Tabbed)
        self.setButtons(KPageDialog.ButtonCode(
            KPageDialog.Try |
            KPageDialog.Ok | KPageDialog.Cancel | KPageDialog.Default))
        self.setButtonIcon(KPageDialog.Try, KIcon("run-lilypond"))
        self.enableButton(KPageDialog.Try, False)
        self.setCaption(i18n("Score Setup Wizard"))
        self.completableWidgets = {}
        self.titles = Titles(self)
        self.parts = Parts(self)
        self.settings = Settings(self)
        self.loadCompletions()
        self.restoreDialogSize(config("dialogsize"))
        @onSignal(self, "defaultClicked()")
        def default():
            self.titles.default()
            self.parts.default()
            self.settings.default()
        @onSignal(self, "tryClicked()")
        def previewscore():
            self.previewDialog().showPreview()
        
    @lazy
    def previewDialog(self):
        from frescobaldi_app.scorewiz import preview
        return preview.PreviewDialog(self)
        
    def complete(self, widget, name=None):
        """ Save the completions of the specified widget """
        if not name:
            name = widget.objectName()
        self.completableWidgets[name] = widget

    def saveCompletions(self):
        """ Saves completion items for all lineedits. """
        conf = config("completions")
        for name, widget in self.completableWidgets.iteritems():
            items = widget.completionObject().items()
            text = widget.text()
            if len(text) > 1 and text not in items:
                items.append(text)
            conf.writeEntry(name, items)

    def loadCompletions(self):
        """ Loads the completion data from the config. """
        conf = config("completions")
        for name, widget in self.completableWidgets.iteritems():
            c = widget.completionObject()
            c.setOrder(KCompletion.Sorted)
            c.setItems(conf.readEntry(name, QStringList()))

    def done(self, result):
        self.saveDialogSize(config("dialogsize"))
        self.saveCompletions()
        self.settings.saveConfig()
        if result:
            self.mainwin.view().insertText(self.builder().ly())
        KPageDialog.done(self, result)

    def builder(self):
        """ Return a Builder that mimics our settings """
        return Builder(self)


class Titles(QWidget):
    """
    A widget where users can fill in all the titles that are put
    in the \header block.
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        p = parent.addPage(self, i18n("Titles and Headers"))

        l = QHBoxLayout(self)
        # The html view with the score layout example
        t = QTextBrowser(self)
        t.setSearchPaths(KGlobal.dirs().findDirs("appdata", "pics"))
        t.setOpenLinks(False)
        t.setOpenExternalLinks(False)

        # ensure that the full HTML example page is displayed
        t.setContentsMargins(2, 2, 2, 2)
        t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        @onSignal(t.document().documentLayout(), "documentSizeChanged(QSizeF)")
        def resize(size):
            t.setMinimumSize(size.toSize() + QSize(4, 4))

        headers = ly.headers(i18n)
        msg = i18n("Click to enter a value.")
        html = string.Template(titles_html % (
                i18n("bottom of first page"),
                i18n("bottom of last page"))
            ).substitute(dict(
                (k, "<a title='%s' href='%s'>%s</a>" % (msg, k, v))
                for k, v in headers))
        t.setHtml(html)
        l.addWidget(t)
        @onSignal(t, "anchorClicked(QUrl)")
        def focusEntry(qurl):
            self.findChild(KLineEdit, qurl.toString()).setFocus()

        g = QGridLayout()
        g.setVerticalSpacing(1)
        g.setColumnMinimumWidth(1, 200)
        l.addLayout(g)

        for row, (name, title) in enumerate(headers):
            l = QLabel(title + ":", self)
            e = KLineEdit(self)
            e.setObjectName(name)
            l.setBuddy(e)
            g.addWidget(l, row, 0)
            g.addWidget(e, row, 1)
            # set completion items
            parent.complete(e)


    def default(self):
        """ Clear the text entries. """
        for w in self.findChildren(KLineEdit):
            w.clear()

    def headers(self):
        """ Iterate over the user-entered headers (name, value) """
        for h in ly.headerNames:
            yield h, unicode(self.findChild(KLineEdit, h).text())


class Parts(QSplitter):
    """
    The widget where users can select parts and adjust their settings.
    """
    def __init__(self, parent):
        QSplitter.__init__(self, parent)
        parent.addPage(self, i18n("Parts"))

        # The part types overview widget.
        v = KVBox()
        self.addWidget(v)
        QLabel('<b>%s</b>' % i18n("Available parts:"), v)
        allParts = QTreeWidget(v)
        addButton = KPushButton(KStandardGuiItem.add(), v)
        addButton.setToolTip(i18n("Add selected part to your score."))

        # The listbox with selected parts
        v = KVBox()
        self.addWidget(v)
        QLabel('<b>%s</b>' % i18n("Score:"), v)
        score = QListWidget(v)
        self.score = score  # so the partList method can find us
        h = KHBox(v)
        removeButton = KPushButton(KStandardGuiItem.remove(), h)
        upButton = QToolButton(h)
        upButton.setIcon(KIcon("go-up"))        # TODO: check icon
        downButton = QToolButton(h)
        downButton.setIcon(KIcon("go-down"))    # TODO: check icon

        # The StackedWidget with settings
        partSettings = QStackedWidget()
        self.addWidget(partSettings)
        
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 1)
        self.setStretchFactor(2, 1)
        self.setSizes((100, 100, 100))

        allParts.setSelectionMode(QTreeWidget.ExtendedSelection)
        allParts.setRootIsDecorated(False)
        allParts.headerItem().setHidden(True)
        score.setSelectionMode(QListWidget.ExtendedSelection)

        class PartItem(QListWidgetItem):
            """
            A part from the score, instantiating a config widget as well.
            """
            def __init__(self, partClass):
                name = partClass.name() # partClass.name is a ki18n object
                QListWidgetItem.__init__(self, name, score)
                self.w = QGroupBox(name)
                partSettings.addWidget(self.w)
                self.part = partClass()
                layout = QVBoxLayout(self.w)
                self.part.widgets(layout)
                layout.addStretch(1)
                if score.count() == 1:
                    score.setCurrentRow(0)
                    self.setSelected(True)
                parent.enableButton(KPageDialog.Try, True)

            def showSettingsWidget(self):
                partSettings.setCurrentWidget(self.w)

            def remove(self):
                if score.count() == 1:
                    parent.enableButton(KPageDialog.Try, False)
                sip.delete(self.w)
                sip.delete(self) # TODO: check if necessary

        @onSignal(allParts, "itemDoubleClicked(QTreeWidgetItem*, int)")
        def addPart(item, col):
            if hasattr(item, "partClass"):
                PartItem(item.partClass)

        @onSignal(allParts, "itemClicked(QTreeWidgetItem*, int)")
        def toggleExpand(item, col):
            item.setExpanded(not item.isExpanded())

        @onSignal(addButton, "clicked()")
        def addSelectedParts():
            for item in allParts.selectedItems():
                PartItem(item.partClass)

        @onSignal(removeButton, "clicked()")
        def removeSelectedParts():
            for item in score.selectedItems():
                item.remove()

        def keepSel(func):
            """
            Restore the selection and current element after reordering parts.
            """
            def decorator():
                selItems = score.selectedItems()
                curItem = score.currentItem()
                func()
                score.setCurrentItem(curItem)
                for i in selItems:
                    i.setSelected(True)
            return decorator
            
        @onSignal(upButton, "clicked()")
        @keepSel
        def moveUp():
            """ Move selected parts up. """
            for row in range(1, score.count()):
                if score.item(row).isSelected():
                    item = score.takeItem(row)
                    score.insertItem(row - 1, item)

        @onSignal(downButton, "clicked()")
        @keepSel
        def moveDown():
            """ Move selected parts down. """
            for row in range(score.count() - 1, -1, -1):
                if score.item(row).isSelected():
                    item = score.takeItem(row)
                    score.insertItem(row + 1, item)

        @onSignal(score, "currentItemChanged(QListWidgetItem*, QListWidgetItem*)")
        def showItem(cur, prev):
            if cur:
                cur.showSettingsWidget()

        from frescobaldi_app.scorewiz.parts import categories
        for name, parts in categories():
            group = QTreeWidgetItem(allParts, [name])
            group.setFlags(Qt.ItemIsEnabled)
            #group.setExpanded(True)
            for part in parts:
                p = QTreeWidgetItem(group, [part.name()])
                p.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                p.partClass = part

    def default(self):
        """ Clear the score """
        while self.score.count():
            self.score.item(0).remove()

    def partList(self):
        """ Return user-configured part objects """
        return [self.score.item(row).part for row in range(self.score.count())]


class Settings(QWidget):
    """
    The widget where users can set other preferences.
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        parent.addPage(self, i18n("Score settings"))

        h = QHBoxLayout(self)
        v = QVBoxLayout()
        h.addLayout(v)
        score = QGroupBox(i18n("Score settings"))
        v.addWidget(score)
        lily =  QGroupBox(i18n("LilyPond"))
        v.addWidget(lily)

        v = QVBoxLayout()
        h.addLayout(v)
        prefs = QGroupBox(i18n("General preferences"))
        v.addWidget(prefs)
        instr = QGroupBox(i18n("Instrument names"))
        v.addWidget(instr)

        # Score settings:
        v = QVBoxLayout(score)
        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Key signature:"), h)
        self.key = QComboBox(h) # the key names are filled in later
        self.mode = QComboBox(h)
        self.mode.addItems([title for name, title in ly.modes(i18n)])
        l.setBuddy(self.key)

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Time signature:"), h)
        self.time = QComboBox(h)
        self.time.setEditable(True)
        self.time.addItem(KIcon('time_c44'), '(4/4)')
        self.time.addItem(KIcon('time_c22'), '(2/2)')
        self.time.addItems([
            '2/4', '3/4', '4/4', '5/4', '6/4', '7/4',
            '2/2', '3/2', '4/2',
            '3/8', '5/8', '6/8', '7/8', '8/8', '9/8', '12/8',
            '3/16', '6/16', '12/16'])
        l.setBuddy(self.time)

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Pickup measure:"), h)
        self.pickup = QComboBox(h)
        self.pickup.addItem(i18n("None"))
        self.pickup.insertSeparator(1)
        durs = [(KIcon('note_%s' % d.replace('.', 'd')), d) for d in durations]
        for icon, text in durs:
            self.pickup.addItem(icon, text)
        l.setBuddy(self.pickup)

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Metronome mark:"), h)
        self.metroDur = QComboBox(h)

        l.setBuddy(self.metroDur)
        for icon, text in durs:
            self.metroDur.addItem(icon, '')
        l = QLabel('=', h)
        l.setAlignment(Qt.AlignCenter)
        l.setMaximumWidth(20)
        self.metroVal = QComboBox(h)
        self.metroVal.setEditable(True)
        metroValues, start = [], 40
        for end, step in (60, 2), (72, 3), (120, 4), (144, 6), (210, 8):
            metroValues.extend(range(start, end, step))
            start = end
        # reverse so mousewheeling is more intuitive
        self.metroValues = metroValues[::-1]
        self.metroVal.addItems(map(str, self.metroValues))
        def tap(bpm):
            """ Tap the tempo tap button """
            l = [abs(t - bpm) for t in self.metroValues]
            m = min(l)
            if m < 6:
                self.metroVal.setCurrentIndex(l.index(m))
        TapButton(h, tap)

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Tempo indication:"), h)
        self.tempoInd = KLineEdit(h)
        parent.complete(self.tempoInd, "tempo")
        l.setBuddy(self.tempoInd)
        h.setToolTip(i18n("A tempo indication, e.g. \"Allegro.\""))

        # LilyPond settings
        v = QVBoxLayout(lily)
        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Language:"), h)
        self.languageNames = list(sorted(ly.keyNames))
        self.lylang = QComboBox(h)
        l.setBuddy(self.lylang)
        self.lylang.addItem(i18n("Default"))
        self.lylang.insertSeparator(1)
        self.lylang.addItems([l.title() for l in self.languageNames])
        h.setToolTip(i18n(
            "The LilyPond language you want to use for the pitch names."))
        @onSignal(self.lylang, "currentIndexChanged(const QString&)")
        def slotLanguageChanged(lang):
            """ Change the LilyPond language, affects key names """
            lang = unicode(lang).lower()    # can be QString
            if lang not in self.languageNames:
                lang = 'nederlands'
            index = self.key.currentIndex()
            if index == -1:
                index = 0
            self.key.clear()
            self.key.addItems(ly.keyNames[lang])
            self.key.setCurrentIndex(index)
        slotLanguageChanged('') # init with default

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Version:"), h)
        self.lyversion = QComboBox(h)
        self.lyversion.setEditable(True)
        l.setBuddy(self.lyversion)
        version = ly.version.LilyPondVersion('lilypond').versionString
        if version:
            self.lyversion.addItem(version)
        self.lyversion.addItems(('2.10.0', '2.11.0'))
        h.setToolTip(i18n(
            "The LilyPond version you will be using for this document."))

        # General preferences
        v = QVBoxLayout(prefs)
        self.typq = QCheckBox(i18n("Use typographical quotes"))
        self.typq.setToolTip(i18n(
            "Replace normal quotes in titles with nice typographical quotes."))
        v.addWidget(self.typq)
        self.tagl = QCheckBox(i18n("Remove default tagline"))
        self.tagl.setToolTip(i18n(
            "Suppress the default tagline output by LilyPond."))
        v.addWidget(self.tagl)
        self.barnum = QCheckBox(i18n("Remove bar numbers"))
        self.barnum.setToolTip(i18n(
            "Suppress the display of measure numbers at the beginning of "
            "every system."))
        v.addWidget(self.barnum)
        self.midi = QCheckBox(i18n("Create MIDI output"))
        self.midi.setToolTip(i18n(
            "Create a MIDI file in addition to the PDF file."))
        v.addWidget(self.midi)
        self.metro = QCheckBox(i18n("Show metronome mark"))
        self.metro.setToolTip(i18n(
            "If checked, show the metronome mark at the beginning of the "
            "score. The MIDI output also uses the metronome setting."))
        v.addWidget(self.metro)

        # paper size:
        h = KHBox()
        v.addWidget(h)
        h.setSpacing(2)
        l = QLabel(i18n("Paper size:"), h)
        self.paper = QComboBox(h)
        l.setBuddy(self.paper)
        self.paperLandscape = QCheckBox(i18n("Landscape"), h)
        self.paper.addItem(i18n("Default"))
        self.paper.addItems(paperSizes)
        @onSignal(self.paper, "activated(int)")
        def checkLandscape(i):
            self.paperLandscape.setEnabled(bool(i))

        # Instrument names
        instr.setCheckable(True)
        self.instr = instr
        v = QVBoxLayout(instr)

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("First system:"), h)
        self.instrFirst = QComboBox(h)
        l.setBuddy(self.instrFirst)
        self.instrFirst.addItems((i18n("Long"), i18n("Short")))
        h.setToolTip(i18n(
            "Use long or short instrument names before the first system."))

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Other systems:"), h)
        self.instrOther = QComboBox(h)
        l.setBuddy(self.instrOther)
        self.instrOther.addItems((i18n("Long"), i18n("Short"), i18n("None")))
        h.setToolTip(i18n(
            "Use short, long or no instrument names before the next systems."))

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Language:"), h)
        self.instrLang = QComboBox(h)
        l.setBuddy(self.instrLang)
        self.instrLang.addItems((i18n("Default"), KGlobal.locale().languageCodeToName("en")))
        h.setToolTip(i18n("Which language to use for the instrument names."))

        langs = KGlobal.dirs().findAllResources("locale", "*/LC_MESSAGES/frescobaldi.mo")
        self.instrLanguages = list(sorted(unicode(lang).split('/')[-3] for lang in langs))
        self.instrLang.addItems([KGlobal.locale().languageCodeToName(lang)
                for lang in self.instrLanguages])
        
        self.default()
        self.loadConfig()

    def saveConfig(self):
        conf = config()
        conf.writeEntry('language', self.getLanguage() or 'default')
        conf.writeEntry('typographical', QVariant(self.typq.isChecked()))
        conf.writeEntry('remove tagline', QVariant(self.tagl.isChecked()))
        conf.writeEntry('remove barnumbers', QVariant(self.barnum.isChecked()))
        conf.writeEntry('midi', QVariant(self.midi.isChecked()))
        conf.writeEntry('metronome mark', QVariant(self.metro.isChecked()))
        if self.paper.currentIndex() > 0:
            conf.writeEntry('paper size', paperSizes[self.paper.currentIndex() - 1])
        conf.writeEntry('paper landscape', QVariant(self.paperLandscape.isChecked()))
        g = config('instrument names')
        g.writeEntry('show', QVariant(self.instr.isChecked()))
        g.writeEntry('first', ['long', 'short'][self.instrFirst.currentIndex()])
        g.writeEntry('other', ['long', 'short', 'none'][self.instrOther.currentIndex()])
        g.writeEntry('lang', (['default', 'english'] + self.instrLanguages)[self.instrLang.currentIndex()])

    def loadConfig(self):
        conf = config()
        self.setLanguage(conf.readEntry('language', 'default'))
        self.typq.setChecked(conf.readEntry('typographical', QVariant(True)).toBool())
        self.tagl.setChecked(conf.readEntry('remove tagline', QVariant(False)).toBool())
        self.barnum.setChecked(conf.readEntry('remove barnumbers', QVariant(False)).toBool())
        self.midi.setChecked(conf.readEntry('midi', QVariant(True)).toBool())
        self.metro.setChecked(conf.readEntry('metronome mark', QVariant(False)).toBool())

        psize = conf.readEntry('paper size', '')
        if psize in paperSizes:
            self.paper.setCurrentIndex(paperSizes.index(psize) + 1)
        self.paperLandscape.setChecked(conf.readEntry('paper landscape', QVariant(False)).toBool())
        self.paperLandscape.setEnabled(psize in paperSizes)

        g = config('instrument names')
        def readconf(entry, itemlist, defaultIndex):
            item = g.readEntry(entry, itemlist[defaultIndex])
            if item in itemlist:
                return itemlist.index(item)
            else:
                return defaultIndex

        first = readconf('first', ['long', 'short'], 0)
        other = readconf('other', ['long', 'short', 'none'], 2)
        lang = readconf('lang', ['default', 'english'] + self.instrLanguages, 0)

        self.instrFirst.setCurrentIndex(first)
        self.instrOther.setCurrentIndex(other)
        self.instrLang.setCurrentIndex(lang)
        self.instr.setChecked(g.readEntry('show', QVariant(True)).toBool())

    def default(self):
        """ Set various items to their default state """
        self.lylang.setCurrentIndex(0)
        self.key.setCurrentIndex(0)
        self.mode.setCurrentIndex(0)
        self.time.setCurrentIndex(0)
        self.pickup.setCurrentIndex(0)
        self.metroVal.setCurrentIndex(self.metroValues.index(100))
        self.metroDur.setCurrentIndex(durations.index('4'))
        self.tempoInd.clear()
        self.typq.setChecked(True)
        self.tagl.setChecked(False)
        self.barnum.setChecked(False)
        self.midi.setChecked(True)
        self.metro.setChecked(False)
        self.paper.setCurrentIndex(0)
        self.paperLandscape.setEnabled(False)
        self.instrFirst.setCurrentIndex(0)
        self.instrOther.setCurrentIndex(2)
        self.instrLang.setCurrentIndex(0)
        self.instr.setChecked(True)

    def getLanguage(self):
        """ Return the configured LilyPond pitch language, '' for default. """
        if self.lylang.currentIndex():
            return self.languageNames[self.lylang.currentIndex() - 2]
        else:
            return ''

    def setLanguage(self, lang):
        """ Sets the language combobox to the specified language """
        if lang not in self.languageNames:
            self.lylang.setCurrentIndex(0)
        else:
            self.lylang.setCurrentIndex(self.languageNames.index(lang) + 2)


class Builder(object):
    """
    Builds a LilyPond document, based on the preferences from the ScoreWizard.
    The builder reads settings from the ScoreWizard, and is thus tightly
    integrated with the ScoreWizard.

    Interacts also with the parts. The parts (in parts.py) may only use a few
    functions, and should not interact with the Wizard directly!

    Parts may interact with:

    lilypondVersion     a tuple like (2, 11, 64) describing the LilyPond the
                        document is built for.

    getInstrumentNames  to translate instrument names

    setInstrumentNames  to translate and set instrument names for a node

    setMidiInstrument   to set the Midi instrument for a node
    """
    def __init__(self, wizard):
        self.wizard = wizard
        self.midi = wizard.settings.midi.isChecked()
        
    def ly(self, doc=None):
        """ Return LilyPond formatted output. """
        return self.printer().indent(doc or self.document())
        
    def printer(self):
        """ printer, that converts the ly.dom structure to LilyPond text. """
        p = ly.dom.Printer()
        p.indentString = "  " # FIXME get indent-width somehow...
        p.typographicalQuotes = self.wizard.settings.typq.isChecked()
        language = self.wizard.settings.getLanguage()
        if language:
            p.language = language
        return p
        
    def document(self):
        """ Get the document as a ly.dom tree structure """
        s = self.wizard.settings # easily access the settings tab.

        doc = ly.dom.Document()

        # instrument names language:
        self.translate = lambda s: s    # english (untranslated)
        i = s.instrLang.currentIndex()
        if i == 0:                      # default (translated)
            self.translate = lambda s: unicode(i18n(s))
        elif i >= 2:                    # other translation
            try:
                import gettext
                self.translate = gettext.GNUTranslations(open(unicode(
                  KGlobal.dirs().findResource("locale", s.instrLanguages[i-2] +
                    "/LC_MESSAGES/frescobaldi.mo")))).ugettext
            except IOError:
                pass
            
        # version:
        version = unicode(s.lyversion.currentText())
        ly.dom.Version(version, doc)
        ly.dom.BlankLine(doc)
        self.lilypondVersion = tuple(map(int, re.findall('\\d+', version)))

        # pitch language:
        language = s.getLanguage()
        if language:
            ly.dom.Text('\\include "%s.ly"' % language, doc)
            ly.dom.BlankLine(doc)

        # header:
        h = ly.dom.Header()
        for name, value in self.wizard.titles.headers():
            if value:
                h[name] = value
        if 'tagline' not in h and s.tagl.isChecked():
            ly.dom.Comment(i18n("Remove default LilyPond tagline"), h)
            h['tagline'] = ly.dom.Scheme('#f')
        if len(h):
            doc.append(h)
            ly.dom.BlankLine(doc)

        # paper size:
        if s.paper.currentIndex():
            ly.dom.Scheme('(set-paper-size "%s"%s)' % (
                    s.paper.currentText(),
                    s.paperLandscape.isChecked() and " 'landscape" or ""),
                ly.dom.Paper(doc)).after = 1
            ly.dom.BlankLine(doc)

        # get the part list
        parts = self.wizard.parts.partList()
        if parts:
            self.buildScore(doc, parts)

        # Finally, return the document
        return doc

    def buildScore(self, doc, partList):
        """ Creates a LilyPond score based on parts in partList """
        s = self.wizard.settings

        # a global = {  } construct setting key and time sig, etc.
        g = ly.dom.Seq(ly.dom.Assignment('global'))

        # First find out if we need to define a tempoMark section.
        tempoText = unicode(s.tempoInd.text())
        metro = s.metro.isChecked()
        dur = durations[s.metroDur.currentIndex()]
        val = s.metroVal.currentText()
        if tempoText:
            # Yes.
            tm = ly.dom.Enclosed(ly.dom.Assignment('tempoMark', doc))
            ly.dom.BlankLine(doc)
            ly.dom.Line('\\tempoMark', g)
            ly.dom.Line(
                "\\once \\override Score.RehearsalMark "
                "#'self-alignment-X = #LEFT", tm)
            if self.lilypondVersion > (2, 11, 0):
                ly.dom.Line(
                    "\\once \\override Score.RehearsalMark "
                    "#'break-align-symbols = #'(time-signature key-signature)", tm)
                ly.dom.Line(
                    "\\once \\override Staff.TimeSignature "
                    "#'break-align-anchor-alignment = #LEFT", tm)
            # Should we also display the metronome mark?
            m = ly.dom.MarkupEnclosed('bold', ly.dom.Markup(ly.dom.Mark(tm)))
            if metro:
                # Constuct a tempo indication with metronome mark
                ly.dom.QuotedString(tempoText + " ", m)
                ly.dom.Line(r'\small \general-align #Y #DOWN \note #"%s" #1 = %s' %
                    (dur, val), m)
            else:
                # Constuct a tempo indication without metronome mark
                ly.dom.QuotedString(tempoText, m)
        elif metro:
            # No, but display a metronome value
            ly.dom.Tempo(dur, val, g).after = 1

        # Add the global section's assignment to the document:
        doc.append(g.parent())
        ly.dom.BlankLine(doc)

        # key signature
        note, alter = ly.keys[s.key.currentIndex()]
        alter = Rational(alter, 2)
        mode = ly.modes()[s.mode.currentIndex()][0]
        ly.dom.KeySignature(note, alter, mode, g).after = 1
        # time signature
        match = re.search('(\\d+).*?(\\d+)', unicode(s.time.currentText()))
        if match:
            if s.time.currentText() in ('2/2', '4/4'):
                ly.dom.Line(r"\override Staff.TimeSignature #'style = #'()", g)
            num, beat = map(int, match.group(1, 2))
            ly.dom.TimeSignature(num, beat, g).after = 1
        # partial
        if s.pickup.currentIndex() > 1:
            dur, dots = partialDurations[s.pickup.currentIndex() - 2]
            ly.dom.Partial(dur, dots, parent=g)

        # Now on to the parts!
        # number instances of the same type (Choir I and Choir II, etc.)
        types = {}
        for part in partList:
            types.setdefault(part.__class__, []).append(part)
        for t in types.values():
            if len(t) > 1:
                for num, part in enumerate(t):
                    part.num = num + 1
            else:
                t[0].num = 0

        # let each part build the LilyPond output
        for part in partList:
            part.run(self)

        # check for name collisions in assignment identifiers
        refs = {}
        for part in partList:
            for a in part.assignments:
                ref = a.name
                name = ref.name
                refs.setdefault(name, []).append((ref, part))
        for reflist in refs.values():
            if len(reflist) > 1:
                for ref, part in reflist:
                    ref.name += part.identifier(lowerFirst=False)

        # collect all assignments
        for part in partList:
            for a in part.assignments:
                doc.append(a)
                ly.dom.BlankLine(doc)

        # create a \score and add all nodes:
        score = ly.dom.Score(doc)
        sim = ly.dom.Simr(score)
        for part in partList:
            for n in part.nodes:
                sim.append(n)

        lay = ly.dom.Layout(score)
        if s.barnum.isChecked():
            ly.dom.Line('\\remove "Bar_number_engraver"',
                ly.dom.Context('Score', lay))
        if self.midi:
            mid = ly.dom.Midi(score)
            if tempoText or not metro:
                base, mul = midiDurations[s.metroDur.currentIndex()]
                val = int(val) * mul
                ly.dom.Context('Score', mid)['tempoWholesPerMinute'] = \
                    ly.dom.Scheme("(ly:make-moment %s %s)" % (val, base))

    ##
    # The following methods are to be used by the parts.
    ##

    def getInstrumentNames(self, names, num=0):
        """
        Returns a tuple (longname, shortname).

        names is a ki18n string with a pipe symbol separating the
        long and the short instrument name. (This way the abbreviated
        instrument names remain translatable).

        If num > 0, it is added to the instrument name (e.g. Violine II)
        """
        names = self.translate(names).split("|")
        if num:
            names = [name + " " + ly.romanize(num) for name in names]
        return names

    def setInstrumentNames(self, node, names, num=0):
        """
        Add instrument names to the given node, which should be of
        ly.dom.ContextType.

        For instrumentNames and num, see getInstrumentNames.
        (instrumentNames may also be a tuple of ly.dom.LyNode objects.)
        """
        s = self.wizard.settings
        if s.instr.isChecked():
            if not isinstance(names, (tuple, list)):
                names = self.getInstrumentNames(names, num)
            ly.dom.addInstrumentNameEngraverIfNecessary(node)
            w = node.getWith()
            w['instrumentName'] = names[s.instrFirst.currentIndex()]
            if s.instrOther.currentIndex() < 2:
                w['shortInstrumentName'] = names[s.instrOther.currentIndex()]

    def setMidiInstrument(self, node, midiInstrument):
        """
        Sets the MIDI instrument for the node, if the user wants MIDI output.
        """
        if self.midi:
            node.getWith()['midiInstrument'] = midiInstrument


class PartBase(object):
    """
    Abstract base class for parts in the Parts widget.
    Classes provide basic information.
    Instances provide a settings widget and can create LilyPond output.
    """

    # The name of our part type in the dialog, mark for translation using ki18n!
    _name = "unnamed"
    
    def __init__(self):
        self.num = 0

    def run(self, builder):
        """
        This method is called by the score wizard to build our part.
        It initializes the nodes and assignments and calls the build
        method. You should not reimplement this method, but rather the
        build method.
        """
        self.assignments = []
        self.nodes = []
        self.build(builder)
        
    @classmethod
    def name(cls):
        """
        Return the translated part name.
        You should not override this method, but set the part name as an ki18n
        object in the _name class attribute.
        """
        return cls._name.toString()

    def identifier(self, lowerFirst=True):
        """
        Returns an untranslated name, usable as LilyPond identifier,
        with the first letter lowered by default.
        """
        name = self.__class__.__name__
        if lowerFirst:
            name = name[0].lower() + name[1:]
        if self.num:
            name += ly.romanize(self.num)
        return name

    def widgets(self, layout):
        """
        Reimplement this method to add widgets with settings
        to the given layout.
        """
        layout.addWidget(QLabel('(%s)' % i18n("No settings available.")))

    def build(self, builder):
        """
        May add assignments and created nodes to respectively
        self.assignments and self.nodes.
        builder is a Builder instance providing access to users settings.
        You must implement this method in your part subclasses.
        """
        pass


titles_html = r"""
<html><head><style type='text/css'>
a { text-decoration: none;}
</style></head>
<body><table width='100%%' style='font-family:serif;'>
<tr><td colspan=3 align=center>$dedication</td></tr>
<tr><td colspan=3 align=center style='font-size:20pt;'><b>$title</b></td></tr>
<tr><td colspan=3 align=center style='font-size:12pt;'><b>$subtitle</b></td></tr>
<tr><td colspan=3 align=center><b>$subsubtitle</b></td></tr>
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
</table></body></html>"""

durations = ['16', '16.', '8', '8.', '4', '4.', '2', '2.', '1', '1.']
midiDurations = ((16,1),(32,3),(8,1),(16,3),(4,1),(8,3),(2,1),(4,3),(1,1),(2,3))
partialDurations = ((4,0),(4,1),(3,0),(3,1),(2,0),(2,1),(1,0),(1,1),(0,0),(0,1))

paperSizes = ['a3', 'a4', 'a5', 'a6', 'a7', 'legal', 'letter', '11x17']
