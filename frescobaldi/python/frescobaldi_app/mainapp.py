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

import os
from dbus.service import method

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kparts import KParts

import kateshell.app, kateshell.mainwindow

class MainApp(kateshell.app.MainApp):
    """ A Frescobaldi application instance """
    
    defaultEncoding = 'UTF-8'
    defaultHighlightingMode = "LilyPond"
    fileTypes = ["*.ly *.ily *.lyi|%s" % i18n("LilyPond files")]
    
    def __init__(self, servicePrefix):
        kateshell.app.MainApp.__init__(self, servicePrefix)
        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = self.serviceName + '/MainApp'

    def openUrl(self, url, encoding=None):
        #TODO: check whether URL is textedit URL
        d = kateshell.app.MainApp.openUrl(self, url, encoding)
        #TODO: if textedit URL, set cursor position
        return d

    @method("org.lilypond.TextEdit", in_signature='s', out_signature='b')
    def openTextEditUrl(self, url):
        """
        To be called by ktexteditservice (part of lilypond-kde4).
        Opens the specified textedit:// URL.
        """
        return bool(self.openUrl(url))

    def createMainWindow(self):
        """ use our own MainWindow """
        return MainWindow(self)


class MainWindow(kateshell.mainwindow.MainWindow):
    """ Our customized Frescobaldi MainWindow """
    def __init__(self, app):
        kateshell.mainwindow.MainWindow.__init__(self, app)
        
        KonsoleTool(self)
        

class KonsoleTool(kateshell.mainwindow.Tool):
    def __init__(self, mainwin):
        def konsoleWidgetFactory():
            return QWidget()
        kateshell.mainwindow.Tool.__init__(self, mainwin,
            "konsole", i18n("Konsole"), "terminal",
            dock=kateshell.mainwindow.Bottom,
            factory = konsoleWidgetFactory)
            

