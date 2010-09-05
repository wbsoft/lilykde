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
Some nice widgets.
"""

import os

from PyQt4.QtCore import QRegExp, QTimeLine
from PyQt4.QtGui import (
    QFileDialog, QGridLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPainter, QPixmap, QRegExpValidator, QWidget)
from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import (
    KDialog, KLineEdit, KPushButton, KStandardGuiItem, KVBox)

from signals import Signal


class ExecLineEdit(QLineEdit):
    """
    A QLineEdit to enter a filename or path.
    The background changes to red if the entered path is not an
    executable command.
    """
    def __init__(self, *args):
        QLineEdit.__init__(self, *args)
        self.textChanged.connect(self._checkexec)

    def _get(self, filename):
        return filename

    def _checkexec(self, filename):
        if not findexe(self._get(filename)):
            self.setStyleSheet("QLineEdit { background-color: #FAA }")
        else:
            self.setStyleSheet("")


class ExecArgsLineEdit(ExecLineEdit):
    """
    An ExecLineEdit that allows arguments in the command string.
    """
    def _get(self, filename):
        if filename:
            return filename.split()[0]
        else:
            return ''


class ListEdit(QWidget):
    """A widget to edit a list of items (e.g. a list of directories)."""
    
    # emitted when anything changed in the listbox.
    changed = Signal()
    
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        layout = QGridLayout(self)
        self.setLayout(layout)
        
        self.addButton = KPushButton(KStandardGuiItem.add())
        self.editButton = KPushButton(KStandardGuiItem.configure())
        self.removeButton = KPushButton(KStandardGuiItem.remove())
        self.listBox = QListWidget()
        
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.listBox, 0, 0, 4, 1)
        layout.addWidget(self.addButton, 0, 1)
        layout.addWidget(self.editButton, 1, 1)
        layout.addWidget(self.removeButton, 2, 1)
        
        @self.addButton.clicked.connect
        def addClicked():
            item = self.createItem()
            if self.openEditor(item):
                self.addItem(item)
                
        @self.editButton.clicked.connect
        def editClicked():
            item = self.listBox.currentItem()
            item and self.editItem(item)
        
        @self.removeButton.clicked.connect
        def removeClicked():
            item = self.listBox.currentItem()
            if item:
                self.removeItem(item)
        
        @self.listBox.itemDoubleClicked.connect
        def itemDoubleClicked(item):
            item and self.editItem(item)
            
        self.listBox.model().layoutChanged.connect(self.changed)
    
        def updateSelection():
            selected = bool(self.listBox.currentItem())
            self.editButton.setEnabled(selected)
            self.removeButton.setEnabled(selected)
        self.changed.connect(updateSelection)
        self.listBox.itemSelectionChanged.connect(updateSelection)
        updateSelection()
    
    def createItem(self):
        return QListWidgetItem()
        
    def addItem(self, item):
        self.listBox.addItem(item)
        self.itemChanged(item)
        self.changed()
        
    def removeItem(self, item):
        self.listBox.takeItem(self.listBox.row(item))
        self.changed()
        
    def editItem(self, item):
        if self.openEditor(item):
            self.itemChanged(item)
            self.changed()
            
    def setCurrentItem(self, item):
        self.listBox.setCurrentItem(item)
        
    def setCurrentRow(self, row):
        self.listBox.setCurrentRow(row)
        
    def openEditor(self, item):
        """Opens an editor (dialog) for the item.
        
        Returns True if the dialog was accepted and the item edited.
        Returns False if the dialog was cancelled (the item must be left
        unedited).
        """
        pass
    
    def itemChanged(self, item):
        """Called after an item has been added or edited.
        
        Re-implement to do something at this moment if needed, e.g. alter the
        text or display of other items.
        """
        pass
    
    def setValue(self, strings):
        """Sets the listbox to a list of strings."""
        self.listBox.clear()
        self.listBox.addItems(strings)
        self.changed()
        
    def value(self):
        """Returns the list of paths in the listbox."""
        return [self.listBox.item(i).text()
            for i in range(self.listBox.count())]
    
    def setItems(self, items):
        """Sets the listbox to a list of items."""
        self.listBox.clear()
        for item in items:
            self.listBox.addItem(item)
        self.changed()
    
    def items(self):
        """Returns the list of items in the listbox."""
        return [self.listBox.item(i)
            for i in range(self.listBox.count())]
        
    def clear(self):
        """Clears the listbox."""
        self.listBox.clear()
        self.changed()
        

class FilePathEdit(ListEdit):
    """
    A widget to edit a list of directories (e.g. a file path).
    """
    def __init__(self, *args, **kwargs):
        super(FilePathEdit, self).__init__(*args, **kwargs)
        
    def openEditor(self, item):
        """Asks the user for an (existing) directory."""
        directory = item.text()
        directory = QFileDialog.getExistingDirectory(self, None, directory)
        if directory:
            item.setText(directory)
            return True
        return False


class StackFader(QWidget):
    """
    A widget that creates smooth transitions in a QStackedWidget.
    """
    def __init__(self, stackedWidget):
        QWidget.__init__(self, stackedWidget)
        self.curIndex = None
        self.timeline = QTimeLine()
        self.timeline.setDuration(333)
        self.timeline.finished.connect(self.hide)
        self.timeline.valueChanged.connect(self.animate)
        stackedWidget.currentChanged.connect(self.start)
        self.hide()
    
    def start(self, index):
        if self.curIndex is not None:
            stack = self.parent()
            old, new = stack.widget(self.curIndex), stack.widget(index)
            if old and new:
                self.old_pixmap = QPixmap(new.size())
                old.render(self.old_pixmap)
                self.pixmap_opacity = 1.0
                self.resize(new.size())
                self.timeline.start()
                self.raise_()
                self.show()
        self.curIndex = index
        
    def paintEvent(self, ev):
        painter = QPainter()
        painter.begin(self)
        painter.setOpacity(self.pixmap_opacity)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.end()
        
    def animate(self, value):
        self.pixmap_opacity = 1.0 - value
        self.repaint()


# some handy "static" functions
def promptText(parent, message, title = None, text="", rx=None, help=None):
    """
    Prompts for a text. Returns None on cancel, otherwise the input string.
    rx = if given, regexp string that the input must validate against
    help = if given, the docbook id in the help menu handbook.
    """
    d = KDialog(parent)
    buttons = KDialog.Ok | KDialog.Cancel
    if help:
        buttons |= KDialog.Help
        d.setHelp(help)
    d.setButtons(KDialog.ButtonCode(buttons))
    if title:
        d.setCaption(title)
    v = KVBox()
    v.setSpacing(4)
    d.setMainWidget(v)
    QLabel(message, v)
    edit = KLineEdit(v)
    if rx:
        edit.setValidator(QRegExpValidator(QRegExp(rx), edit))
    edit.setText(text)
    d.show()
    edit.setFocus()
    if d.exec_():
        return edit.text()


# utility functions used by above classes:
def isexe(path):
    """
    Return path if it is an executable file, otherwise False
    """
    return os.access(path, os.X_OK) and path

def findexe(filename):
    """
    Look up a filename in the system PATH, and return the full
    path if it can be found. If the path is absolute, return it
    unless it is not an executable file.
    """
    if os.path.isabs(os.path.expanduser(filename)):
        return isexe(os.path.expanduser(filename))
    for p in os.environ.get("PATH", os.defpath).split(os.pathsep):
        if isexe(os.path.join(p, filename)):
            return os.path.join(p, filename)
    return False

