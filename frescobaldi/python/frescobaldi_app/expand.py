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

from PyQt4.QtCore import QObject, QString, QTimer, Qt, QVariant, SIGNAL
from PyQt4.QtGui import (
    QFont, QKeySequence, QSplitter, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout)

from PyKDE4.kdecore import KConfig, KGlobal, i18n
from PyKDE4.kdeui import (
    KDialog, KKeySequenceWidget, KMessageBox, KShortcut, KStandardGuiItem,
    KTreeWidgetSearchLine, KVBox)
from PyKDE4.ktexteditor import KTextEditor

import ly.parse, ly.pitch

from kateshell.app import lazymethod
from frescobaldi_app.highlight import LilyPondHighlighter

def config():
    return KGlobal.config().group("expand manager")

def onSignal(obj, signalName, shot=False):
    """
    Decorator to attach a function to a Qt signal.
    If shot == True, the function is called after the event queue
    has been processed, using QTimer.singleShot.
    """
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
        
    @lazymethod
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
        return unicode(self.expansions.group(name).readEntry("Name", QVariant("")).toString())
    
    def doExpand(self, expansion, remove=None):
        """
        Perform the given expansion, must exist.
        if remove is given, use doc.replaceText to replace that Range.
        """
        doc = self.mainwin.currentDocument()
        
        group = self.expansions.group(expansion)
        text = unicode(group.readEntry("Text", QVariant("")).toString())
        
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
        QObject.connect(self, SIGNAL("closeClicked()"), self.reject)
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
            "td.short { font-family: monospace; font-weight: bold; }"
            "</style></head><body>"
            "<p>%s</p><table border=0 width=300 cellspacing=2><tbody>"
            "<tr><td class=short align=center>(|)</td><td>%s</td></tr>"
            "<tr><td class=short align=center>@</td><td>%s</td></tr>"
            "</tbody></table></body></html>"
            % (i18n(
                "This is the text associated with the selected shortcut. "
                "Some characters have special meaning:"),
            i18n("Place the cursor on this spot."),
            i18n("Translate the following pitch."),
            ))
        
        self.searchLine = search
        self.treeWidget = tree
        self.key = key
        self.edit = edit
        
        self.restoreDialogSize(config())
        
        expansions = self.manager.expansions
        
        # load the expansions
        for groupName in sorted(expansions.groupList()):
            group = expansions.group(groupName)
            description = group.readEntry("Name", QVariant("")).toString()
            if description:
                self.createItem(groupName, description)

        tree.sortByColumn(1, Qt.AscendingOrder)
        tree.setSortingEnabled(True)
        tree.resizeColumnToContents(1)
        
        @onSignal(self, "user1Clicked()")
        def removeButton():
            item = self.currentItem()
            if item:
                index = tree.indexOfTopLevelItem(item)
                setIndex = index + 1 < tree.topLevelItemCount()
                expansions.deleteGroup(item.groupName)
                self.manager.mainwin.expansionShortcuts.removeShortcut(item.groupName)
                tree.takeTopLevelItem(index)
                if setIndex:
                    self.setCurrentItem(tree.topLevelItem(index))
                
        @onSignal(self, "user2Clicked()")
        def addButton():
            self.addItem()
        
        @onSignal(edit, "textChanged()")
        def textChanged():
            edit.dirty = True

        @onSignal(search, "textChanged(QString)")
        def checkMatch(text):
            items = tree.findItems(text, Qt.MatchExactly, 0)
            if len(items) == 1:
                self.setCurrentItem(items[0])
                
        @onSignal(tree, "itemSelectionChanged()")
        def updateSelection():
            self.updateSelection()
        
        @onSignal(tree, "itemChanged(QTreeWidgetItem*, int)", shot=True)
        def itemChanged(item, column):
            if column == 0 and item.groupName != item.text(0):
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
                    # the mnemonic has changed
                    old, new = item.groupName, item.text(0)
                    group = expansions.group(new)
                    group.writeEntry("Name", item.text(1))
                    group.writeEntry("Text",
                        expansions.group(old).readEntry("Text", QVariant("")).toString())
                    expansions.deleteGroup(old)
                    # shortcut
                    s = self.manager.mainwin.expansionShortcuts
                    s.setShortcut(new, s.shortcut(old))
                    s.removeShortcut(old)
                    item.groupName = item.text(0)
                    tree.scrollToItem(item)
            elif column == 1:
                group = expansions.group(item.text(0))
                if item.text(1):
                    group.writeEntry("Name", item.text(1))
                    tree.scrollToItem(item)
                else:
                    KMessageBox.error(self.manager.mainwin, i18n(
                        "Please don't leave the description empty."))
                    item.setText(1, group.readEntry("Name", QVariant("")).toString())
                    tree.editItem(item, 1)
            elif column == 2:
                # User should not edit textual representation of shortcut
                key = self.manager.mainwin.expansionShortcuts.shortcut(item.text(0))
                item.setText(2, key and key.toList()[0].toString() or '')
        
        @onSignal(key, "keySequenceChanged (QKeySequence)")
        def keySequenceChanged(seq):
            item = self.currentItem()
            if item:
                manager.mainwin.expansionShortcuts.setShortcut(
                    item.text(0), KShortcut(seq))
                item.setText(2, seq.toString())
                key.applyStealShortcut()
        
    def createItem(self, name, description):
        item = QTreeWidgetItem(self.treeWidget)
        item.groupName = name
        item.setFont(0, QFont("monospace"))
        item.setText(0, name)
        item.setText(1, description)
        key = self.manager.mainwin.expansionShortcuts.shortcut(name)
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
            name = "new%d" % num
        description = i18n("New Item")
        if num:
            description += " %d" % num
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

    def updateSelection(self):
        """ (Internal use) update the edit widget when selection changes. """
        items = self.treeWidget.selectedItems()
        if items:
            self.saveEditIfNecessary()
            name = items[0].text(0)
            group = self.manager.expansions.group(name)
            self.edit.setPlainText(group.readEntry("Text", QVariant("")).toString())
            self.edit.item = items[0]
            self.edit.dirty = False
            # key shortcut widget
            key = self.manager.mainwin.expansionShortcuts.shortcut(name)
            self.key.setCheckActionCollections([
                    self.manager.mainwin.actionCollection(),
                    self.manager.mainwin.view().actionCollection(),
                    ])
            self.key.setEnabled(True)
            self.key.blockSignals(True)
            self.key.setKeySequence(key and key.toList()[0] or QKeySequence())
            self.key.blockSignals(False)
        else:
            self.key.setEnabled(False)
    
    def saveEditIfNecessary(self):
        """ (Internal use) save the edit if it has changed. """
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
        text = re.compile(r"\(\|\)|@").sub(repl, unicode(text))
        super(ExpandHighlighter, self).highlightBlock(text)
        for start, count in matches:
            self.setFormat(start, count, self.formats['special'])
