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
import ly, ly.dom

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

def config(group=None):
    c = KGlobal.config().group("scorewiz")
    if group:
        c = c.group(group)
    return c



class Builder(ly.dom.Receiver):
    """
    Interacts with the parts and builds the LilyPond document,
    based on the user's preferences.
    """
    def __init__(self):
        super(Builder, self).__init__()
        
        # Create MIDI output?
        self.createMidiOutput = False
        
        # output instrument names?
        self.instrumentNames = False
        
        # 0 = italian, 1 = english, 2 = translated
        self.instrumentNamesLanguage = 0
        
        # 0 = long, 1 = short
        self.instrumentNamesFirst = 0
        
        # 0 = long, 1 = short, 2 = none
        self.instrumentNamesOther = 1
        
    
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
        durs = [(KIcon('note_%s' % d.replace('.', 'd')), d) for d in durations]
        for icon, text in durs:
            self.pickup.addItem(icon, text)
        l.setBuddy(self.pickup)



    def default(self):
        """ Set various items to their default state """
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
