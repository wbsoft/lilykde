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
Dialog to download new binary versions of LilyPond
"""

import os, re

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

from frescobaldi_app.lilydoc import HtmlLoader


class LilyPondDownloadDialog(KDialog):
    def __init__(self, info):
        """info is a LilyPondInfoDialog (see settings.py)"""
        KDialog.__init__(self, info)
        self.setButtons(KDialog.ButtonCode(
            KDialog.Help | KDialog.Ok | KDialog.Cancel))
        layout = QGridLayout()
        self.mainWidget().setLayout(layout)
        
        self.setButtonText(KDialog.Ok, i18n("Start Download"))
        self.setButtonIcon(KDialog.Ok, KIcon("download"))
        self.setCaption(i18n("Download LilyPond"))
        
        l = QLabel(i18n(
            "With this tool you can download packaged binary releases "
            "of LilyPond for your operating system."))
        l.setWordWrap(True)
        layout.addWidget(l, 0, 0, 1, 2)
        
        b = self.baseUrl = QComboBox()
        b.setEditable(True)
        b.addItems(['http://download.linuxaudio.org/lilypond/binaries/'])
        b.setCurrentIndex(0)
        
        l = QLabel(i18n("Download from:"))
        l.setBuddy(b)
        layout.addWidget(l, 1, 0)
        layout.addWidget(b, 1, 1)
        
        m = self.machineType = QComboBox()
        items = [
            'linux-x86',
            'linux-64',
            'linux-ppc',
            'freebsd-x86',
            'freebsd-64',
            'darwin-x86',
            'darwin-ppc',
            ]
        m.addItems(items)
        
        # default for machine
        platform, machine = os.uname()[0::4]
        if '64' in machine:
            machine = '64'
        elif '86' in machine:
            machine = 'x86'
        elif 'ower' in machine or 'ppc' in machine:
            machine = 'ppc'
        mtype = platform.lower() + '-' + machine
        if mtype in items:
            m.setCurrentIndex(items.index(mtype))
        m.currentIndexChanged.connect(self.downloadVersions)

        l = QLabel(i18n("Machine type:"))
        l.setBuddy(m)
        layout.addWidget(l, 2, 0)
        layout.addWidget(m, 2, 1)
        
        v = self.lilyVersion = QComboBox()
        
        l = QLabel(i18n("Version:"))
        l.setBuddy(v)
        layout.addWidget(l, 3, 0)
        layout.addWidget(v, 3, 1)
        
        d = self.installDest = KUrlRequester()
        d.setMode(KFile.Mode(KFile.Directory | KFile.LocalOnly))
        d.setPath('~/lilypond_bin/')
        
        l = QLabel(i18n("Install into:"))
        l.setBuddy(d)
        layout.addWidget(l, 4, 0)
        layout.addWidget(d, 4, 1)
        
        s = self.status = QLabel()
        layout.addWidget(s, 5, 0, 1, 2)
        
        p = self.progress = QProgressBar()
        layout.addWidget(p, 6, 0, 1, 2)
        
        self.downloadVersions()
        
    def downloadVersions(self):
        directory = self.baseUrl.currentText()
        if not directory.endswith('/'):
            directory += '/'
        directory += self.machineType.currentText()
        directory += '/'
        self.directory = directory
        self.loader = HtmlLoader(directory)
        self.status.setText(i18n("Downloading directory listing..."))
        self.progress.setRange(0, 0)
        self.loader.done.connect(self.versionsDownloaded)
        
    def versionsDownloaded(self):
        self.progress.setRange(0, 100)
        self.progress.reset()
        self.status.setText('')
        if self.loader.error():
            return
        
        versions = {}
        versionStrings = {}
        for m in re.finditer(r'\bhref="(lilypond-.*?\.sh)"', self.loader.html()):
            fileName = m.group(1)
            m = re.search(r'(\d+(\.\d+)+)(-(\d+))?', fileName)
            if m:
                versionStrings[fileName] = m.group()
                ver, build = m.group(1, 4)
                version = (tuple(map(int, re.findall(r'\d+', ver))), int(build or 0))
                versions[fileName] = version
        
        files = versions.keys()
        files.sort(key=versions.get)
        
        # determine last stable and development:
        stable, development = None, None
        for f in files[::-1]:
            if versions[f][0][1] & 1:
                if not development:
                    development = f
            elif not stable:
                stable = f
            if stable and development:
                break
        
        # add the versions
        self.lilyVersion.clear()
        items = []
        if stable:
            self.lilyVersion.addItem(i18n("Latest Stable Version (%1)",
                versionStrings[stable]))
            items.append(stable)
            self.lilyVersion.setCurrentIndex(0)
        if development:
            self.lilyVersion.addItem(i18n("Latest Development Version (%1)",
                versionStrings[development]))
            self.lilyVersion.setCurrentIndex(len(items))
            items.append(development)
        for f in files:
            self.lilyVersion.addItem(versionStrings[f])
            items.append(f)
            
        self.items = items


            
        
        
    
        