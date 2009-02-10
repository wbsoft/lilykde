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
Expand Manager, manages expansions.
"""
import re, sip

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.ktexteditor import KTextEditor

from frescobaldi_app.widgets import promptText
from frescobaldi_app.mainapp import lazy

def config():
    return KGlobal.config().group("expand manager")

def onSignal(obj, signalName, shot=False):
    """ decorator to attach a function to a Qt signal """
    def decorator(func):
        if shot:
            QObject.connect(obj, SIGNAL(signalName), lambda *args:
                QTimer.singleShot(0, lambda: func(*args)))
        else:        
            QObject.connect(obj, SIGNAL(signalName), func)
        return func
    return decorator
    

class ExpandManager(object):
    def __init__(self, mainwin):
        self.mainwin = mainwin
        self.expansions = KConfig("expansions", KConfig.NoGlobals, "appdata")
        
    def expand(self):
        """
        Reads the last word in the current document. If it is not
        an expansion, open the expansion dialog. If the string matches
        multiple possible expansions, also open the dialog with the matching
        expansions shown.
        """
        doc = self.mainwin.currentDocument()
        cursor = doc.view.cursorPosition()
        lastWord = re.split("\W+",
            doc.line()[:cursor.column()])[-1]
        
        if lastWord and self.expansionExists(lastWord):
            # delete entered expansion name
            begin = KTextEditor.Cursor(cursor)
            begin.setColumn(begin.column() - len(lastWord))
            doc.doc.removeText(KTextEditor.Range(begin, cursor))
            # write the expansion
            self.doExpand(lastWord)
            return
        # open dialog and let the user choose
        self.expansionDialog().show()
        
    @lazy
    def expansionDialog(self):
        return ExpansionDialog(self)

    def expansionExists(self, name):
        return (self.expansions.hasGroup(name) and
                self.expansions.group(name).hasKey("Name"))

    def expansionsList(self):
        """
        Return list of all defined shortcuts.
        """
        return [name for name in self.expansions.groupList()
                     if self.expansions.group(name).hasKey("Name")]
                     
    def doExpand(self, expansion):
        """
        Perform the given expansion, must exist.
        """
        doc = self.mainwin.currentDocument()
        
        group = self.expansions.group(expansion)
        text = unicode(group.readEntry("Text", ""))
        
        # where to insert the text:
        cursor = doc.view.cursorPosition()
        newcursor = False
        # "(|)" is the place to position the cursor after inserting
        if "(|)" in text:
            col = cursor.column()
            line = cursor.line()
            t1, t2 = text.split("(|)", 1)
            if "\n" in t1:
                line += t1.count("\n")
                col = len(t1) - t1.rfind("\n") - 1
            else:
                col += len(t1)
            text = t1 + t2
            newcursor = KTextEditor.Cursor(line, col)
        # re-indent the text:
        indent = re.match(r'\s*', doc.line()[:cursor.column()]).group()
        text = text.replace('\n' , '\n' + indent)
        doc.doc.insertText(cursor, text)
        if newcursor:
            doc.view.setCursorPosition(newcursor)
    

class ExpansionDialog(KDialog):
    def __init__(self, manager):
        self.manager = manager
        KDialog.__init__(self, manager.mainwin)
        self.setCaption(i18n("Expansion Manager"))
        self.setButtons(KDialog.ButtonCode(
            KDialog.Ok | KDialog.Close | KDialog.User1 | KDialog.User2 ))
        self.setButtonGuiItem(KDialog.User1, KStandardGuiItem.remove())
        self.setButtonGuiItem(KDialog.User2, KStandardGuiItem.add())
        QObject.connect(self, SIGNAL("closeClicked()"), self.reject)
        self.setDefaultButton(KDialog.Ok)
        
        layout = QVBoxLayout(self.mainWidget())
        
        search = KTreeWidgetSearchLine()
        search.setClickMessage(i18n("Search..."))
        layout.addWidget(search)
        
        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)
        layout.addWidget(splitter)

        tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.setHeaderLabels((i18n("Shortcut"), i18n("Description")))
        tree.setRootIsDecorated(False)
        search.setTreeWidget(tree)
        splitter.addWidget(tree)
        
        edit = QTextEdit()
        edit.setFontFamily("monospace")
        edit.setAcceptRichText(False)
        edit.item = None
        edit.dirty = False
        splitter.addWidget(edit)
        
        self.searchLine = search
        self.treeWidget = tree
        self.edit = edit
        
        self.restoreDialogSize(config())
        
        expansions = self.manager.expansions
        
        def makeItem(name, description):
            item = QTreeWidgetItem(tree)
            item.groupName = name
            item.setFont(0, QFont("monospace"))
            item.setText(0, name)
            item.setText(1, description)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            return item
        
        def setCurrent(item):
            item.setSelected(True)
            updateSelection()
            tree.setCurrentItem(item)
            tree.scrollToItem(item)
            

        # load the expansions
        for groupName in sorted(self.manager.expansions.groupList()):
            group = expansions.group(groupName)
            description = group.readEntry("Name", "")
            if description:
                makeItem(groupName, description)

        tree.sortByColumn(1, Qt.AscendingOrder)
        tree.setSortingEnabled(True)
        
        @onSignal(self, "user1Clicked()")
        def removeButton():
            items = tree.selectedItems()
            if items and not items[0].isHidden():
                item = items[0]
                index = tree.indexOfTopLevelItem(item)
                if index + 1 == tree.topLevelItemCount():
                    index = 0
                expansions.deleteGroup(items[0].groupName)
                sip.delete(items[0])
                if index:
                    setCurrent(tree.topLevelItem(index))
                
        @onSignal(self, "user2Clicked()")
        def addButton():
            num = 0
            name = "new"
            while self.manager.expansionExists(name):
                num += 1
                name = "new%d" % num
            description = i18n("New Item")
            if num:
                description += " %d" % num
            expansions.group(name).writeEntry("Name", description)
            item = makeItem(name, description)
            setCurrent(item)
            tree.editItem(item, 0)
            
        @onSignal(edit, "textChanged()")
        def textChanged():
            edit.dirty = True

        @onSignal(search, "textChanged(QString)")
        def checkMatch(text):
            items = tree.findItems(text, Qt.MatchExactly, 0)
            if len(items) == 1:
                setCurrent(items[0])
                
        @onSignal(tree, "itemSelectionChanged()")
        def updateSelection():
            items = tree.selectedItems()
            if items:
                self.saveEditIfNecessary()
                edit.setText(expansions.group(
                    items[0].text(0)).readEntry("Text", ""))
                edit.item = items[0]
                edit.dirty = False
        
        @onSignal(tree, "itemChanged(QTreeWidgetItem*, int)", shot=True)
        def itemChanged(item, column):
            if column == 1:
                group = expansions.group(item.text(0))
                if item.text(1):
                    group.writeEntry("Name", item.text(1))
                    setCurrent(item)
                else:
                    KMessageBox.error(self.manager.mainwin, i18n(
                        "Please don't leave the description empty."))
                    item.setText(1, group.readEntry("Name", ""))
                    tree.editItem(item, 1)
            elif item.groupName != item.text(0):
                items = [i for i in self.items() if i.text(0) == item.text(0)]
                if len(items) > 1:
                    KMessageBox.error(self.manager.mainwin, i18n(
                        "Another expansion already uses this name.\n\n"
                        "Please use a different name."))
                    item.setText(0, item.groupName)
                    tree.editItem(item, 0)
                elif not re.match(r"\w+$", unicode(item.text(0))):
                    KMessageBox.error(self.manager.mainwin, i18n(
                        "Please only use letters, numbers and the underscore "
                        "character in the expansion name."))
                    item.setText(0, item.groupName)
                    tree.editItem(item, 0)
                else:
                    group = expansions.group(item.text(0))
                    group.writeEntry("Name", item.text(1))
                    group.writeEntry("Text", edit.toPlainText())
                    expansions.deleteGroup(item.groupName)
                    item.groupName = item.text(0)
                    setCurrent(item)
                
    def items(self):
        """ Return an iterator over all the items in our dialog. """
        return (self.treeWidget.topLevelItem(i)
                for i in range(self.treeWidget.topLevelItemCount()))
    
    def saveEditIfNecessary(self):
        if self.edit.dirty and self.edit.item:
            self.manager.expansions.group(self.edit.item.text(0)).writeEntry(
                "Text", self.edit.toPlainText())
            self.edit.dirty = False
            
    def show(self):
        KDialog.show(self)
        self.searchLine.setFocus()
        
    def done(self, result):
        self.saveEditIfNecessary()
        self.manager.expansions.sync()
        if result:
            items = self.treeWidget.selectedItems() or self.items()
            items = [item for item in items if not item.isHidden()]
            if len(items) == 1:
                expansion = items[0].text(0)
                self.manager.doExpand(expansion)
        self.saveDialogSize(config())
        KDialog.done(self, result)
