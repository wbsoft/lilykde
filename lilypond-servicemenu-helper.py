#! python

# This file is part of LilyKDE, http://lilykde.googlecode.com/
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


import sys, os

from kdecore import KAboutData, KApplication, KStandardDirs, KCmdLineArgs

# Find LilyKDE
sys.path[0:0] = map(os.path.normpath, map(str,
    KStandardDirs().findDirs("data", "lilykde")))


from lilykde.about import *
from lilykde.runlily import LyFile, LyJob
from lilykde.widgets import LogWidget

# Translate the messages
from lilykde.i18n import _, I18N_NOOP


class File(LyFile):

    def __init__(self, path):
        path = os.path.abspath(path).decode(
            sys.getfilesystemencoding() or 'utf-8')
        self.setPath(path) # the full path to the ly file

    def isLyFile(self):
        return self.extension in ('.ly', '.ily', '.lyi')


class Job(LyJob):

    def __init__(self, files, log, numFailed=0):
        if files:
            self.numFailed = numFailed
            self.f = File(files[0])
            self.files = files[1:]
            LyJob.__init__(self, self.f, log)
            self._run(['--pdf', self.f.ly])
        else:
            if numFailed:
                log.fail(_("One document failed.",
                           "$count documents failed.",
                           numFailed).args(count = numFailed))
            else:
                log.ok(_("All documents successfully converted."))

    def completed(self, success):
        if not success:
            self.numFailed += 1
        Job(self.files, self.log, self.numFailed)


def main():
    aboutData = KAboutData(
        PACKAGE, PROGRAMNAME, VERSION,
        I18N_NOOP("LilyKDE servicemenu helper"),
        KAboutData.License_GPL,
        "Copyright (c) 2008, " + AUTHOR,
        "", HOMEPAGE)
    KCmdLineArgs.init (sys.argv, aboutData)
    KCmdLineArgs.addCmdLineOptions([
        ("+files", I18N_NOOP("LilyPond files to convert"))
        ])
    app = KApplication()
    log = LogWidget()
    app.setMainWidget(log)
    log.setMinimumHeight(240)
    log.setMinimumWidth(400)
    log.setCaption(PROGRAMNAME)
    log.show()

    # get the files to convert
    pa = KCmdLineArgs.parsedArgs()
    files = map(pa.arg, range(pa.count()))

    # start the first job. Itself takes care of running the rest.
    Job(files, log)
    app.exec_loop()


main()


# kate: indent-width 4;
