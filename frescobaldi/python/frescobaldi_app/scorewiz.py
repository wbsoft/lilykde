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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

from frescobaldi_app.widgets import TapButton


def config(group=None):
    c = KGlobal.config().group("scorewiz")
    if group:
        c = c.group(group)
    return c




class ScoreWizard(KPageDialog):
    
    def __init__(self, parent):
        KPageDialog.__init__(self, parent)
        self.setFaceType(KPageDialog.Tabbed)
        self.setButtons(KPageDialog.ButtonCode(
            KPageDialog.Ok | KPageDialog.Cancel | KPageDialog.Default))
        self.setCaption(i18n("Score Setup Wizard"))
        self.completableWidgets = {}
        self.titles = Titles(self)
        self.parts = Parts(self)
        self.settings = Settings(self)
        self.loadCompletions()
        self.restoreDialogSize(config("dialogsize"))
        QObject.connect(self, SIGNAL("defaultClicked()"), self.slotDefault)
        
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
            Builder(self, self.parent())
        KPageDialog.done(self, result)
        
    def slotDefault(self):
        self.titles.default()
        self.parts.default()
        self.settings.default()
        
        
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
        QObject.connect(t.document().documentLayout(),
            SIGNAL("documentSizeChanged(QSizeF)"), 
            lambda size: t.setMinimumSize(size.toSize()+QSize(4, 4)))

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
        QObject.connect(t, SIGNAL("anchorClicked(QUrl)"), self.focusEntry)

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

    def focusEntry(self, qurl):
        self.findChild(KLineEdit, qurl.toString()).setFocus()
        
    def default(self):
        """ Set various items to their default state """
        for w in self.findChildren(KLineEdit):
            w.clear()
        
    def headers(self):
        """ Return the user-entered headers. """
        for h in ly.headerNames:
            yield h, unicode(self.findChild(KLineEdit, h).text())
            
    
class Parts(QSplitter):
    """
    The widget where users can select parts and adjust their settings.
    """
    def __init__(self, parent):
        QSplitter.__init__(self, parent)
        p = parent.addPage(self, i18n("Parts"))


    def default(self):
        """ Set various items to their default state """
        pass
    

class Settings(QWidget):
    """
    The widget where users can set other preferences.
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        p = parent.addPage(self, i18n("Score settings"))

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
        QObject.connect(self.lylang,
            SIGNAL("currentIndexChanged(const QString&)"), self.slotSetLanguage)
        self.slotSetLanguage('') # init with default
        
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
        QObject.connect(self.paper, SIGNAL("activated(int)"),
            lambda i: self.paperLandscape.setEnabled(bool(i)))

        # Instrument names
        instr.setCheckable(True)
        self.instr = instr
        v = QVBoxLayout(instr)
        
        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("First system:"), h)
        self.instrFirst = QComboBox(h)
        l.setBuddy(self.instrFirst)
        self.instrFirst.addItems((i18n("Short"), i18n("Long")))
        h.setToolTip(i18n(
            "Use long or short instrument names before the first system."))

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Other systems:"), h)
        self.instrOther = QComboBox(h)
        l.setBuddy(self.instrOther)
        self.instrOther.addItems((i18n("Short"), i18n("Long"), i18n("None")))
        h.setToolTip(i18n(
            "Use short, long or no instrument names before the next systems."))

        h = KHBox()
        v.addWidget(h)
        l = QLabel(i18n("Language:"), h)
        self.instrLang = QComboBox(h)
        l.setBuddy(self.instrLang)
        self.instrLang.addItems((i18n("Italian"), i18n("English"), i18n("Your language")))
        h.setToolTip(i18n(
            "Whether you want instrument names to be standard Italian "
            "(like 'Organo' for 'Organ'), English or in your own language."))

        self.default()
        self.loadConfig()

    def saveConfig(self):
        conf = config()
        if self.lylang.currentIndex() > 0:
            conf.writeEntry('language', self.languageNames[self.lylang.currentIndex() - 1])
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
        g.writeEntry('first', ['short', 'long'][self.instrFirst.currentIndex()])
        g.writeEntry('other', ['short', 'long', 'none'][self.instrOther.currentIndex()])
        g.writeEntry('lang', ['italian', 'english', 'translated'][self.instrLang.currentIndex()])
        
    def loadConfig(self):
        conf = config()
        lylang = conf.readEntry('language', '')
        if lylang in self.languageNames:
            index = self.languageNames.index(lylang) + 1
        else:
            index = 0
        self.lylang.setCurrentIndex(index)

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

        first = readconf('first', ['short', 'long'], 0)
        other = readconf('other', ['short', 'long', 'none'], 2)
        lang = readconf('lang', ['italian', 'english', 'translated'], 0)

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
        
    def slotSetLanguage(self, lang):
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
        


class Builder(ly.dom.Receiver):
    """
    Interacts with the parts and builds the LilyPond document,
    based on the user's preferences.
    
    wizard should be a ScoreWizard instance, from which all settings are read.
    """
    def __init__(self, wizard, mainwin):
        super(Builder, self).__init__()

        s = wizard.settings # the settings tab.
        t = wizard.titles   # the titles tab
        
        doc = ly.dom.Document()
        ly.dom.Version(unicode(s.lyversion.currentText()), doc)
        ly.dom.BlankLine(doc)
        
        # header:
        h = ly.dom.Header()
        for name, value in t.headers():
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
    
        
        # Create MIDI output?
        self.createMidiOutput = s.midi.isChecked()

        # Output instrument names?
        self.instrumentNames = s.instr.isChecked()
        # 0 = italian, 1 = english, 2 = translated
        self.instrumentNamesLanguage = s.instrLang.currentIndex()
        # 0 = long, 1 = short
        self.instrumentNamesFirst = s.instrFirst.currentIndex()
        # 0 = long, 1 = short, 2 = none
        self.instrumentNamesOther = s.instrOther.currentIndex()
        
    
        # Finally, print out
        mainwin.view().insertText(self.indent(doc))
        
        
    
    def setInstrumentNames(self, node, instrumentNames):
        if not self.instrumentNames:
            return
        names = instrumentNames[self.instrumentNamesLanguage].split('|')
        # add instrument_name_engraver if necessary
        ly.dom.addInstrumentNameEngraverIfNecessary(node)
        w = node.getWith()
        w['instrumentName'] = names[self.instrumentNamesFirst]
        if self.instrumentNamesOther < 2:
            w['shortInstrumentName'] = names[self.instrumentNamesOther]

    def setMidiInstrument(self, node, midiInstrument):
        if not self.createMidiOutput:
            return
        node.getWith()['midiInstrument'] = midiInstrument


    

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

paperSizes = ['a3', 'a4', 'a5', 'a6', 'a7', 'legal', 'letter', '11x17']
