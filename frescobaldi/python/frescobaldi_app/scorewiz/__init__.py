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
Score Wizard
"""

import os, re, sip, sys, types
import ly, ly.dom
from fractions import Fraction

from PyQt4.QtCore import QSize, QSizeF, QUrl, Qt
from PyQt4.QtGui import (
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QSplitter, QStackedWidget, QTextBrowser,
    QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
from PyKDE4.kdecore import KGlobal, i18n, ki18n
from PyKDE4.kdeui import (
    KCompletion, KHBox, KIcon, KLineEdit, KPageDialog, KPushButton,
    KStandardGuiItem, KVBox)

from kateshell.app import cacheresult
from frescobaldi_app.mainapp import SymbolManager
from frescobaldi_app.widgets import TapButton
from frescobaldi_app.version import defaultVersion

def config(group=None):
    c = KGlobal.config().group("scorewiz")
    if group:
        c = c.group(group)
    return c


class ScoreWizard(KPageDialog):
    def __init__(self, mainwin):
        KPageDialog.__init__(self, mainwin)
        self.mainwin = mainwin
        self.setFaceType(KPageDialog.Tabbed)
        self.setButtons(KPageDialog.ButtonCode(
            KPageDialog.Try | KPageDialog.Help |
            KPageDialog.Ok | KPageDialog.Cancel | KPageDialog.Default))
        self.setButtonIcon(KPageDialog.Try, KIcon("run-lilypond"))
        self.enableButton(KPageDialog.Try, False)
        self.setCaption(i18n("Score Setup Wizard"))
        self.setHelp("scorewiz")
        self.completableWidgets = {}
        self.titles = Titles(self)
        self.parts = Parts(self)
        self.settings = Settings(self)
        self.loadCompletions()
        self.restoreDialogSize(config("dialogsize"))
        self.defaultClicked.connect(self.default)
        self.tryClicked.connect(self.previewScore)
    
    def default(self):
        self.titles.default()
        self.parts.default()
        self.settings.default()
    
    def previewScore(self):
        self.previewDialog().showPreview()
        
    @cacheresult
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
            c.setItems(conf.readEntry(name, []))

    def done(self, result):
        self.saveDialogSize(config("dialogsize"))
        self.saveCompletions()
        self.settings.saveConfig()
        if result:
            # indent the text again using the user (document) settings:
            text = self.builder().ly()
            text = self.mainwin.currentDocument().indent(text)
            self.mainwin.view().insertText(text)
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
        t.setOpenLinks(False)
        t.setOpenExternalLinks(False)

        # ensure that the full HTML example page is displayed
        t.setContentsMargins(2, 2, 2, 2)
        t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        t.setMinimumSize(QSize(350, 350))
        #t.document().documentLayout().documentSizeChanged.connect(
            #lambda size: t.setMinimumSize(size.toSize() + QSize(4, 4)))

        headers = ly.headers(i18n)
        msg = i18n("Click to enter a value.")
        t.setHtml(titles_html.format(
            copyrightmsg = i18n("bottom of first page"),
            taglinemsg = i18n("bottom of last page"),
            **dict((k, "<a title='{0}' href='{1}'>{2}</a>".format(msg, k, v))
                    for k, v in headers)))
        l.addWidget(t)
        t.anchorClicked.connect(lambda qurl:
            self.findChild(KLineEdit, qurl.toString()).setFocus())

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
            yield h, self.findChild(KLineEdit, h).text()


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
        QLabel('<b>{0}</b>'.format(i18n("Available parts:")), v)
        allParts = QTreeWidget(v)
        addButton = KPushButton(KStandardGuiItem.add(), v)
        addButton.setToolTip(i18n("Add selected part to your score."))

        # The listbox with selected parts
        v = KVBox()
        self.addWidget(v)
        QLabel('<b>{0}</b>'.format(i18n("Score:")), v)
        score = QListWidget(v)
        self.score = score  # so the partList method can find us
        h = KHBox(v)
        removeButton = KPushButton(KStandardGuiItem.remove(), h)
        upButton = QToolButton(h)
        upButton.setIcon(KIcon("go-up"))
        downButton = QToolButton(h)
        downButton.setIcon(KIcon("go-down"))

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
        score.setDragDropMode(QListWidget.InternalMove)

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
        
        @allParts.itemDoubleClicked.connect
        def addPart(item, col):
            if hasattr(item, "partClass"):
                PartItem(item.partClass)
        
        @allParts.itemClicked.connect
        def toggleExpand(item, col):
            item.setExpanded(not item.isExpanded())

        @addButton.clicked.connect
        def addSelectedParts():
            for item in allParts.selectedItems():
                PartItem(item.partClass)

        @removeButton.clicked.connect
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
            
        @upButton.clicked.connect
        @keepSel
        def moveUp():
            """ Move selected parts up. """
            for row in range(1, score.count()):
                if score.item(row).isSelected():
                    item = score.takeItem(row)
                    score.insertItem(row - 1, item)

        @downButton.clicked.connect
        @keepSel
        def moveDown():
            """ Move selected parts down. """
            for row in range(score.count() - 1, -1, -1):
                if score.item(row).isSelected():
                    item = score.takeItem(row)
                    score.insertItem(row + 1, item)

        @score.currentItemChanged.connect
        def showItem(cur, prev):
            if cur:
                cur.showSettingsWidget()

        from frescobaldi_app.scorewiz.parts import categories
        for name, parts in categories():
            group = QTreeWidgetItem(allParts, [name])
            group.setFlags(Qt.ItemIsEnabled)
            group.setIcon(0, KIcon("inode-directory"))
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


class Settings(SymbolManager, QWidget):
    """
    The widget where users can set other preferences.
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        SymbolManager.__init__(self)
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
        self.time.addItems([
            '(4/4)', '(2/2)',
            '2/4', '3/4', '4/4', '5/4', '6/4', '7/4',
            '2/2', '3/2', '4/2',
            '3/8', '5/8', '6/8', '7/8', '8/8', '9/8', '12/8',
            '3/16', '6/16', '12/16'])
        # palette sensitive icons for the first two items
        self.addItemSymbol(self.time, 0, 'time_c44')
        self.addItemSymbol(self.time, 1, 'time_c22')
        l.setBuddy(self.time)

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Pickup measure:"), h)
        self.pickup = QComboBox(h)
        self.pickup.addItem(i18n("None"))
        self.pickup.insertSeparator(1)
        durs = [('note_' + d.replace('.', 'd'), d) for d in durations]
        for icon, text in durs:
            self.addItemSymbol(self.pickup, self.pickup.count(), icon)
            self.pickup.addItem(text)
        l.setBuddy(self.pickup)

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Metronome mark:"), h)
        self.metroDur = QComboBox(h)

        l.setBuddy(self.metroDur)
        for icon, text in durs:
            self.addItemSymbol(self.metroDur, self.metroDur.count(), icon)
            self.metroDur.addItem('')
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
        l = QLabel(i18n("Pitch name language:"), h)
        self.languageNames = list(sorted(ly.keyNames))
        self.lylang = QComboBox(h)
        l.setBuddy(self.lylang)
        self.lylang.addItem(i18n("Default"))
        self.lylang.insertSeparator(1)
        self.lylang.addItems([l.title() for l in self.languageNames])
        h.setToolTip(i18n(
            "The LilyPond language you want to use for the pitch names."))
        self.lylang.currentIndexChanged.connect(self.slotLanguageChanged)
        self.slotLanguageChanged(0) # init with default
        
        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Version:"), h)
        self.lyversion = QComboBox(h)
        self.lyversion.setEditable(True)
        l.setBuddy(self.lyversion)
        version = defaultVersion()
        if version:
            self.lyversion.addItem(str(version))
        self.lyversion.addItems(('2.12.0', '2.10.0'))
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

        self.book = QCheckBox(i18n("Wrap score in \\book block"))
        self.book.setToolTip(i18n(
            "If checked, wraps the \\score block inside a \\book block."))
        v.addWidget(self.book)

        # paper size:
        h = KHBox()
        v.addWidget(h)
        h.setSpacing(2)
        l = QLabel(i18n("Paper size:"), h)
        self.paper = QComboBox(h)
        l.setBuddy(self.paper)
        self.paperLandscape = QCheckBox(i18n("Landscape"), h)
        self.paper.addItem(i18n("Default"))
        self.paper.addItems(ly.paperSizes)
        self.paper.activated.connect(lambda i: self.paperLandscape.setEnabled(bool(i)))

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
        self.instrLanguages = list(sorted(set(lang.split('/')[-3] for lang in langs)))
        self.instrLang.addItems(map(KGlobal.locale().languageCodeToName, self.instrLanguages))
        
        self.default()
        self.loadConfig()

    def saveConfig(self):
        conf = config()
        conf.writeEntry('language', self.getLanguage() or 'default')
        conf.writeEntry('typographical', self.typq.isChecked())
        conf.writeEntry('remove tagline', self.tagl.isChecked())
        conf.writeEntry('remove barnumbers', self.barnum.isChecked())
        conf.writeEntry('midi', self.midi.isChecked())
        conf.writeEntry('metronome mark', self.metro.isChecked())
        conf.writeEntry('wrap in book', self.book.isChecked())
        if self.paper.currentIndex() > 0:
            conf.writeEntry('paper size', ly.paperSizes[self.paper.currentIndex() - 1])
        conf.writeEntry('paper landscape', self.paperLandscape.isChecked())
        g = config('instrument names')
        g.writeEntry('show', self.instr.isChecked())
        g.writeEntry('first', ['long', 'short'][self.instrFirst.currentIndex()])
        g.writeEntry('other', ['long', 'short', 'none'][self.instrOther.currentIndex()])
        g.writeEntry('lang', (['default', 'english'] + self.instrLanguages)[self.instrLang.currentIndex()])

    def loadConfig(self):
        conf = config()
        self.setLanguage(conf.readEntry('language', 'default'))
        self.typq.setChecked(conf.readEntry('typographical', True))
        self.tagl.setChecked(conf.readEntry('remove tagline', False))
        self.barnum.setChecked(conf.readEntry('remove barnumbers', False))
        self.midi.setChecked(conf.readEntry('midi', True))
        self.metro.setChecked(conf.readEntry('metronome mark', False))
        self.book.setChecked(conf.readEntry('wrap in book', False))

        psize = conf.readEntry('paper size', "")
        if psize in ly.paperSizes:
            self.paper.setCurrentIndex(ly.paperSizes.index(psize) + 1)
        self.paperLandscape.setChecked(conf.readEntry('paper landscape', False))
        self.paperLandscape.setEnabled(psize in ly.paperSizes)

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
        self.instr.setChecked(g.readEntry('show', True))

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
        self.book.setChecked(False)
        self.paper.setCurrentIndex(0)
        self.paperLandscape.setEnabled(False)
        self.instrFirst.setCurrentIndex(0)
        self.instrOther.setCurrentIndex(2)
        self.instrLang.setCurrentIndex(0)
        self.instr.setChecked(True)

    def getLanguage(self):
        """ Return the configured LilyPond pitch language, '' for default. """
        if self.lylang.currentIndex() >= 2:
            return self.languageNames[self.lylang.currentIndex() - 2]
        else:
            return ''

    def setLanguage(self, lang):
        """ Sets the language combobox to the specified language """
        if lang not in self.languageNames:
            self.lylang.setCurrentIndex(0)
        else:
            self.lylang.setCurrentIndex(self.languageNames.index(lang) + 2)
    
    def slotLanguageChanged(self, index):
        """ Change the LilyPond language, affects key names """
        lang = index < 2 and "nederlands" or self.languageNames[index - 2]
        key = self.key.currentIndex()
        if key == -1:
            key = 0
        self.key.clear()
        self.key.addItems(ly.keyNames[lang])
        self.key.setCurrentIndex(key)


class Builder(object):
    """
    Builds a LilyPond document, based on the preferences from the ScoreWizard.
    The builder reads settings from the ScoreWizard, and is thus tightly
    integrated with the ScoreWizard.

    Interacts also with the parts. The parts (in parts.py) may only use a few
    functions, and should not interact with the Wizard directly!

    Parts may interact with:
    
    methods:
    include             to request filenames to be included
    
    addCodeBlock        to add arbitrary strings to the output (e.g. functions)

    getInstrumentNames  to translate instrument names

    setInstrumentNames  to translate and set instrument names for a node
    
    setMidiInstrument   to set the Midi instrument for a node
    
    getMidiTempo        to get the configured tempo e.g."(ly:make-moment 100 4)"
    
    setMidiTempo        to write the configured tempo in the given context
    
    properties:
    lilyPondVersion     a tuple like (2, 11, 64) describing the LilyPond the
                        document is built for.

    midi                property is True if MIDI output is requested
    
    book                True if the main \\score { } block is to be wrapped
                        inside a \\book { } block. A part may set this to True
                        if it is needed (e.g. when alternate output files are to
                        be created).
    
    """
    def __init__(self, wizard):
        self.wizard = wizard
        self.midi = wizard.settings.midi.isChecked()
        self.book = wizard.settings.book.isChecked()
        
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
            self.translate = i18n
        elif i >= 2:                    # other translation
            try:
                import gettext
                self.translate = gettext.GNUTranslations(open(
                  KGlobal.dirs().findResource("locale", s.instrLanguages[i-2] +
                    "/LC_MESSAGES/frescobaldi.mo"))).ugettext
            except IOError:
                pass
        
        # keep track of include files:
        self.includeFiles = []
        
        # keep track of arbitrary code blocks:
        self.codeBlocks = []
        
        # version:
        version = s.lyversion.currentText()
        ly.dom.Version(version, doc)
        ly.dom.BlankLine(doc)
        self.lilyPondVersion = tuple(map(int, re.findall('\\d+', version)))

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
            ly.dom.Scheme('(set-paper-size "{0}"{1})'.format(
                    s.paper.currentText(),
                    s.paperLandscape.isChecked() and " 'landscape" or ""),
                ly.dom.Paper(doc)).after = 1
            ly.dom.BlankLine(doc)

        # insert code blocks here later
        codeBlockOffset = len(doc)

        # get the part list
        parts = self.wizard.parts.partList()
        if parts:
            self.buildScore(doc, parts)
        
        # pitch language:
        language = s.getLanguage()
        if language:
            if self.lilyPondVersion >= (2, 13, 38):
                doc.insert(1, ly.dom.Line('\\language "{0}"'.format(language)))
            else:
                self.include("{0}.ly".format(language))

        # add code blocks, if any:
        for code in self.codeBlocks[::-1]:
            node = isinstance(code, basestring) and ly.dom.Line(code) or code()
            node.after = 2
            doc.insert(codeBlockOffset, node)
        
        # add the files that want to be included at the beginning
        if self.includeFiles:
            doc.insert(2, ly.dom.BlankLine())
            for fileName in reversed(self.includeFiles):
                doc.insert(2, ly.dom.Include(fileName))
                
        # Finally, return the document
        return doc

    def buildScore(self, doc, partList):
        """ Creates a LilyPond score based on parts in partList """
        s = self.wizard.settings

        # a global = {  } construct setting key and time sig, etc.
        globalAssignment = ly.dom.Assignment('global')
        g = ly.dom.Seq(globalAssignment)

        # First find out if we need to define a tempoMark section.
        tempoText = s.tempoInd.text()
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
                ly.dom.Line(r'\small \general-align #Y #DOWN \note #"{0}" #1 = {1}'.format(dur, val), m)
            else:
                # Constuct a tempo indication without metronome mark
                ly.dom.QuotedString(tempoText, m)
        elif metro:
            # No, but display a metronome value
            ly.dom.Tempo(dur, val, g).after = 1

        # Add the global section's assignment to the document:
        doc.append(globalAssignment)
        ly.dom.BlankLine(doc)

        # key signature
        note, alter = ly.keys[s.key.currentIndex()]
        alter = Fraction(alter, 2)
        mode = ly.modes()[s.mode.currentIndex()][0]
        ly.dom.KeySignature(note, alter, mode, g).after = 1
        # time signature
        match = re.search('(\\d+).*?(\\d+)', s.time.currentText())
        if match:
            if s.time.currentText() in ('2/2', '4/4'):
                if self.lilyPondVersion >= (2, 11, 44):
                    ly.dom.Line(r"\numericTimeSignature", g)
                else:
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
        score = ly.dom.Score()
        sim = ly.dom.Simr(score)
        
        # if there is more than one part, make separate assignments for each
        # part, so printing separate parts is easier
        if len(partList) > 1:
            for part in partList:
                ref = ly.dom.Reference(part.identifier() + "Part")
                p = ly.dom.Simr(ly.dom.Assignment(ref, doc))
                ly.dom.BlankLine(doc)
                ly.dom.Identifier(ref, sim).after = 1
                for n in part.nodes:
                    p.append(n)
        else:
            for part in partList:
                for n in part.nodes:
                    sim.append(n)

        # put the score in the document
        if self.book:
            book = ly.dom.Book()
            book.append(score)
            doc.append(book)
        else:
            doc.append(score)
        
        # Add some layout stuff
        lay = ly.dom.Layout(score)
        if s.barnum.isChecked():
            ly.dom.Line('\\remove "Bar_number_engraver"',
                ly.dom.Context('Score', lay))
        if self.midi:
            mid = ly.dom.Midi(score)
            if tempoText or not metro:
                self.setMidiTempo(ly.dom.Context('Score', mid))
        
        # Add possible aftermath:
        for part in partList:
            if part.aftermath:
                ly.dom.BlankLine(doc)
                for n in part.aftermath:
                    doc.append(n)

        # clean up the parts:
        for part in partList:
            part.cleanup()
        
    ##
    # The following methods are to be used by the parts.
    ##
    
    def include(self, fileName):
        """
        Request an \\include statement be placed at the beginning
        of the output document.
        """
        # We don't use a set, because we want to maintain the order.
        if fileName not in self.includeFiles:
            self.includeFiles.append(fileName)
    
    def addCodeBlock(self, code):
        """
        Adds an arbitary Node to the output file, containing e.g. Scheme
        functions.
        
        The argument is either a string, a function or an iterable (containing
        other strings, functions and/or iterables).
        
        Strings and functions are recursively added to a list (if not already
        present).  Strings are written directly to the output document, e.g. for
        added music functions or pieces of Ccheme code.  Functions are called on
        output time and should return one ly.dom.Node object that is inserted in
        the output document.
        """
        if not isinstance(code, (basestring, types.FunctionType)):
            for c in code:
                self.addCodeBlock(c)
        elif code not in self.codeBlocks:
            self.codeBlocks.append(code)

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
            first = names[s.instrFirst.currentIndex()]
            w['instrumentName'] = first
            if s.instrOther.currentIndex() < 2:
                other = names[s.instrOther.currentIndex()]
                # if these are markup objects, copy them otherwise the assignment
                # to shortInstrumentName takes it away from the instrumentName.
                if other is first and isinstance(first, ly.dom.Node):
                    other = other.copy()
                w['shortInstrumentName'] = other

    def setMidiInstrument(self, node, midiInstrument):
        """
        Sets the MIDI instrument for the node, if the user wants MIDI output.
        """
        if self.midi:
            node.getWith()['midiInstrument'] = midiInstrument
    
    def getMidiTempo(self):
        """
        Returns the configured tempo as a string e.g. "(ly:make-moment 100 4)"
        """
        s = self.wizard.settings
        base, mul = midiDurations[s.metroDur.currentIndex()]
        val = int(re.search(r"\d*", s.metroVal.currentText()).group() or "100") * mul
        return "(ly:make-moment {0} {1})".format(val, base)
        
    def setMidiTempo(self, node):
        """
        Writes the configured tempo to the 'tempoWholesPerMinute' variable
        of the given context (should be subclass of ly.dom.HandleVars).
        """
        node['tempoWholesPerMinute'] = ly.dom.Scheme(self.getMidiTempo())


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

    def cleanup(self):
        """
        Delete previously built assignments, nodes and aftermath
        """
        self.assignments = []
        self.nodes = []
        self.aftermath = []
        
    def run(self, builder):
        """
        This method is called by the score wizard to build our part.
        It initializes the nodes and assignments and calls the build
        method. You should not reimplement this method, but rather the
        build method.
        """
        self.cleanup()
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
        layout.addWidget(QLabel('({0})'.format(i18n("No settings available."))))

    def build(self, builder):
        """
        May add assignments and created nodes to respectively
        self.assignments and self.nodes.
        builder is a Builder instance providing access to users settings.
        You must implement this method in your part subclasses.
        
        You may also add ly.dom.Node objects to the self.aftermath list. These
        are reproduces below the main score and can be used to create additional
        score sections or markups, etc.
        """
        pass


titles_html = r"""<html><head><style type='text/css'>
body {{
  background-color: #fefefe;
  color: black;
}}
a {{
  text-decoration: none;
  color: black;
}}
</style></head>
<body><table width='100%' style='font-family:serif;'>
<tr><td colspan=3 align=center>{dedication}</td></tr>
<tr><td colspan=3 align=center style='font-size:20pt;'><b>{title}</b></td></tr>
<tr><td colspan=3 align=center style='font-size:12pt;'><b>{subtitle}</b></td></tr>
<tr><td colspan=3 align=center><b>{subsubtitle}</b></td></tr>
<tr>
    <td align=left width='25%'>{poet}</td>
    <td align=center><b>{instrument}</b></td>
    <td align=right width='25%'>{composer}</td>
</tr>
<tr>
    <td align=left>{meter}</td>
    <td> </td>
    <td align=right>{arranger}</td>
</tr>
<tr>
    <td align=left>{piece}</td>
    <td> </td>
    <td align=right>{opus}</td>
</tr>
<tr><td colspan=3 align=center><img src='pics:scorewiz.png'></td></tr>
<tr><td colspan=3 align=center>{copyright} <i>({copyrightmsg})</i></td></tr>
<tr><td colspan=3 align=center>{tagline} <i>({taglinemsg})</i></td></tr>
</table></body></html>
"""

durations = ['16', '16.', '8', '8.', '4', '4.', '2', '2.', '1', '1.']
midiDurations = ((16,1),(32,3),(8,1),(16,3),(4,1),(8,3),(2,1),(4,3),(1,1),(2,3))
partialDurations = ((4,0),(4,1),(3,0),(3,1),(2,0),(2,1),(1,0),(1,1),(0,0),(0,1))
