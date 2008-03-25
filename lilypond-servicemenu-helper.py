#!/python

import sys, os
from subprocess import Popen, PIPE, STDOUT

from qt import *
from kdecore import *
from kdeui import *

def runLilyPond(paths, log):
    global app
    """
    Run Lilypond on a list of paths.
    If some paths are in the same directory, lilypond is run once.
    """
    # collect the directories
    dirs = {}
    for p in paths:
        path, file = os.path.split(os.path.abspath(p))
        dirs.setdefault(path,[]).append(file)

    retcode = 0
    cmd = ["lilypond", "--pdf"]
    for path in dirs:
        p = Popen(cmd + dirs[path], cwd=path, stdout=PIPE, stderr=STDOUT)
        for line in p.stdout:
            log.append(line.strip())
            log.repaint()
            app.processEvents()
        retcode = max(retcode, p.wait())
    return retcode

def main():
    global app, log
    KCmdLineArgs.init (sys.argv, "lilypond-servicemenu-helper", "", "1.0")
    KCmdLineArgs.addCmdLineOptions([("+files", "LilyPond files to convert")])
    app = KApplication()
    log = KTextBrowser()
    app.setMainWidget(log)
    #log.setMinimumHeight(240)
    #log.setMinimumWidth(400)
    log.show()
    QTimer.singleShot(1000, run)
    app.exec_loop()

def run():
    global app, log
    pa = KCmdLineArgs.parsedArgs()
    files = map(pa.arg, range(pa.count()))
    runLilyPond(files, log)

main()
