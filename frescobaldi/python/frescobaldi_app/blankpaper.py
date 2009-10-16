# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
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

"""
A wizard to create empty staff paper with LilyPond
"""

from PyQt4.QtCore import QObject, QSize, Qt, SIGNAL
from PyQt4.QtGui import (
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QIcon, QLabel, QPixmap, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget)

from PyKDE4.kdecore import KGlobal, i18n
from PyKDE4.kdeui import KDialog, KIcon

import ly.indent
from kateshell.app import lazymethod
from frescobaldi_app.mainapp import SymbolManager
from frescobaldi_app.runlily import LilyPreviewDialog


def config(group=None):
    c = KGlobal.config().group("blankpaper")
    if group:
        c = c.group(group)
    return c


class Dialog(KDialog):
    def __init__(self, mainwin):
        KDialog.__init__(self, mainwin)
        self.mainwin = mainwin
        self.setButtons(KDialog.ButtonCode(
            KDialog.Try | KDialog.Help |
            KDialog.Details | KDialog.Reset |
            KDialog.Ok | KDialog.Cancel))
        self.setButtonIcon(KDialog.Try, KIcon("run-lilypond"))
        self.setCaption(i18n("Create blank staff paper"))
        self.setHelp("blankpaper")
        self.setDefaultButton(KDialog.Ok)

        layout = QGridLayout(self.mainWidget())
        self.typeChooser = QComboBox()
        self.stack = QStackedWidget()
        paperSettings = QWidget(self)
        paperSettings.setLayout(QHBoxLayout())
        self.actionChooser = QComboBox(self)
        layout.addWidget(self.typeChooser, 0, 1)
        layout.addWidget(self.stack, 1, 0, 1, 3)
        layout.addWidget(self.actionChooser, 2, 1)
        l = QLabel(i18n("Type:"))
        l.setBuddy(self.typeChooser)
        layout.addWidget(l, 0, 0, Qt.AlignRight)
        l = QLabel(i18n("Action:"))
        l.setBuddy(self.actionChooser)
        layout.addWidget(l, 2, 0, Qt.AlignRight)
        
        # paper stuff
        paper = QGroupBox(i18n("Paper"))
        paperSettings.layout().addWidget(paper)
        settings = QGroupBox(i18n("Settings"))
        paperSettings.layout().addWidget(settings)
        
        paper.setLayout(QGridLayout())
        
        self.paperSize = QComboBox()
        l = QLabel(i18n("Paper size:"))
        l.setBuddy(self.paperSize)
        paper.layout().addWidget(l, 0, 0, Qt.AlignRight)
        paper.layout().addWidget(self.paperSize, 0, 1)
        self.paperSize.addItem(i18n("Default"))
        self.paperSize.addItems(paperSizes)

        self.pointSize = QSpinBox()
        l = QLabel(i18n("Pointsize:"))
        l.setBuddy(self.pointSize)
        paper.layout().addWidget(l, 1, 0, Qt.AlignRight)
        paper.layout().addWidget(self.pointSize, 1, 1)
        self.pointSize.setRange(8, 40)
        
        self.pageCount = QSpinBox()
        l = QLabel(i18n("Page count:"))
        l.setBuddy(self.pageCount)
        paper.layout().addWidget(l, 2, 0, Qt.AlignRight)
        paper.layout().addWidget(self.pageCount, 2, 1)
        self.pageCount.setRange(1, 1000)
        
        settings.setLayout(QGridLayout())
        
        self.barLines = QCheckBox(i18n("Print Bar Lines"))
        self.barsPerLine = QSpinBox()
        l = QLabel(i18n("Bars per line:"))
        l.setBuddy(self.barsPerLine)
        settings.layout().addWidget(self.barLines, 0, 0, 1, 2)
        settings.layout().addWidget(l, 1, 0, Qt.AlignRight)
        settings.layout().addWidget(self.barsPerLine, 1, 1)
        self.barsPerLine.setRange(1, 20)
        
        self.pageNumbers = QCheckBox(i18n("Show Page Numbers"))
        self.pageNumStart = QSpinBox()
        l = QLabel(i18n("Start with:"))
        l.setBuddy(self.pageNumStart)
        settings.layout().addWidget(self.pageNumbers, 2, 0, 1, 2)
        settings.layout().addWidget(l, 3, 0, Qt.AlignRight)
        settings.layout().addWidget(self.pageNumStart, 3, 1)
        QObject.connect(self.barLines, SIGNAL("toggled(bool)"),
            self.barsPerLine.setEnabled)
        QObject.connect(self.pageNumbers, SIGNAL("toggled(bool)"),
            self.pageNumStart.setEnabled)
        
        # types
        self.typeWidgets = [
            SingleStaff(self),
            PianoStaff(self),
            ]
        for widget in self.typeWidgets:
            self.stack.addWidget(widget)
            self.typeChooser.addItem(widget.name())
        QObject.connect(self.typeChooser, SIGNAL("currentIndexChanged(int)"),
            lambda index: self.stack.setCurrentWidget(self.typeWidgets[index]))


        self.actors = [
            OpenPDF(),
            SavePDF(),
            PrintPDF(),
            CopyToEditor(),
            ]
        for actor in self.actors:
            self.actionChooser.addItem(actor.name())
        
        self.setDetailsWidget(paperSettings)
        
        # buttons
        QObject.connect(self, SIGNAL("resetClicked()"), self.default)
        QObject.connect(self, SIGNAL("tryClicked()"), self.showPreview)
        self.default()
    
    def done(self, r):
        if r:
            print self.ly()
        KDialog.done(self, r)

    def default(self):
        """ Set everything to default """
        self.paperSize.setCurrentIndex(0)
        self.pointSize.setValue(20)
        self.pageCount.setValue(1)
        self.barLines.setChecked(False)
        self.barsPerLine.setValue(4)
        self.barsPerLine.setEnabled(False)
        self.pageNumbers.setChecked(False)
        self.pageNumStart.setValue(1)
        self.pageNumStart.setEnabled(False)
        self.typeChooser.setCurrentIndex(0)
        self.actionChooser.setCurrentIndex(0)
        for widget in self.typeWidgets:
            widget.default()

    def showPreview(self):
        self.previewDialog().showPreview(self.ly())

    @lazymethod
    def previewDialog(self):
        return PreviewDialog(self)

    def ly(self):
        """
        Return the LilyPond document to print the empty staff paper.
        """
        staff = self.stack.currentWidget()
        music = ['\\version "2.12.0"']
        music.append('#(set-global-staff-size %d)' % self.pointSize.value())
        # paper section
        music.append('\\paper {')
        if self.paperSize.currentIndex() > 0:
            music.append('#(set-paper-size "%s")' % paperSizes[self.paperSize.currentIndex()-1])
        if self.pageNumbers.isChecked():
            music.append('first-page-number = #%d' % self.pageNumStart.value())
            music.append('oddHeaderMarkup = \\markup \\fill-line {')
            music.append("\\null\n\\fromproperty #'page:page-number-string\n}")
        else:
            music.append('oddHeaderMarkup = ##f')
        music.append('evenHeaderMarkup = ##f')
        music.append('oddFooterMarkup = \\markup \\fill-line {')
        music.append("\\null\n\\sans \\fontsize #-8 { %s }\n}" % "FRESCOBALDI.ORG")
        music.append("head-separation = 0.1\\in")
        music.append("foot-separation = 0.1\\in")
        music.append("top-margin = 0.5\\in")
        music.append("bottom-margin = 0.5\\in")
        music.append("ragged-last-bottom = ##f")
        music.append("}\n")
        # music expression
        music.append("music = \\repeat unfold %s {\n\\repeat unfold %s {\n\\repeat unfold %s {" %
            (self.pageCount.value(), staff.systemCount(),
            self.barLines.isChecked() and self.barsPerLine.value() or 1))
        music.append("s1\n\\noBreak\n}\n\\break\n\\noPageBreak\n}\n\\pageBreak\n}\n")

        # layout
        music.append('\\layout {\nindent = #0\n\\context {\n\\Score')
        music.append('\\remove "Bar_number_engraver"')
        music.extend(staff.layoutScore())
        music.append('}\n\\context {\n\\Staff')
        music.append('\\remove "Time_signature_engraver"')
        if not self.barLines.isChecked():
            music.append("\\override BarLine #'stencil = ##f")
        music.extend(staff.layoutStaff())
        music.append('}\n}\n')
        
        # score
        music.append('\\score {')
        music.append(staff.music())
        music.append('}')
        
        
        return ly.indent.indent('\n'.join(music))


class PreviewDialog(LilyPreviewDialog):
    def __init__(self, parent):
        LilyPreviewDialog.__init__(self, parent)
        self.setCaption(i18n("Blank staff paper preview"))


class StaffBase(QWidget):
    def __init__(self, dialog):
        QWidget.__init__(self, dialog)
        self.dialog = dialog
        self.setLayout(QGridLayout())
        self.systems = QSpinBox()
        self.systems.setRange(1, 64)
        self.layout().setColumnStretch(0, 1)
        self.layout().setColumnStretch(3, 1)

    def systemCount(self):
        return self.systems.value()
    
    def layoutStaff(self):
        """ Returns input lines for the Staff layout context """
        return []
        
    def layoutScore(self):
        """ Returns input lines for the Score layout context """
        return []

    def music(self):
        """ Returns the stuff for the \score { ... } block """
        return ''


class SingleStaff(StaffBase):
    def __init__(self, dialog):
        StaffBase.__init__(self, dialog)
        l = QLabel(i18n("Staves per page:"))
        l.setBuddy(self.systems)
        self.layout().addWidget(l, 0, 1, Qt.AlignRight)
        self.layout().addWidget(self.systems, 0, 2)
        self.clef = ClefSelector()
        l = QLabel(i18n("Clef:"))
        l.setBuddy(self.clef)
        self.layout().addWidget(l, 1, 1, Qt.AlignRight)
        self.layout().addWidget(self.clef, 1, 2)
        
    def name(self):
        return i18n("Single Staff")
        
    def default(self):
        self.systems.setValue(12)

    def layoutStaff(self):
        return ["\\override VerticalAxisGroup #'minimum-Y-extent = #'(-6 . 4)"]

    def music(self):
        if self.clef.clef():
            return '\\new Staff { \\clef %s \\music }' % self.clef.clef()
        else:
            return '\\new Staff \\with {\n\\remove "Clef_engraver"\n} { \\music }'
        
        
        
        
class PianoStaff(StaffBase):
    def __init__(self, dialog):
        StaffBase.__init__(self, dialog)
        l = QLabel(i18n("Systems per page:"))
        l.setBuddy(self.systems)
        self.layout().addWidget(l, 0, 1, Qt.AlignRight)
        self.layout().addWidget(self.systems, 0, 2)
    
    def name(self):
        return i18n("Piano Staff")
        
    def default(self):
        pass







class OpenPDF(object):
    def name(self):
        return i18n("Open in PDF viewer")
    

class SavePDF(object):
    def name(self):
        return i18n("Save PDF As...")


class PrintPDF(object):
    def name(self):
        return i18n("Directly print PDF on default printer")


class CopyToEditor(object):
    def name(self):
        return i18n("Copy LilyPond code to editor")



class ClefSelector(SymbolManager, QComboBox):
    def __init__(self, parent=None, noclef=True):
        SymbolManager.__init__(self)
        QComboBox.__init__(self, parent)
        self.setDefaultSymbolSize(48)
        self.setSymbolSize(self, 48)
        self.clefs = [
            ('treble', i18n("Treble")),
            ('alto', i18n("Alto")),
            ('tenor', i18n("Tenor")),
            ('treble_8', i18n("Treble 8")),
            ('bass', i18n("Bass")),
            ]
        if noclef:
            self.clefs.insert(0, ('', i18n("No Clef")))
        self.addItems([title for name, title in self.clefs])
        for index, (name, title) in enumerate(self.clefs):
            self.addItemSymbol(self, index, 'clef_%s' % (name or 'none'))
    
    def clef(self):
        return self.clefs[self.currentIndex()][0]
    

paperSizes = ['a3', 'a4', 'a5', 'a6', 'a7', 'legal', 'letter', '11x17']



