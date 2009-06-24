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
Exception dialog for unhandled Python exceptions
(which are bugs in our program).
"""

import traceback

from PyQt4.QtCore import QObject, SIGNAL
from PyQt4.QtGui import QLabel, QTextBrowser, QTextCursor, QVBoxLayout
from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import KBugReport, KDialog, KIcon, KLineEdit, KTextEdit

class ExceptionDialog(KDialog):
    
    def __init__(self, app, exctype, excvalue, exctb):
        KDialog.__init__(self, app.mainwin)
        self.app = app
        self.tbshort = ''.join(traceback.format_exception_only(exctype, excvalue))
        self.tbfull = ''.join(traceback.format_exception(exctype, excvalue, exctb))
        
        l = QVBoxLayout(self.mainWidget())
        l.addWidget(QLabel("<b>%s</b>" % i18n(
            "An internal error has occurred:")))
        b = QTextBrowser()
        l.addWidget(b)
        self.setCaption(self.tbshort)
        b.setText(self.tbfull)
        self.setButtons(KDialog.ButtonCode(
            KDialog.User1 | KDialog.Close))
        self.setButtonIcon(KDialog.User1, KIcon("tools-report-bug"))
        self.setButtonText(KDialog.User1, i18n("Report Bug..."))
        QObject.connect(self, SIGNAL("user1Clicked()"), self.reportBug)
        self.resize(600,300)
        self.exec_()

    def reportBug(self):
        self.accept()
        bug = KBugReport()
        subject = bug.findChild(KLineEdit)
        if subject:
            subject.setText("[v%s] %s" % (self.app.version(), self.tbshort))
        bug.setMessageBody("%s\n%s\n\n" % (self.tbfull,
            i18n("Optionally describe what you were doing below:")))
        body = bug.findChild(KTextEdit)
        if body:
            body.setFocus()
            body.moveCursor(QTextCursor.End)
        bug.exec_()


def showException(parent, exctype, excvalue, exctb):
    ExceptionDialog(parent, exctype, excvalue, exctb)

