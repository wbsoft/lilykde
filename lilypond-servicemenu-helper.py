#!/python

import sys, os
from subprocess import call

def runLilyPond(paths):
    """
    Run Lilypond on a list of paths.
    If some paths are in the same directory, lilypond is run once.
    """
    # collect the directories
    dirs = {}
    for p in paths:
        path, file = os.path.split(p)
        dirs.setdefault(path,[]).append(file)
    
    for path in dirs:
        cmd = ["lilypond", "--pdf"]
        cmd.extend(dirs[path])
        call(cmd, cwd = path)

runLilyPond(sys.argv[1:])
