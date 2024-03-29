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
A wizard to create empty staff paper with LilyPond
"""
import sip

from PyQt4.QtCore import QSize, Qt
from PyQt4.QtGui import (
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QIcon, QLabel,
    QPixmap, QPushButton, QSpinBox, QStackedWidget, QToolButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)

from PyKDE4.kdecore import KGlobal, KUrl, i18n
from PyKDE4.kdeui import (
    KDialog, KIcon, KMessageBox, KPushButton, KStandardGuiItem)
from PyKDE4.kio import KFileDialog, KIO

import ly, ly.indent
from kateshell.app import cacheresult
from kateshell.widgets import StackFader
from frescobaldi_app.mainapp import SymbolManager, lilyPondVersion
from frescobaldi_app.widgets import ClefSelector
from frescobaldi_app.runlily import BackgroundJob, LilyPreviewDialog
from frescobaldi_app.actions import openPDF, printPDF, getPrinter


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
        
        self.removeTagline = QCheckBox(i18n("Remove default tagline"))
        paper.layout().addWidget(self.removeTagline, 3, 0, 1, 2)
        
        settings.setLayout(QGridLayout())
        
        self.barLines = QCheckBox(i18n("Print Bar Lines"))
        self.barsPerLine = QSpinBox()
        l = QLabel(i18n("Bars per line:"))
        l.setBuddy(self.barsPerLine)
        settings.layout().addWidget(self.barLines, 0, 0, 1, 2)
        settings.layout().addWidget(l, 1, 0, Qt.AlignRight)
        settings.layout().addWidget(self.barsPerLine, 1, 1)
        self.barsPerLine.setRange(1, 20)
        
        self.pageNumbers = QCheckBox(i18n("Print Page Numbers"))
        self.pageNumStart = QSpinBox()
        l = QLabel(i18n("Start with:"))
        l.setBuddy(self.pageNumStart)
        settings.layout().addWidget(self.pageNumbers, 2, 0, 1, 2)
        settings.layout().addWidget(l, 3, 0, Qt.AlignRight)
        settings.layout().addWidget(self.pageNumStart, 3, 1)
        self.barLines.toggled.connect(self.barsPerLine.setEnabled)
        self.pageNumbers.toggled.connect(self.pageNumStart.setEnabled)
        
        # types
        self.typeWidgets = [
            SingleStaff(self),
            PianoStaff(self),
            OrganStaff(self),
            ChoirStaff(self),
            CustomStaff(self),
            ]
        for widget in self.typeWidgets:
            self.stack.addWidget(widget)
            self.typeChooser.addItem(widget.name())
        self.typeChooser.currentIndexChanged.connect(lambda index:
            self.stack.setCurrentWidget(self.typeWidgets[index]))

        self.actors = [
            PrintPDF,
            SavePDF,
            OpenPDF,
            CopyToEditor,
            ]
        for actor in self.actors:
            self.actionChooser.addItem(actor.name())
        
        self.setDetailsWidget(paperSettings)
        # cleanup on exit
        mainwin.aboutToClose.connect(self.cleanup)
        # buttons
        self.resetClicked.connect(self.default)
        self.tryClicked.connect(self.showPreview)
        self.setInitialSize(QSize(400, 240))
        self.default()
        self.loadSettings()
    
    def done(self, r):
        self.saveSettings()
        KDialog.done(self, r)
        if r:
            self.actors[self.actionChooser.currentIndex()](self)

    def default(self):
        """ Set everything to default """
        self.paperSize.setCurrentIndex(0)
        self.staffSize.setValue(22)
        self.pageCount.setValue(1)
        self.removeTagline.setChecked(False)
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

    def loadSettings(self):
        conf = config()
        self.removeTagline.setChecked(conf.readEntry("remove tagline", False))
        action = conf.readEntry("action", "PrintPDF")
        for index, actor in enumerate(self.actors):
            if actor.__name__ == action:
                self.actionChooser.setCurrentIndex(index)
    
    def saveSettings(self):
        conf = config()
        conf.writeEntry("remove tagline", self.removeTagline.isChecked())
        action = self.actors[self.actionChooser.currentIndex()].__name__
        conf.writeEntry("action", action)
    
    def showPreview(self):
        self.previewDialog().showPreview(self.ly())

    @cacheresult
    def previewDialog(self):
        return PreviewDialog(self)

    def ly(self):
        """
        Return the LilyPond document to print the empty staff paper.
        """
        staff = self.stack.currentWidget()
        output = []
        version = lilyPondVersion()
        if version:
            output.append('\\version "{0}"\n'.format(version))
        output.append('#(set-global-staff-size {0})\n'.format(self.staffSize.value()))
        # paper section
        output.append('\\paper {')
        if self.paperSize.currentIndex() > 0:
            output.append('#(set-paper-size "{0}")'.format(ly.paperSizes[self.paperSize.currentIndex()-1]))
        if self.pageNumbers.isChecked():
            output.append('top-margin = 10\\mm')
            output.append('first-page-number = #{0}'.format(self.pageNumStart.value()))
            output.append('oddHeaderMarkup = \\markup \\fill-line {')
            output.append('\\strut')
            output.append("\\fromproperty #'page:page-number-string")
            output.append('}')
        else:
            output.append('top-margin = 16\\mm')
            output.append('oddHeaderMarkup = ##f')
        output.append('evenHeaderMarkup = ##f')
        if self.removeTagline.isChecked():
            output.append('bottom-margin = 16\\mm')
            output.append('oddFooterMarkup = ##f')
        else:
            output.append('bottom-margin = 10\\mm')
            output.append('oddFooterMarkup = \\markup \\abs-fontsize #6 \\fill-line {')
            tagline = config().readEntry("tagline",
                '\\with-url #"http://www.frescobaldi.org/" FRESCOBALDI.ORG')
            output.append('\\sans {{ {0} }}'.format(tagline))
            output.append('\\strut')
            output.append('}')
        output.append('evenFooterMarkup = ##f')
        output.append('ragged-last-bottom = ##f')
        output.append('ragged-right = ##f')
        output.append('}\n')
        # music expression
        output.append('music = \\repeat unfold {0} {{ % pages'.format(self.pageCount.value()))
        output.append('\\repeat unfold {0} {{ % systems'.format(staff.systemCount()))
        output.append('\\repeat unfold {0} {{ % bars'.format(
            self.barLines.isChecked() and self.barsPerLine.value() or 1))
        output.extend(('r1', '\\noBreak', '}', '\\break', '\\noPageBreak', '}', '\\pageBreak', '}\n'))

        # get the layout
        layout = LayoutContexts()
        layout.add("Score", '\\remove "Bar_number_engraver"')
        layout.add("Voice", "\\override Rest #'stencil = ##f")
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

    def cleanup(self):
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
        Calls handlePDF() with the filename of the created PDF.
        Displays the error dialog if no PDF was created.
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
        dlg = KFileDialog(KUrl(), '*.pdf|{0}\n*|{1}'.format(
            i18n("PDF Files"), i18n("All Files")), dialog)
        dlg.setOperationMode(KFileDialog.Saving)
        dlg.setCaption(i18n("Save PDF"))
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
        return i18n("Print...")

    def __init__(self, dialog):
        BlankPaperJob.__init__(self, dialog)
        self.printer = None
        self.fileName = None
        printer = getPrinter(dialog, i18n("Print staff paper"))
        if printer:
            self.printer = printer
            self.printPDF()
        else:
            self.cleanup()
            
    def handlePDF(self, fileName):
        self.fileName = fileName
        self.printPDF()
        
    def printPDF(self):
        """ Prints if the printer and the PDF are both there."""
        if self.printer and self.fileName:
            printPDF(self.fileName, self.dialog, self.printer)


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
        self._alwaysShowSystemStartBar = False
    
    def setStaffContexts(self, staffContexts):
        """
        Specify which contexts must get visible or invisible barlines, etc.
        """
        self._staffContexts = staffContexts

    def addStaffContext(self, staffContext):
        """
        Just add a single context that must get (in)visible barlines etc.
        """
        if staffContext not in self._staffContexts:
            self._staffContexts.append(staffContext)

    def setSpanBarContexts(self, spanBarContexts):
        """
        Specify which contexts must have the Span_bar_engraver removed
        if no barlines are requested.
        """
        self._spanBarContexts = spanBarContexts
    
    def addSpanBarContext(self, spanBarContext):
        """
        Just add a single context which must have the Span_bar_engraver
        removed...
        """
        if spanBarContext not in self._spanBarContexts:
            self._spanBarContexts.append(spanBarContext)
        
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
    
    def setAlwaysShowSystemStartBar(self, show=True):
        line = "\override SystemStartBar #'collapse-height = #1"
        inscore = 'Score' in self._contexts and line in self._contexts['Score']
        if show and not inscore:
            self.add('Score', line)
        elif not show and inscore:
            self._contexts['Score'].remove(line)
    
    def ly(self):
        """ Return a list of LilyPond lines. """
        result = []
        for name, lines in self._contexts.iteritems():
            if lines:
                result.append('\\context {')
                result.append('\\' + name)
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
                return ['\\new Staff {{ \\clef "{0}" \\music }}'.format(self.clef.clef())]
            else:
                layout.add('Staff', "\\override Clef #'transparent = ##t")
                return ['\\new Staff { \\music }']
        
        
class PianoStaff(StaffBase):
    def __init__(self, dialog):
        StaffBase.__init__(self, dialog)
        l = QLabel(i18n("Systems per page:"))
        l.setBuddy(self.systems)
        self.layout().addWidget(l, 0, 1, Qt.AlignRight)
        self.layout().addWidget(self.systems, 0, 2)
        self.clefs = QCheckBox(i18n("Clefs"))
        self.layout().addWidget(self.clefs, 1, 2)
        
    def name(self):
        return i18n("Piano Staff")
        
    def default(self):
        self.systems.setValue(6)
        self.clefs.setChecked(True)
    
    def music(self, layout):
        layout.setSpanBarContexts(['PianoStaff'])
        if not self.clefs.isChecked():
            layout.add('Staff', "\\override Clef #'transparent = ##t")
        if lilyPondVersion() < (2, 13, 4):
            spacing = "#'minimum-Y-extent = #'(-6 . 3)"
        elif lilyPondVersion() < (2, 14, 0):
            spacing = "#'next-staff-spacing = #'((space . 10))"
        else:
            spacing = "#'next-staff-spacing = #'((basic-distance . 10))"
        return ['\\new PianoStaff <<',
            '\\new Staff \\with {',
            '\\override VerticalAxisGroup ' + spacing,
            '} { \\clef treble \\music }',
            '\\new Staff { \\clef bass \\music }',
            '>>']


class OrganStaff(PianoStaff):
    def name(self):
        return i18n("Organ Staff")
        
    def default(self):
        self.systems.setValue(4)
        self.clefs.setChecked(True)
    
    def music(self, layout):
        layout.setSpanBarContexts(['GrandStaff'])
        if not self.clefs.isChecked():
            layout.add('Staff', "\\override Clef #'transparent = ##t")
        if lilyPondVersion() < (2, 13, 4):
            spacing = "#'minimum-Y-extent = #'(-6 . 3)"
        elif lilyPondVersion() < (2, 14, 0):
            spacing = "#'next-staff-spacing = #'((space . 12) (stretchability . 1))"
            layout.add('Staff', "\\override VerticalAxisGroup "
                "#'next-staff-spacing = #'((space . 10) (stretchability . 1))")
        else:
            spacing = "#'next-staff-spacing = #'((basic-distance . 12) (stretchability . 1))"
            layout.add('Staff', "\\override VerticalAxisGroup "
                "#'next-staff-spacing = #'((basic-distance . 10) (stretchability . 1))")
        return ['<<',
            '\\new GrandStaff <<',
            '\\new Staff \\with {',
            '\\override VerticalAxisGroup ' + spacing,
            '} { \\clef treble \\music }',
            '\\new Staff { \\clef bass \\music }',
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
        self.clefs.setCompleter(None)
        l = QLabel(i18n("Clefs:"))
        l.setBuddy(self.clefs)
        self.layout().addWidget(l, 2, 1, Qt.AlignRight)
        self.layout().addWidget(self.clefs, 2, 2)
        
        # tool tips
        self.clefs.setToolTip(i18n(
            "Enter as many letters (S, A, T or B) as there are staves.\n"
            "See \"What's This\" for more information."))
        self.clefs.setWhatsThis(i18n(
            "To configure clefs, first set the number of staves per system. "
            "Then enter as many letters (S, A, T or B) as there are staves.\n\n"
            "S or A: treble clef,\n"
            "T: treble clef with an \"8\" below,\n"
            "B: bass clef\n\n"
            "So when you want to create music paper for a four-part mixed "
            "choir score, first set the number of staves per system to 4. "
            "Then enter \"SATB\" (without the quotes) here."))
        
        self.staffCount.valueChanged.connect(self.slotStaffCountChanged)
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
        clefs = self.clefs.currentText().upper()
        length = self.staffCount.value()
        if clefs and set(clefs) <= set("SATB"):
            # pad to staff count if necessary
            clefs = (clefs + clefs[-1] * length)[:length]
        else:
            clefs = [None] * length
            layout.add('Staff', "\\override Clef #'transparent = ##t")
        if lilyPondVersion() < (2, 13, 4):
            layout.add("Staff",
                "\\override VerticalAxisGroup #'minimum-Y-extent = #'(-6 . 4)")
        music = ['\\new ChoirStaff <<']
        for clef in clefs:
            music.append('\\new Staff {{{0} \\music }}'.format({
                'S': ' \\clef treble',
                'A': ' \\clef treble',
                'T': ' \\clef "treble_8"',
                'B': ' \\clef bass',
                None: '',
                }[clef]))
        music.append('>>')
        return music


class CustomStaff(SymbolManager, QWidget):
    def __init__(self, dialog):
        QWidget.__init__(self, dialog)
        SymbolManager.__init__(self)
        self.setDefaultSymbolSize(40)
        self.dialog = dialog
        self.setLayout(QGridLayout())
        self.tree = QTreeWidget()
        self.stack = QStackedWidget()
        StackFader(self.stack)
        self.systems = QSpinBox()
        newStaves = QVBoxLayout()
        operations = QHBoxLayout()
        self.layout().addLayout(newStaves, 0, 0)
        self.layout().addWidget(self.tree, 0, 1)
        self.layout().addWidget(self.stack, 0, 2, 1, 2)
        self.layout().addWidget(self.systems, 1, 3)
        self.systems.setRange(1, 64)
        l = QLabel(i18n("Systems per page:"))
        l.setBuddy(self.systems)
        self.layout().addWidget(l, 1, 2, Qt.AlignRight)
        self.layout().addLayout(operations, 1, 1)
        
        operations.setSpacing(0)
        operations.setContentsMargins(0, 0, 0, 0)
        removeButton = KPushButton(KStandardGuiItem.remove())
        removeButton.clicked.connect(self.removeSelectedItems)
        operations.addWidget(removeButton)
        upButton = QToolButton()
        upButton.clicked.connect(self.moveSelectedItemsUp)
        upButton.setIcon(KIcon("go-up"))
        operations.addWidget(upButton)
        downButton = QToolButton()
        downButton.clicked.connect(self.moveSelectedItemsDown)
        downButton.setIcon(KIcon("go-down"))
        operations.addWidget(downButton)
        newStaves.setSpacing(0)
        newStaves.setContentsMargins(0, 0, 0, 0)
        
        self.tree.setIconSize(QSize(32, 32))
        self.tree.setDragDropMode(QTreeWidget.InternalMove)
        self.tree.headerItem().setHidden(True)
        self.tree.itemSelectionChanged.connect(self.slotSelectionChanged)
        
        for staffType in (
            BracketItem,
            BraceItem,
            StaffItem,
            ):
            b = QPushButton(staffType.name())
            b.clicked.connect((lambda t: lambda: self.createItem(t))(staffType))
            b.setIconSize(QSize(40, 40))
            self.addSymbol(b, staffType.symbol())
            newStaves.addWidget(b)
        
    def createItem(self, staffType):
        empty = self.tree.topLevelItemCount() == 0
        items = self.tree.selectedItems()
        if len(items) == 1 and items[0].flags() & Qt.ItemIsDropEnabled:
            parent = items[0]
        else:
            parent = self.tree
        item = staffType(self, parent)
        if empty:
            item.setSelected(True)
        
    def slotSelectionChanged(self):
        items = self.tree.selectedItems()
        if items:
            self.stack.setCurrentWidget(items[0].widget)
        
    def moveSelectedItemsUp(self):
        items = self.tree.selectedItems()
        if items:
            item = items[0] # currently we support only one selected item
            parent = item.parent() or self.tree.invisibleRootItem()
            index = parent.indexOfChild(item)
            if index > 0:
                parent.takeChild(index)
                parent.insertChild(index - 1, item)
                self.tree.clearSelection()
                item.setSelected(True)
                item.setExpanded(True)
    
    def moveSelectedItemsDown(self):
        items = self.tree.selectedItems()
        if items:
            item = items[0] # currently we support only one selected item
            parent = item.parent() or self.tree.invisibleRootItem()
            index = parent.indexOfChild(item)
            if index < parent.childCount() - 1:
                parent.takeChild(index)
                parent.insertChild(index + 1, item)
                self.tree.clearSelection()
                item.setSelected(True)
                item.setExpanded(True)
    
    def removeSelectedItems(self):
        for item in self.tree.selectedItems():
            item.remove()

    def systemCount(self):
        return self.systems.value()
    
    def name(self):
        return i18n("Custom Staff")
        
    def default(self):
        while self.tree.topLevelItemCount():
            self.tree.topLevelItem(0).remove()
        self.systems.setValue(4)
        
    def items(self):
        for i in range(self.tree.topLevelItemCount()):
            yield self.tree.topLevelItem(i)
    
    def music(self, layout):
        music = sum((i.music(layout) for i in self.items()), ['<<'])
        music.append('>>')
        return music
        
    def staffCount(self):
        return sum(i.staffCount() for i in self.items())
        

class Item(QTreeWidgetItem):
    def __init__(self, staff, parent):
        self.staff = staff
        QTreeWidgetItem.__init__(self, parent)
        self.setText(0, self.name())
        self.setIcon(0, staff.symbolIcon(self.symbol()))
        self.setExpanded(True)
        self.widget = self.createWidget()
        staff.stack.addWidget(self.widget)
        
    def createWidget(self):
        return QWidget()
        
    def remove(self):
        while self.childCount():
            self.child(0).remove()
        sip.delete(self.widget)
        sip.delete(self)
    
    def items(self):
        for i in range(self.childCount()):
            yield self.child(i)
        
    def childMusic(self, layout):
        """ Returns a list with music from all children """
        return sum((i.music(layout) for i in self.items()), [])

    def staffCount(self):
        """ Returns the number of real staves """
        return sum(i.staffCount() for i in self.items())


class StaffItem(Item):
    def __init__(self, staff, parent):
        Item.__init__(self, staff, parent)
        self.setFlags(self.flags() & ~Qt.ItemIsDropEnabled)
        
    @staticmethod
    def name():
        return i18n("Staff")
    
    @staticmethod
    def symbol():
        return 'clef_none'

    def createWidget(self):
        w = QWidget()
        w.setLayout(QGridLayout())
        self.clef = ClefSelector(noclef=True, tab=True)
        l = QLabel(i18n("Clef:"))
        l.setBuddy(self.clef)
        w.layout().addWidget(l, 0, 0, Qt.AlignRight)
        w.layout().addWidget(self.clef, 0, 1)
        self.clef.currentIndexChanged.connect(self.clefChanged)
        self.spaceBelow = QSpinBox()
        self.spaceBelow.setRange(0, 25)
        self.spaceBelow.setValue(5)
        w.layout().addWidget(self.spaceBelow, 2, 1)
        l = QLabel(i18n("Space below:"))
        l.setBuddy(self.spaceBelow)
        w.layout().addWidget(l, 2, 0, Qt.AlignRight)
        return w
        
    def clefChanged(self, index):
        self.setIcon(0, self.staff.symbolIcon('clef_' + (self.clef.clef() or 'none')))

    def staffCount(self):
        return 1
    
    def music(self, layout):
        clef = self.clef.clef()
        staff = 'TabStaff' if clef == 'tab' else 'Staff'
        layout.addStaffContext(staff)
        music = ['\\new {0} \\with {{'.format(staff)]
        if lilyPondVersion() < (2, 13, 4):
            music.append(
                "\\override VerticalAxisGroup #'minimum-Y-extent = #'(-{0} . 5)".format(
                    self.spaceBelow.value()))
        elif lilyPondVersion() < (2, 14, 0):
            music.append(
                "\\override VerticalAxisGroup #'next-staff-spacing = #'((space . {0}))".format(
                    self.spaceBelow.value() + 5))
        else:
            music.append(
                "\\override VerticalAxisGroup #'next-staff-spacing = #'((basic-distance . {0}))".format(
                    self.spaceBelow.value() + 5))
        if not clef:
            music.append("\\override Clef #'transparent = ##t")
        if not clef or clef == 'tab':
            music.append('} { \\music }')
        else:
            music.append('}} {{ \\clef "{0}" \\music }}'.format(clef))
        return music


class BraceItem(Item):
    
    @staticmethod
    def name():
        return i18n("Brace")
    
    @staticmethod
    def symbol():
        return 'system_brace'

    def music(self, layout):
        layout.addSpanBarContext('PianoStaff')
        withMusic = []
        if self.staffCount() == 1:
            withMusic.append("\override SystemStartBrace #'collapse-height = #1")
            layout.setAlwaysShowSystemStartBar()
        if withMusic:
            music = ['\\new PianoStaff \\with {'] + withMusic + ['} <<']
        else:
            music = ['\\new PianoStaff <<']
        music.extend(self.childMusic(layout))
        music.append('>>')
        return music


class BracketItem(Item):
    
    @staticmethod
    def name():
        return i18n("Bracket")
    
    @staticmethod
    def symbol():
        return 'system_bracket'

    def createWidget(self):
        w = QWidget()
        w.setLayout(QVBoxLayout())
        self.squareBracket = QCheckBox(i18n("Square Bracket"))
        w.layout().addWidget(self.squareBracket)
        self.connectBarLines = QCheckBox(i18n("Connect bar lines"))
        self.connectBarLines.setChecked(True)
        w.layout().addWidget(self.connectBarLines)
        return w
        
    def music(self, layout):
        staff = self.connectBarLines.isChecked() and 'StaffGroup' or 'ChoirStaff'
        layout.addSpanBarContext(staff)
        withMusic = []
        if self.staffCount() == 1:
            withMusic.append("\override SystemStartBracket #'collapse-height = #1")
            layout.setAlwaysShowSystemStartBar()
        if self.squareBracket.isChecked():
            withMusic.append("systemStartDelimiter = #'SystemStartSquare")
        if withMusic:
            music = ['\\new {0} \\with {{'.format(staff)] + withMusic + ['} <<']
        else:
            music = ['\\new {0} <<'.format(staff)]
        music.extend(self.childMusic(layout))
        music.append('>>')
        return music


def config(group="blankpaper"):
    return KGlobal.config().group(group)

