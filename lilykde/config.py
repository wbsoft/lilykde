# config module

from qt import QString, QStringList
from kdecore import KConfig, KConfigGroup
from lilykde.util import py2qstringlist, qstringlist2py

main = KConfig("lilykderc", False, False)


class group(KConfigGroup):
    def __init__(self, groupname):
        KConfigGroup.__init__(self, main, groupname)

    def writePathEntry(self, key, path, *args, **kargs):
        if type(path) not in (str, unicode, QString, QStringList):
            path = py2qstringlist(path)
        KConfigGroup.writePathEntry(self, key, path, *args, **kargs)

    def readPathListEntry(self, *args, **kargs):
        return qstringlist2py(KConfigGroup.readPathListEntry(self, *args, **kargs))

