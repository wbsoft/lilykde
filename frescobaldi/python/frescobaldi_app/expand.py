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
import re

from PyQt4.QtCore import QObject, QTimer, Qt, SIGNAL
from PyQt4.QtGui import (
    QFont, QSplitter, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout)

from PyKDE4.kdecore import KConfig, KGlobal, i18n
from PyKDE4.kdeui import (
    KDialog, KKeySequenceWidget, KMessageBox, KShortcut, KStandardGuiItem,
    KTreeWidgetSearchLine, KVBox)
from PyKDE4.ktexteditor import KTextEditor

import ly.parse, ly.pitch

from kateshell.app import cacheresult
from kateshell.shortcut import ShortcutClient
from frescobaldi_app.highlight import LilyPondHighlighter


class ExpandManager(ShortcutClient):
    def __init__(self, mainwin):
        self.mainwin = mainwin
        self.shortcuts = mainwin.expansionShortcuts
        ShortcutClient.__init__(self, self.shortcuts)
        self.expansions = KConfig("expansions", KConfig.NoGlobals, "appdata")
        # delete shortcut actions that do not exist here anymore
        mainwin.expansionShortcuts.shakeHands(self.expansionsList())
        
    def actionTriggered(self, name):
        return self.doExpand(name)
        
    def populateAction(self, action):
        action.setText(self.description(action.objectName()))
        
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
            # write the expansion
            self.doExpand(lastWord, remove=KTextEditor.Range(begin, cursor))
            return
        # open dialog and let the user choose
        self.expansionDialog().show()
        
    @cacheresult
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

    def description(self, name):
        """
        Return the description for the expansion name.
        """
        return self.expansions.group(name).readEntry("Name", "")
    
    def doExpand(self, expansion, remove=None):
        """
        Perform the given expansion, must exist.
        if remove is given, use doc.replaceText to replace that Range.
        """
        doc = self.mainwin.currentDocument()
        
        group = self.expansions.group(expansion)
        text = group.readEntry("Text", "")
        
        # where to insert the text:
        cursor = remove and remove.start() or doc.view.cursorPosition()
        
        # translate pitches (marked by @)
        # find the current language
        lang = ly.parse.documentLanguage(doc.textToCursor(cursor))
        writer = ly.pitch.pitchWriter[lang or "nederlands"]
        reader = ly.pitch.pitchReader["nederlands"]
        
        def repl(matchObj):
            pitch = matchObj.group(1)
            result = reader(pitch)
            if result:
                note, alter = result
                return writer(note, alter)
            return matchObj.group()
            
        text = re.sub(r"@([a-z]+)(?!\.)", repl, text)
            
        # if the expansion starts with a backslash and the character just 
        # before the cursor is also a backslash, don't repeat it.
        if (text.startswith("\\") and cursor.column() > 0
            and doc.line()[cursor.column()-1] == "\\"):
            text = text[1:]
        
        doc.manipulator().insertTemplate(text, cursor, remove)

    def addExpansion(self, text = None):
        """ Open the expansion dialog with a new expansion given in text. """
        dlg = self.expansionDialog()
        dlg.show()
        dlg.addItem(text)


class ExpansionDialog(KDialog):
    def __init__(self, manager):
        self.manager = manager
        KDialog.__init__(self, manager.mainwin)
        self.setCaption(i18n("Expansion Manager"))
        self.setButtons(KDialog.ButtonCode(
            KDialog.Help |
            KDialog.Ok | KDialog.Close | KDialog.User1 | KDialog.User2 ))
        self.setButtonGuiItem(KDialog.User1, KStandardGuiItem.remove())
        self.setButtonGuiItem(KDialog.User2, KStandardGuiItem.add())
        self.closeClicked.connect(self.reject)
        self.setDefaultButton(KDialog.Ok)
        self.setHelp("expand")
        
        layout = QVBoxLayout(self.mainWidget())
        layout.setContentsMargins(0, 0, 0, 0)
        
        search = KTreeWidgetSearchLine()
        search.setClickMessage(i18n("Search..."))
        layout.addWidget(search)
        
        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)
        layout.addWidget(splitter)

        tree = QTreeWidget()
        tree.setColumnCount(3)
        tree.setHeaderLabels((i18n("Name"), i18n("Description"), i18n("Shortcut")))
        tree.setRootIsDecorated(False)
        tree.setAllColumnsShowFocus(True)
        search.setTreeWidget(tree)
        splitter.addWidget(tree)
        
        box = KVBox()
        splitter.addWidget(box)
        
        key = KKeySequenceWidget(box)
        key.layout().setContentsMargins(0, 0, 0, 0)
        key.layout().insertStretch(0, 1)
        key.setEnabled(False)
        
        edit = QTextEdit(box)
        edit.setAcceptRichText(False)
        edit.setStyleSheet("QTextEdit { font-family: monospace; }")
        edit.item = None
        edit.dirty = False
        ExpandHighlighter(edit.document())
        
        # whats this etc.
        tree.setWhatsThis(i18n(
            "This is the list of defined expansions.\n\n"
            "Click on a row to see or change the associated text. "
            "Doubleclick a shortcut or its description to change it. "
            "You can also press F2 to edit the current shortcut.\n\n"
            "Use the buttons below to add or remove expansions.\n\n"
            "There are two ways to use the expansion: either type the "
            "shortcut in the text and then call the Expand function, or "
            "just call the Expand function (default shortcut: Ctrl+.), "
            "choose the expansion from the list and press Enter or click Ok."
            ))
            
        edit.setWhatsThis(
            "<html><head><style type='text/css'>"
            "td.short {{ font-family: monospace; font-weight: bold; }}"
            "</style></head><body>"
            "<p>{0}</p><table border=0 width=300 cellspacing=2><tbody>"
            "<tr><td class=short align=center>(|)</td><td>{1}</td></tr>"
            "<tr><td class=short align=center>@</td><td>{2}</td></tr>"
            "</tbody></table></body></html>".format(
            i18n("This is the text associated with the selected shortcut. "
                 "Some characters have special meaning:"),
            i18n("Place the cursor on this spot."),
            i18n("Translate the following pitch."),
            ))
        
        self.searchLine = search
        self.treeWidget = tree
        self.key = key
        self.edit = edit
        
        self.restoreDialogSize(config())
        
        # load the expansions
        for name in sorted(self.manager.expansionsList()):
            self.createItem(name, self.manager.description(name),
            self.manager.shortcuts.shortcut(name))

        tree.sortByColumn(1, Qt.AscendingOrder)
        tree.setSortingEnabled(True)
        tree.resizeColumnToContents(1)
        
        self.user1Clicked.connect(self.removeItem)
        self.user2Clicked.connect(self.addItem)
        edit.textChanged.connect(self.editChanged)
        search.textChanged.connect(self.checkMatch)
        tree.itemSelectionChanged.connect(self.updateSelection)
        tree.itemChanged.connect(self.itemChanged, Qt.QueuedConnection)
        key.keySequenceChanged.connect(self.keySequenceChanged)
    
    def createItem(self, name, description, key=None):
        """ Create a new item, if key is given it should be a KShortcut. """
        item = QTreeWidgetItem(self.treeWidget)
        item.groupName = name
        item.setFont(0, QFont("monospace"))
        item.setText(0, name)
        item.setText(1, description)
        if key:
            item.setText(2, key.toList()[0].toString())
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
        return item
    
    def addItem(self, text=None):
        """
        Add a new empty item (or use the text in the edit if no previous item
        is selected). The new item becomes the selected item.
        If text is given, put it in the text edit widget.
        """
        num = 0
        name = "new"
        while self.manager.expansionExists(name):
            num += 1
            name = "new{0}".format(num)
        description = i18n("New Item")
        if num:
            description += " {0}".format(num)
        self.manager.expansions.group(name).writeEntry("Name", description)
        self.searchLine.clear() # otherwise strange things happen...
        item = self.createItem(name, description)
        if self.edit.item is None:
            # the user might have typed/pasted text in the edit already,
            # intending to add a new expansion.
            self.edit.item = item
            self.saveEditIfNecessary()
        self.setCurrentItem(item)
        self.treeWidget.setFocus()
        self.treeWidget.editItem(item, 0)
        self.edit.dirty = True # so that our (empty) text gets saved
        if text is not None:
            self.edit.setText(text)
    
    def removeItem(self):
        """ Remove the current item. """
        item = self.currentItem()
        if item:
            index = self.treeWidget.indexOfTopLevelItem(item)
            setIndex = index + 1 < self.treeWidget.topLevelItemCount()
            self.manager.expansions.deleteGroup(item.groupName)
            self.manager.shortcuts.removeShortcut(item.groupName)
            self.treeWidget.takeTopLevelItem(index)
            if setIndex:
                self.setCurrentItem(self.treeWidget.topLevelItem(index))
    
    def items(self):
        """ Return an iterator over all the items in our dialog. """
        return (self.treeWidget.topLevelItem(i)
                for i in range(self.treeWidget.topLevelItemCount()))
    
    def currentItem(self):
        """ Returns the currently selected item, if any. """
        items = self.treeWidget.selectedItems()
        if items and not items[0].isHidden():
            return items[0]
            
    def setCurrentItem(self, item):
        """ Sets the item to be the current and selected item. """
        item.setSelected(True)
        self.updateSelection()
        self.treeWidget.setCurrentItem(item)
        self.treeWidget.scrollToItem(item)

    def checkMatch(self, text):
        """ Called when the user types in the search line. """
        items = self.treeWidget.findItems(text, Qt.MatchExactly, 0)
        if len(items) == 1:
            self.setCurrentItem(items[0])
                
    def updateSelection(self):
        """ (Internal use) update the edit widget when selection changes. """
        items = self.treeWidget.selectedItems()
        self.saveEditIfNecessary()
        if items:
            name = items[0].text(0)
            group = self.manager.expansions.group(name)
            self.edit.setPlainText(group.readEntry("Text", ""))
            self.edit.item = items[0]
            self.edit.dirty = False
            # key shortcut widget
            self.key.setEnabled(True)
            self.manager.keyLoadShortcut(self.key, name)
        else:
            self.edit.item = None
            self.edit.clear()
            self.key.clearKeySequence()
            self.key.setEnabled(False)
    
    def itemChanged(self, item, column):
        """ Called when the user has edited an item. """
        if column == 0 and item.groupName != item.text(0):
            # The user has changed the mnemonic
            items = [i for i in self.items() if i.text(0) == item.text(0)]
            if len(items) > 1:
                KMessageBox.error(self.manager.mainwin, i18n(
                    "Another expansion already uses this name.\n\n"
                    "Please use a different name."))
                item.setText(0, item.groupName)
                self.treeWidget.editItem(item, 0)
            elif not re.match(r"\w+$", item.text(0)):
                KMessageBox.error(self.manager.mainwin, i18n(
                    "Please only use letters, numbers and the underscore "
                    "character in the expansion name."))
                item.setText(0, item.groupName)
                self.treeWidget.editItem(item, 0)
            else:
                # apply the changed mnemonic
                old, new = item.groupName, item.text(0)
                group = self.manager.expansions.group(new)
                group.writeEntry("Name", item.text(1))
                group.writeEntry("Text", self.manager.expansions.group(old).readEntry("Text", ""))
                self.manager.expansions.deleteGroup(old)
                # move the shortcut
                s = self.manager.shortcuts
                if s.shortcut(old):
                    s.setShortcut(new, s.shortcut(old))
                s.removeShortcut(old)
                item.groupName = item.text(0)
                self.treeWidget.scrollToItem(item)
        elif column == 1:
            group = self.manager.expansions.group(item.text(0))
            if item.text(1):
                group.writeEntry("Name", item.text(1))
                self.treeWidget.scrollToItem(item)
                self.treeWidget.resizeColumnToContents(1)
            else:
                KMessageBox.error(self.manager.mainwin, i18n(
                    "Please don't leave the description empty."))
                item.setText(1, group.readEntry("Name", ""))
                self.treeWidget.editItem(item, 1)
        elif column == 2:
            # User should not edit textual representation of shortcut
            item.setText(2, self.shortcutText(item.text(0)))
    
    def editChanged(self):
        """ Marks our edit view as changed. """
        self.edit.dirty = True

    def saveEditIfNecessary(self):
        """ (Internal use) save the edit if it has changed. """
        if self.edit.dirty and self.edit.item:
            self.manager.expansions.group(self.edit.item.text(0)).writeEntry(
                "Text", self.edit.toPlainText())
            self.edit.dirty = False
    
    def keySequenceChanged(self, seq):
        """ Called when the user has changed the keyboard shortcut. """
        item = self.currentItem()
        if item:
            self.manager.keyApplyShortcut(self.key, item.text(0), seq)
            item.setText(2, seq.toString())
            self.updateShortcuts()
        
    def updateShortcuts(self):
        """
        Checks if shortcuts have disappeared by stealing them from other
        keyboard shortcut dialogs.  And initialize the shortcut button to
        check for collisions.
        """
        names = self.manager.shortcuts.shortcuts()
        for item in self.items():
            if item.text(2) and item.text(0) not in names:
                item.setText(2, '')
            elif item.text(0) in names:
                item.setText(2, self.shortcutText(item.text(0)))
        item = self.currentItem()
        if item:
            self.manager.keyLoadShortcut(self.key, item.text(0))
        self.manager.keySetCheckActionCollections(self.key)
    
    def show(self):
        self.updateShortcuts()
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


class ExpandHighlighter(LilyPondHighlighter):
    """
    LilyPond Highlighter that also highlights some non-LilyPond input that
    the expander uses.
    """
    def highlightBlock(self, text):
        matches = []
        def repl(m):
            matches.append((m.start(), len(m.group())))
            return ' ' * len(m.group())
        text = re.compile(r"\(\|\)|@").sub(repl, text)
        super(ExpandHighlighter, self).highlightBlock(text)
        for start, count in matches:
            self.setFormat(start, count, self.formats['special'])


def config():
    return KGlobal.config().group("expand manager")
