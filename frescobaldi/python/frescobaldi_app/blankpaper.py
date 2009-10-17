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
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QIcon, QLabel,
    QPixmap, QSpinBox, QStackedWidget, QVBoxLayout, QWidget)

from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KDialog, KIcon

import ly.indent
from kateshell.app import lazymethod
from frescobaldi_app.widgets import StackFader
from frescobaldi_app.mainapp import SymbolManager
from frescobaldi_app.runlily import BackgroundJob, LilyPreviewDialog


class Dialog(KDialog):
    def __init__(self, mainwin):
        KDialog.__init__(self, mainwin)
        self._jobs = []
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
        StackFader(self.stack)
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

        self.staffSize = QSpinBox()
        l = QLabel(i18n("Staff Size:"))
        l.setBuddy(self.staffSize)
        paper.layout().addWidget(l, 1, 0, Qt.AlignRight)
        paper.layout().addWidget(self.staffSize, 1, 1)
        self.staffSize.setRange(8, 40)
        
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
            OrganStaff(self),
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
        
        QObject.connect(self, SIGNAL("destroyed()"), self.slotDestroyed)
        # buttons
        QObject.connect(self, SIGNAL("resetClicked()"), self.default)
        QObject.connect(self, SIGNAL("tryClicked()"), self.showPreview)
        self.default()
    
    def done(self, r):
        KDialog.done(self, r)
        if r:
            self.actors[self.actionChooser.currentIndex()].doIt(self)

    def default(self):
        """ Set everything to default """
        self.paperSize.setCurrentIndex(0)
        self.staffSize.setValue(20)
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
        output = ['\\version "2.12.0"']
        output.append('#(set-global-staff-size %d)' % self.staffSize.value())
        # paper section
        output.append('\\paper {')
        if self.paperSize.currentIndex() > 0:
            output.append('#(set-paper-size "%s")' % paperSizes[self.paperSize.currentIndex()-1])
        if self.pageNumbers.isChecked():
            output.append('first-page-number = #%d' % self.pageNumStart.value())
            output.append('oddHeaderMarkup = \\markup \\fill-line {')
            output.append("\\null\n\\fromproperty #'page:page-number-string\n}")
        else:
            output.append('oddHeaderMarkup = ##f')
        output.append('evenHeaderMarkup = ##f')
        output.append('oddFooterMarkup = \\markup \\fill-line {')
        output.append("\\null\n\\sans \\fontsize #-8 { %s }\n}" % "FRESCOBALDI.ORG")
        output.append("head-separation = 0.1\\in")
        output.append("foot-separation = 0.1\\in")
        output.append("top-margin = 0.5\\in")
        output.append("bottom-margin = 0.5\\in")
        output.append("ragged-last-bottom = ##f")
        output.append("}\n")
        # output.expression
        output.append("music = \\repeat unfold %d { %% pages" % self.pageCount.value())
        output.append("\\repeat unfold %d { %% systems" % staff.systemCount())
        output.append("\\repeat unfold %d { %% bars" % (
            self.barLines.isChecked() and self.barsPerLine.value() or 1))
        output.extend(("s1", "\\noBreak", "}", "\\break", "\\noPageBreak", "}", "\\pageBreak", "}\n"))

        # get the layout
        layout = LayoutContexts()
        layout.add("Score", '\\remove "Bar_number_engraver"')
        music = staff.music(layout)
        layout.addToStaffContexts('\\remove "Time_signature_engraver"')
        if not self.barLines.isChecked():
            layout.disableBarLines()
        # write it out
        output.append('\\layout {\nindent = #0')
        output.extend(layout.ly())
        output.append('}\n')
        
        # score
        output.append('\\score {')
        output.extend(music)
        output.append('}\n')
        return ly.indent.indent('\n'.join(output))

    def createJob(self):
        job = PDFJob(self.ly())
        self._jobs.append(job)
        return job
    
    def removeJob(self, job):
        if job in self._jobs:
            self._jobs.remove(job)
            job.cleanup()
        
    def slotDestroyed(self):
        for job in self._jobs:
            job.cleanup()
            


class PDFJob(BackgroundJob):
    def pdf(self):
        """ return the filename of the created PDF file. """
        pdfs = self.result("pdf")
        if pdfs:
            return pdfs[0]


class PreviewDialog(LilyPreviewDialog):
    def __init__(self, parent):
        LilyPreviewDialog.__init__(self, parent)
        self.setCaption(i18n("Blank staff paper preview"))


class LayoutContexts(object):
    """
    A class to manage the \context { \Staff ... } type constructs.
    """
    def __init__(self):
        self._contexts = {}
        self._staffContexts = ['Staff']
        self._spanBarContexts = []
    
    def setStaffContexts(self, staffContexts):
        """
        Specify which contexts must get visible or invisible barlines, etc.
        """
        self._staffContexts = staffContexts

    def setSpanBarContexts(self, spanBarContexts):
        """
        Specify which contexts must have the Span_bar_engraver removed
        if no barlines are requested.
        """
        self._spanBarContexts = spanBarContexts
        
    def add(self, context, line):
        """ Add a line to the given context """
        self._contexts.setdefault(context, []).append(line)
    
    def addToStaffContexts(self, line):
        for s in self._staffContexts:
            self.add(s, line)

    def disableBarLines(self):
        self.addToStaffContexts("\\override BarLine #'stencil = ##f")
        for c in self._spanBarContexts:
            self.add(c, '\\remove "Span_bar_engraver"')
    
    def ly(self):
        """ Return a list of LilyPond lines. """
        result = []
        for name, lines in self._contexts.iteritems():
            result.append('\\context {')
            result.append('\\%s' % name)
            result.extend(lines)
            result.append('}')
        return result



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
    
    def music(self, layout):
        """ add lines to layout contexts and returns the music, also in lines """
        return []


class SingleStaff(StaffBase):
    def __init__(self, dialog):
        StaffBase.__init__(self, dialog)
        l = QLabel(i18n("Staves per page:"))
        l.setBuddy(self.systems)
        self.layout().addWidget(l, 0, 1, Qt.AlignRight)
        self.layout().addWidget(self.systems, 0, 2)
        self.clef = ClefSelector(noclef=True, tab=True)
        l = QLabel(i18n("Clef:"))
        l.setBuddy(self.clef)
        self.layout().addWidget(l, 1, 1, Qt.AlignRight)
        self.layout().addWidget(self.clef, 1, 2)
        
    def name(self):
        return i18n("Single Staff")
        
    def default(self):
        self.systems.setValue(12)

    def music(self, layout):
        if self.clef.clef() == 'tab':
            layout.setStaffContexts(['TabStaff'])
            return ['\\new TabStaff { \\music }']
        else:
            if self.clef.clef():
                return ['\\new Staff { \\clef %s \\music }' % self.clef.clef()]
            else:
                layout.add('Staff', '\\remove "Clef_engraver"')
                return ['\\new Staff { \\music }']
        
        
        
        
class PianoStaff(StaffBase):
    def __init__(self, dialog):
        StaffBase.__init__(self, dialog)
        l = QLabel(i18n("Systems per page:"))
        l.setBuddy(self.systems)
        self.layout().addWidget(l, 0, 1, Qt.AlignRight)
        self.layout().addWidget(self.systems, 0, 2)
        self.clefs = QCheckBox(i18n("Clefs"))
        self.layout().addWidget(self.clefs, 1, 1, 2, 1)
        
    def name(self):
        return i18n("Piano Staff")
        
    def default(self):
        self.systems.setValue(6)
        self.clefs.setChecked(True)
    
    def music(self, layout):
        layout.setSpanBarContexts(['PianoStaff'])
        if not self.clefs.isChecked():
            layout.add('Staff', '\\remove "Clef_engraver"')
        return ['\\new PianoStaff <<',
            '\\new Staff { \\clef treble \\music }',
            '\\new Staff \\with {',
            "\\override VerticalAxisGroup #'minimum-Y-extent = #'(-3 . 6)",
            '} { \\clef bass \\music }',
            '>>']


class OrganStaff(StaffBase):
    def __init__(self, dialog):
        StaffBase.__init__(self, dialog)
        l = QLabel(i18n("Systems per page:"))
        l.setBuddy(self.systems)
        self.layout().addWidget(l, 0, 1, Qt.AlignRight)
        self.layout().addWidget(self.systems, 0, 2)
        self.clefs = QCheckBox(i18n("Clefs"))
        self.layout().addWidget(self.clefs, 1, 1, 2, 1)
        
    def name(self):
        return i18n("Organ Staff")
        
    def default(self):
        self.systems.setValue(4)
        self.clefs.setChecked(True)
    
    def music(self, layout):
        layout.setSpanBarContexts(['PianoStaff'])
        if not self.clefs.isChecked():
            layout.add('Staff', '\\remove "Clef_engraver"')
        return ['<<',
            '\\new PianoStaff <<',
            '\\new Staff { \\clef treble \\music }',
            '\\new Staff \\with {',
            "\\override VerticalAxisGroup #'minimum-Y-extent = #'(-6 . 6)",
            '} { \\clef bass \\music }',
            '>>',
            '\\new Staff { \\clef bass \\music }',
            '>>']






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
    
    def doIt(self, dialog):
        dialog.mainwin.currentDocument().view.insertText(dialog.ly())


class ClefSelector(SymbolManager, QComboBox):
    """
    A ComboBox to select a clef.
    
    Set resp. noclef and/or tab to True for those allowing the user
    to choose those clef/staff types.
    """
    def __init__(self, parent=None, noclef=False, tab=False):
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
            ('percussion', i18n("Percussion")),
            ]
        if tab:
            self.clefs.append(('tab', i18n("Tab clef")))
        if noclef:
            self.clefs.insert(0, ('', i18n("No Clef")))
        self.addItems([title for name, title in self.clefs])
        for index, (name, title) in enumerate(self.clefs):
            self.addItemSymbol(self, index, 'clef_%s' % (name or 'none'))
    
    def clef(self):
        """
        Returns the LilyPond name of the selected clef, or the empty string
        for no clef.
        """
        return self.clefs[self.currentIndex()][0]
    

paperSizes = ['a3', 'a4', 'a5', 'a6', 'a7', 'legal', 'letter', '11x17']



