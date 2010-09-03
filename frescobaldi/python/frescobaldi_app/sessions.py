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
Code for managing editor sessions, inherits the base code from kateshell.
"""

from PyQt4.QtGui import QComboBox, QGridLayout, QLabel, QWidget
from PyKDE4.kdecore import i18n, KGlobal
from PyKDE4.kdeui import KIcon

import ly.version
import kateshell.sessions


class EditorDialog(kateshell.sessions.EditorDialog):
    def __init__(self, manager):
        super(EditorDialog, self).__init__(manager)
        page = QWidget(self)
        item = self.lilyPond = self.addPage(page, i18n("LilyPond"))
        item.setHeader(i18n("LilyPond-related settings"))
        item.setIcon(KIcon("run-lilypond"))
        
        layout = QGridLayout(page)
        
        l = QLabel(i18n("LilyPond version to use:"))
        ver = self.lilyVer = QComboBox()
        l.setBuddy(ver)
        l.setToolTip(i18n(
            "Here you can set a fixed LilyPond version to run on documents "
            "in this session.\n"
            "See What's This (Shift+F1) for more information."))
        l.setWhatsThis(i18n(
            "Here you can set a fixed LilyPond version to run on documents "
            "in this session.\n\n"
            "The LilyPond version selected here is run by default on your "
            "documents, and it's also used by the \"Insert Version\" command."))
        ver.setToolTip(l.toolTip())
        ver.setWhatsThis(l.whatsThis())
        layout.addWidget(l, 0, 0)
        layout.addWidget(ver, 0, 1)
        self.loadLilyPondVersions()
        
    def loadLilyPondVersions(self):
        """ Puts configured lilypond versions in our ComboBox. """
        conf = config("lilypond")
        paths = conf.readEntry("paths", ["lilypond"]) or ["lilypond"]
        default = conf.readEntry("default", "lilypond")
        
        # get all versions
        ver = dict((path, ly.version.LilyPondInstance(path).version())
                   for path in paths)
        paths.sort(key=ver.get)
        self._paths = paths
        self.lilyVer.addItem(i18n("Default"))
        self.lilyVer.addItems([format(ver[p]) for p in paths])
    
    def loadSessionDefaults(self):
        super(EditorDialog, self).loadSessionDefaults()
        self.lilyVer.setCurrentIndex(0)
        
    def loadSessionConfig(self, conf):
        super(EditorDialog, self).loadSessionConfig(conf)
        path = conf.readEntry('lilypond', '')
        try:
            index = self._paths.index(path) + 1
        except ValueError:
            index = 0
        self.lilyVer.setCurrentIndex(index)

    def saveSessionConfig(self, conf):
        super(EditorDialog, self).saveSessionConfig(conf)
        conf.writeEntry('lilypond', 
            ([''] + self._paths)[self.lilyVer.currentIndex()])


# Easily get our global config
def config(group):
    return KGlobal.config().group(group)
