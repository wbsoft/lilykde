#! python

import sys, os

from kdecore import KAboutData, KApplication, KURL, KStandardDirs, KCmdLineArgs

# Find LilyKDE
sys.path[0:0] = map(os.path.normpath, map(str,
    KStandardDirs().findDirs("data", "lilykde")))


from lilykde.about import *
from lilykde.runlily import LyFile, LyJob
from lilykde.widgets import LogWidget

# Translate the messages
from lilykde.i18n import _


class File(LyFile):

    def __init__(self, path):
        self.kurl = KURL(os.path.abspath(path))
        self.path = unicode(self.kurl.path()) # the full path to the ly file
        self.ly = os.path.basename(self.path)
        self.directory = os.path.dirname(self.path)
        self.basename, self.extension = os.path.splitext(self.ly)
        self.pdf = self.ly and os.path.join(
            self.directory, self.basename + ".pdf") or None

    def isLyFile(self):
        return self.extension in ('.ly', '.ily', 'lyi')


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
        "LilyKDE servicemenu helper", KAboutData.License_GPL,
        "Copyright (c) 2008, " + AUTHOR,
        "", HOMEPAGE)
    KCmdLineArgs.init (sys.argv, aboutData)
    KCmdLineArgs.addCmdLineOptions([("+files", "LilyPond files to convert")])
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
