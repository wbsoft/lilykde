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
import ly

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

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
        pass # TODO implement
        
    
    
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
