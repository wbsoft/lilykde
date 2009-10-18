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

from PyKDE4.kdecore import KUrl, i18n
from PyKDE4.kdeui import KDialog, KIcon, KMessageBox
from PyKDE4.kio import KFileDialog, KIO

import ly, ly.indent
from kateshell.app import lazymethod
from frescobaldi_app.version import defaultVersion
from frescobaldi_app.widgets import StackFader, ClefSelector
from frescobaldi_app.runlily import BackgroundJob, LilyPreviewDialog
from frescobaldi_app.actions import openPDF, printPDF


class Dialog(KDialog):
    def __init__(self, mainwin):
        KDialog.__init__(self, mainwin)
        self.jobs = []
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
        
        # tool tips
        self.typeChooser.setToolTip(i18n(
            "Choose what kind of empty staves you want to create."))
        self.actionChooser.setToolTip(i18n(
            "Choose which action happens when clicking \"Ok\"."))
        self.setButtonToolTip(KDialog.Try, i18n(
            "Preview the empty staff paper."))
        self.setButtonToolTip(KDialog.Details, i18n(
            "Click to see more settings."))
        
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
        self.paperSize.addItems(ly.paperSizes)

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
            ChoirStaff(self),
            ]
        for widget in self.typeWidgets:
            self.stack.addWidget(widget)
            self.typeChooser.addItem(widget.name())
        QObject.connect(self.typeChooser, SIGNAL("currentIndexChanged(int)"),
            lambda index: self.stack.setCurrentWidget(self.typeWidgets[index]))

        self.actors = [
            OpenPDF,
            SavePDF,
            PrintPDF,
            CopyToEditor,
            ]
        for actor in self.actors:
            self.actionChooser.addItem(actor.name())
        
        self.setDetailsWidget(paperSettings)
        # cleanup on exit
        QObject.connect(self, SIGNAL("destroyed()"), self.slotDestroyed)
        # buttons
        QObject.connect(self, SIGNAL("resetClicked()"), self.default)
        QObject.connect(self, SIGNAL("tryClicked()"), self.showPreview)
        self.default()
    
    def done(self, r):
        KDialog.done(self, r)
        if r:
            self.actors[self.actionChooser.currentIndex()](self)

    def default(self):
        """ Set everything to default """
        self.paperSize.setCurrentIndex(0)
        self.staffSize.setValue(22)
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
        output = []
        version = defaultVersion()
        if version:
            output.append('\\version "%s"\n' % version)
        output.append('#(set-global-staff-size %d)\n' % self.staffSize.value())
        # paper section
        output.append('\\paper {')
        if self.paperSize.currentIndex() > 0:
            output.append('#(set-paper-size "%s")' % ly.paperSizes[self.paperSize.currentIndex()-1])
        if self.pageNumbers.isChecked():
            output.append('first-page-number = #%d' % self.pageNumStart.value())
            output.append('oddHeaderMarkup = \\markup \\fill-line {')
            output.append('\\null')
            output.append("\\fromproperty #'page:page-number-string")
            output.append('}')
        else:
            output.append('oddHeaderMarkup = \\markup \\strut')
        output.append('evenHeaderMarkup = ##f')
        output.append('oddFooterMarkup = \\markup \\fill-line {')
        output.append('\\sans \\fontsize #-8 { %s }' % "FRESCOBALDI.ORG")
        output.append('\\null')
        output.append('}')
        output.append('head-separation = 3\\mm')
        output.append('foot-separation = 5\\mm')
        output.append('top-margin = 10\\mm')
        output.append('bottom-margin = 10\\mm')
        output.append('ragged-last-bottom = ##f')
        output.append('}\n')
        # music expression
        output.append('music = \\repeat unfold %d { %% pages' % self.pageCount.value())
        output.append('\\repeat unfold %d { %% systems' % staff.systemCount())
        output.append('\\repeat unfold %d { %% bars' % (
            self.barLines.isChecked() and self.barsPerLine.value() or 1))
        output.extend(('s1', '\\noBreak', '}', '\\break', '\\noPageBreak', '}', '\\pageBreak', '}\n'))

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

    def slotDestroyed(self):
        for job in self.jobs[:]: # copy
            job.cleanup()
            


class PreviewDialog(LilyPreviewDialog):
    def __init__(self, parent):
        LilyPreviewDialog.__init__(self, parent)
        self.setCaption(i18n("Blank staff paper preview"))


class BlankPaperJob(BackgroundJob):
    def __init__(self, dialog):
        BackgroundJob.__init__(self)
        self.dialog = dialog
        dialog.jobs.append(self)
        self.run(dialog.ly(), 'staffpaper.ly')
    
    def finished(self):
        """
        Returns the filename of the created PDF or None.
        Displays the error dialog if none was created.
        """
        pdfs = self.job.updatedFiles()("pdf")
        if pdfs:
            self.handlePDF(pdfs[0])
        else:
            self.showLog(i18n("No PDF was created."), '', self.dialog)
        
    def cleanup(self):
        BackgroundJob.cleanup(self)
        self.dialog.jobs.remove(self)


# The actions that can be taken on a blank paper job
class OpenPDF(BlankPaperJob):
    @staticmethod
    def name():
        return i18n("Open in PDF viewer")
    
    def handlePDF(self, fileName):
        openPDF(fileName, self.dialog)


class SavePDF(BlankPaperJob):
    @staticmethod
    def name():
        return i18n("Save PDF As...")

    def __init__(self, dialog):
        BlankPaperJob.__init__(self, dialog)
        self.sourcePDF = None
        self.targetPDF = None
        dlg = KFileDialog(KUrl(), '*.pdf|%s\n*|%s' % (
            i18n("PDF Files"), i18n("All Files")), dialog)
        dlg.setOperationMode(KFileDialog.Saving)
        dlg.setConfirmOverwrite(True)
        dlg.setSelection('staffpaper.pdf')
        if dlg.exec_():
            self.targetPDF = dlg.selectedUrl()
            self.savePDF()
        else:
            self.cleanup()
        
    def handlePDF(self, fileName):
        self.sourcePDF = fileName
        self.savePDF()
        
    def savePDF(self):
        """ Initiates a copy operation if source and target are both there. """
        if self.sourcePDF and self.targetPDF:
            if not KIO.NetAccess.upload(self.sourcePDF, self.targetPDF, self.dialog.mainwin):
                KMessageBox.error(self.dialog, KIO.NetAccess.lastErrorString())
            self.cleanup()


class PrintPDF(BlankPaperJob):
    @staticmethod
    def name():
        return i18n("Directly print on default printer")

    def handlePDF(self, fileName):
        printPDF(fileName, self.dialog)


class CopyToEditor(object):
    @staticmethod
    def name():
        return i18n("Copy LilyPond code to editor")
    
    def __init__(self, dialog):
        doc = dialog.mainwin.currentDocument()
        doc.view.insertText(doc.indent(dialog.ly()))


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


class OrganStaff(PianoStaff):
    def name(self):
        return i18n("Organ Staff")
        
    def default(self):
        self.systems.setValue(4)
        self.clefs.setChecked(True)
    
    def music(self, layout):
        PianoStaff.music(self, layout)
        return ['<<',
            '\\new PianoStaff <<',
            '\\new Staff { \\clef treble \\music }',
            '\\new Staff \\with {',
            "\\override VerticalAxisGroup #'minimum-Y-extent = #'(-5 . 6)",
            '} { \\clef bass \\music }',
            '>>',
            '\\new Staff { \\clef bass \\music }',
            '>>']


class ChoirStaff(StaffBase):
    def __init__(self, dialog):
        StaffBase.__init__(self, dialog)
        self.staffCount = QSpinBox()
        self.staffCount.setRange(2, 8)
        l = QLabel(i18n("Staves per system:"))
        l.setBuddy(self.staffCount)
        self.layout().addWidget(l, 0, 1, Qt.AlignRight)
        self.layout().addWidget(self.staffCount, 0, 2)
        l = QLabel(i18n("Systems per page:"))
        l.setBuddy(self.systems)
        self.layout().addWidget(l, 1, 1, Qt.AlignRight)
        self.layout().addWidget(self.systems, 1, 2)
        self.clefs = QComboBox()
        self.clefs.setEditable(True)
        l = QLabel(i18n("Clefs:"))
        l.setBuddy(self.clefs)
        self.layout().addWidget(l, 2, 1, Qt.AlignRight)
        self.layout().addWidget(self.clefs, 2, 2)
        
        # tool tips
        self.clefs.setToolTip(i18n(
            "Enter as much letters (S, A, T or B) as there are staves.\n"
            "See \"What's This\" for more information."))
        self.clefs.setWhatsThis(i18n(
            "To configure clefs, first set the number of staves per system. "
            "Then enter as much letters (S, A, T or B) as there are staves.\n\n"
            "S or A: treble clef,\n"
            "T: treble clef with an \"8\" below,\n"
            "B: bass clef\n\n"
            "So when you want to create music paper for a four-part mixed "
            "choir score, first set the number of staves per system to 4. "
            "Then enter \"SATB\" (without the quotes) here."))
        
        QObject.connect(self.staffCount, SIGNAL("valueChanged(int)"),
            self.slotStaffCountChanged)
        self.slotStaffCountChanged(2)    
        
    def name(self):
        return i18n("Choir Staff")
        
    def default(self):
        self.staffCount.setValue(2)
    
    def slotStaffCountChanged(self, value):
        self.clefs.clear()
        self.clefs.addItem(i18n("None"))
        self.clefs.addItems((
            ('SB', 'SS', 'ST', 'TT', 'TB', 'BB'), # 2
            ('SSB', 'SSS', 'TTB', 'TTT', 'TTB'), # 3
            ('SATB', 'STTB', 'TTBB'), # 4
            ('SSATB', 'SATTB'), # 5
            ('SSATTB', 'SSATBB'), #6
            ('SSATTBB', ), # 7
            ('SATBSATB', 'SSAATTBB') #8
            )[value - 2])
        self.clefs.setCurrentIndex(0)
        systemCount = int(12 / value)
        if systemCount == 1 and self.dialog.staffSize.value() <= 18:
            systemCount = 2
        self.systems.setValue(systemCount)

    def music(self, layout):
        clefs = unicode(self.clefs.currentText()).upper()
        length = self.staffCount.value()
        if clefs and set(clefs) <= set("SATB"):
            # pad to staff count if necessary
            clefs = (clefs + clefs[-1] * length)[:length]
        else:
            clefs = [None] * length
            layout.add("Staff", '\\remove "Clef_engraver"')
        layout.add("Staff",
            "\\override VerticalAxisGroup #'minimum-Y-extent = #'(-6 . 4)")
        music = ['\\new ChoirStaff <<']
        for clef in clefs:
            music.append('\\new Staff {%s \\music }' % {
                'S': ' \\clef treble',
                'A': ' \\clef treble',
                'T': ' \\clef "treble_8"',
                'B': ' \\clef bass',
                None: '',
                }[clef])
        music.append('>>')
        return music


