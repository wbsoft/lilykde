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


from PyQt4.QtCore import QObject, Qt, QUrl, SIGNAL
from PyQt4.QtGui import QToolBar, QVBoxLayout, QWidget
from PyQt4.QtWebKit import QWebView

from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KStandardGuiItem


class LilyDoc(QWidget):
    def __init__(self, tool):
        QWidget.__init__(self)
        self.mainwin = tool.mainwin
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toolBar = QToolBar(self)
        layout.addWidget(self.toolBar)
        self.view = QWebView(self)
        layout.addWidget(self.view)
        
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        g = KStandardGuiItem.back()
        self.back = self.toolBar.addAction(g.icon(), g.text())
        self.back.setEnabled(False)
        g = KStandardGuiItem.forward()
        self.forward = self.toolBar.addAction(g.icon(), g.text())
        self.forward.setEnabled(False)
        
        # signals
        QObject.connect(self.view, SIGNAL("urlChanged(QUrl)"), self.slotUrlChanged)
        QObject.connect(self.back, SIGNAL("triggered()"), self.view.back)
        QObject.connect(self.forward, SIGNAL("triggered()"), self.view.forward)
        # load initial view.
        self.view.load(QUrl("http://lilypond.org/doc"))


    def slotUrlChanged(self, url):
        self.back.setEnabled(self.view.history().canGoBack())
        self.forward.setEnabled(self.view.history().canGoForward())
        