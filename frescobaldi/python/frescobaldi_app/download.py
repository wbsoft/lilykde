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

import os, re, shutil

from PyQt4.QtCore import QObject, QProcess, Qt, SIGNAL
from PyQt4.QtGui import QComboBox, QGridLayout, QGroupBox, QLabel, QProgressBar
from PyKDE4.kdecore import KGlobal, KUrl, i18n
from PyKDE4.kdeui import KDialog, KGuiItem, KIcon, KMessageBox
from PyKDE4.kio import KFile, KIO, KUrlRequester

from frescobaldi_app.lilydoc import HtmlLoader

# parse version of a LilyPond package
_version_re = re.compile(r'(\d+(\.\d+)+)(-(\d+))?')


class LilyPondDownloadDialog(KDialog):
    def __init__(self, info):
        """info is a LilyPondInfoDialog (see settings.py)"""
        KDialog.__init__(self, info)
        self.info = info
        
        # local attributes
        self.job = None
        self.unpackJob = None
        
        self.setButtons(KDialog.ButtonCode(
            KDialog.Help | KDialog.Details | KDialog.Ok | KDialog.Cancel))
        layout = QGridLayout(self.mainWidget())
        
        self.setButtonText(KDialog.Ok, i18n("Install"))
        self.setButtonIcon(KDialog.Ok, KIcon("download"))
        self.setCaption(i18n("Download LilyPond"))
        self.setHelp("download-lilypond")
        
        l = QLabel(i18n(
            "With this tool you can download packaged binary releases "
            "of LilyPond for your operating system."))
        l.setWordWrap(True)
        layout.addWidget(l, 0, 0, 1, 2)
        
        v = self.lilyVersion = QComboBox()
        v.currentIndexChanged.connect(self.selectVersion, Qt.QueuedConnection)
        v.setToolTip(i18n(
            "Select the LilyPond version you want to download."))
        l = QLabel(i18n("Version:"))
        l.setBuddy(v)
        layout.addWidget(l, 1, 0)
        layout.addWidget(v, 1, 1)
        
        d = self.installDest = KUrlRequester()
        d.setMode(KFile.Mode(KFile.Directory | KFile.LocalOnly))
        d.setPath(config().readPathEntry(
            'lilypond install path', os.path.expanduser('~/lilypond_bin/')))
        d.setToolTip(i18n(
            "Select a writable directory you want to install LilyPond to.\n"
            "(A version-numbered directory will be created in this directory.)"))
        l = QLabel(i18n("Install into:"))
        l.setBuddy(d)
        layout.addWidget(l, 2, 0)
        layout.addWidget(d, 2, 1)
        
        s = self.status = QLabel()
        layout.addWidget(s, 3, 0, 1, 2)
        
        p = self.progress = QProgressBar()
        layout.addWidget(p, 4, 0, 1, 2)
        
        details = QGroupBox(i18n("Details"))
        layout.addWidget(details, 5, 0, 1, 2)
        layout = QGridLayout()
        details.setLayout(layout)

        b = self.baseUrl = QComboBox()
        b.setEditable(True)
        b.setToolTip(i18n(
            "The website where LilyPond binaries can be downloaded."))
        b.addItems(['http://download.linuxaudio.org/lilypond/binaries/'])
        b.setCurrentIndex(0)
        
        l = QLabel(i18n("Download from:"))
        l.setBuddy(b)
        layout.addWidget(l, 0, 0)
        layout.addWidget(b, 0, 1)
        
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

        l = QLabel(i18n("Machine type:"))
        l.setBuddy(m)
        layout.addWidget(l, 1, 0)
        layout.addWidget(m, 1, 1)
        
        u = self.packageUrl = KUrlRequester()
        u.setToolTip(i18n(
            "This is the URL to the package that will be downloaded and "
            "installed.\n"
            "You can also browse to other places to select a LilyPond package."))
        l = QLabel(i18n("Package Url:"))
        l.setBuddy(u)
        layout.addWidget(l, 2, 0)
        layout.addWidget(u, 2, 1)
        
        self.setDetailsWidget(details)
        
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
        else:
            self.setDetailsWidgetVisible(True)
        m.currentIndexChanged.connect(self.downloadVersions)
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
            self.status.setText(i18n(
                "No packages found. You can browse to a package manually."))
            self.setDetailsWidgetVisible(True)
            self.packageUrl.lineEdit().setFocus()
            return
        
        versions = {}
        versionStrings = {}
        for m in re.finditer(r'\bhref="(lilypond-.*?\.sh)"', self.loader.html()):
            fileName = m.group(1)
            m = _version_re.search(fileName)
            if m:
                versionStrings[fileName] = m.group()
                ver, build = m.group(1, 4)
                version = (tuple(map(int, re.findall(r'\d+', ver))), int(build or 0))
                versions[fileName] = version
        
        files = versions.keys()
        files.sort(key=versions.get)
        
        # add the versions
        self.lilyVersion.clear()
        self.items = []
        # determine last stable and development:
        stable, development = False, False
        for f in files[::-1]:
            if versions[f][0][1] & 1:
                if not development:
                    development = True
                    self.items.append(f)
                    self.lilyVersion.addItem(i18n(
                        "Latest Development Version (%1)", versionStrings[f]))
            elif not stable:
                stable = True
                self.items.append(f)
                self.lilyVersion.addItem(i18n(
                    "Latest Stable Version (%1)", versionStrings[f]))
            if stable and development:
                break
        
        for f in files:
            self.lilyVersion.addItem(versionStrings[f])
            self.items.append(f)
        self.lilyVersion.setCurrentIndex(0)

    def selectVersion(self, index):
        self.packageUrl.setUrl(KUrl(self.directory + self.items[index]))

    def done(self, result):
        if result == KDialog.Accepted:
            # Download (OK) clicked
            url = self.packageUrl.url()
            if not url.isEmpty():
                self.enableButtonOk(False)
                # save the install path
                config().writePathEntry('lilypond install path',
                    self.installDest.url().path())
                if url.isLocalFile():
                    self.unpack(url.path())
                else:
                    self.download(url)
        else:
            if self.downloadBusy():
                self.cancelDownload()
            elif not self.unpackBusy():
                KDialog.done(self, result)
    
    def download(self, url):
        """Download the package from given KUrl."""
        self.progress.setRange(0, 100)
        self.status.setText(i18n("Downloading %1...", url.fileName()))
        dest = KGlobal.dirs().saveLocation('tmp')
        self.job = KIO.copy(url, KUrl(dest),
            KIO.JobFlags(KIO.Overwrite | KIO.Resume | KIO.HideProgressInfo))
        QObject.connect(self.job, SIGNAL("percent(KJob*, unsigned long)"), self.slotPercent)
        QObject.connect(self.job, SIGNAL("result(KJob*)"), self.slotResult, Qt.QueuedConnection)
        self.job.start()
        
    def downloadBusy(self):
        return bool(self.job)
    
    def cancelDownload(self):
        self.job.kill()
        self.status.setText(i18n("Download cancelled."))
        self.enableButtonOk(True)
        self.progress.setValue(0)
        
    def slotPercent(self, job, percent):
        self.progress.setValue(percent)
        
    def slotResult(self):
        if self.job.error():
            self.status.setText(i18n("Download failed: %1", self.job.errorString()))
            self.enableButtonOk(True)
        else:
            fileName = self.job.srcUrls()[0].fileName()
            package = os.path.join(self.job.destUrl().path(), fileName)
            self.unpack(package)
        self.job = None

    def unpack(self, package):
        """Unpack the given lilypond .sh archive."""
        fileName = os.path.basename(package)
        ver = version(fileName) or 'unknown' # should not happen
        self.prefix = os.path.join(self.installDest.url().path(), ver)
        self.lilypond = os.path.join(self.prefix, "bin", "lilypond")
        if not os.path.exists(self.prefix):
            os.makedirs(self.prefix)
        elif os.path.exists(self.lilypond):
            result = KMessageBox.questionYesNoCancel(self, i18n(
                "LilyPond %1 seems already to be installed in %2.\n\n"
                "Do you want to use it or to remove and re-install?",
                ver, self.prefix), None,
                KGuiItem(i18n("Use existing LilyPond")),
                KGuiItem(i18n("Remove and re-install")))
            if result == KMessageBox.Yes:
                self.info.lilypond.setText(self.lilypond)
                self.enableButtonOk(True)
                KDialog.done(self, KDialog.Accepted)
                return
            elif result == KMessageBox.No:
                shutil.rmtree(self.prefix, True)
            else: # Cancel
                self.progress.reset()
                self.enableButtonOk(True)
                return
        self.status.setText(i18n("Unpacking %1...", fileName))
        self.progress.setRange(0, 0)
        unpack = self.unpackJob = QProcess()
        unpack.setProcessChannelMode(QProcess.MergedChannels)
        unpack.setWorkingDirectory(self.prefix)
        unpack.finished.connect(self.unpackFinished)
        unpack.error.connect(self.unpackError)
        unpack.start("sh", [package, "--batch", "--prefix", self.prefix])
    
    def unpackBusy(self):
        return bool(self.unpackJob and self.unpackJob.state())
        
    def unpackFinished(self, exitCode, exitStatus):
        self.progress.setRange(0, 100)
        self.progress.reset()
        self.enableButtonOk(True)
        if exitStatus == QProcess.NormalExit and exitCode == 0:
            self.status.setText(i18n("Unpacking finished."))
            self.info.lilypond.setText(self.lilypond)
            KDialog.done(self, KDialog.Accepted)
        else:
            self.status.setText(i18n("Unpacking failed."))
            KMessageBox.error(self, i18n("An error occurred:\n\n%1",
                str(self.unpackJob.readAllStandardOutput())))
        
    def unpackError(self, err):
        self.progress.setRange(0, 100)
        self.progress.reset()
        self.enableButtonOk(True)
        self.status.setText(i18n("Unpacking failed."))
        KMessageBox.error(self, i18n("An error occurred:\n\n%1",
            self.unpackJob.errorString()))



def config(group="installertools"):
    return KGlobal.config().group(group)

def version(fileName):
    """Determine version of the given package filename."""
    m = _version_re.search(fileName)
    if m:
        return m.group()

